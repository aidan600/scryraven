"""LLM, embedding, and similarity helpers usable outside Streamlit."""

from __future__ import annotations

import logging
import os
import time
from functools import lru_cache, wraps
from typing import Any, Callable, Generator, List, Optional, Union

import numpy as np
from exa_py import Exa
from openai import OpenAI

from core.cap_enforcement import (
    DEFAULT_EXTERNAL_TIMEOUT_SECONDS,
    DEFAULT_MODEL_TIMEOUT_SECONDS,
    MODEL_OUTPUT_TOKEN_LIMIT,
    AttemptReservation,
    ExternalAttemptSpec,
    ExternalCallFamily,
    RunCapExceeded,
    RunCapPolicy,
    TokenUsage,
    embedding_usage_bound,
    mark_cap_aware,
    model_usage_bound,
)
from core.cost_accounting import CostAccumulator, estimate_tokens, extract_usage_tokens

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@lru_cache(maxsize=1)
def get_exa_client() -> Exa:
    return Exa(api_key=os.getenv("EXA_API_KEY"))


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cap_policy = kwargs.get("cap_policy")
            bounded = isinstance(cap_policy, RunCapPolicy) and cap_policy.bounded
            attempt_limit = 1 if bounded and cap_policy.max_retries == 0 else max_retries
            for attempt in range(attempt_limit):
                call_kwargs = dict(kwargs)
                call_kwargs["_physical_retry_index"] = attempt
                try:
                    return func(*args, **call_kwargs)
                except RunCapExceeded:
                    raise
                except Exception as e:
                    if attempt == attempt_limit - 1:
                        if bounded:
                            logger.error(
                                "Bounded %s request failed.",
                                func.__name__,
                            )
                        else:
                            logger.error(
                                "Function %s failed after %s attempts. Error: %s",
                                func.__name__,
                                attempt_limit,
                                e,
                            )
                        raise
                    time.sleep(base_delay * (2**attempt))

        return wrapper

    return decorator


def _reserve_model_attempt(
    cap_policy: RunCapPolicy | None,
    *,
    provider: str,
    model: str,
    operation: str,
    prompt: str,
    system_prompt: str,
    logical_call_id: str | None,
    retry_index: int,
    fallback: bool = False,
) -> AttemptReservation | None:
    if cap_policy is None or not cap_policy.bounded:
        return None
    logical_id = logical_call_id or cap_policy.new_logical_call_id("model")
    pricing = cap_policy.resolve_route_pricing(ExternalCallFamily.MODEL, provider, model)
    return cap_policy.reserve_attempt(
        ExternalAttemptSpec(
            family=ExternalCallFamily.MODEL,
            provider=pricing.pricing_key.split(".", 1)[0],
            route=model,
            operation=operation,
            logical_call_id=logical_id,
            max_usage=model_usage_bound(prompt, system_prompt),
            pricing=pricing,
            requested_timeout_seconds=DEFAULT_MODEL_TIMEOUT_SECONDS,
            is_retry=retry_index > 0,
            is_fallback=fallback,
        )
    )


def _reserve_embedding_attempt(
    cap_policy: RunCapPolicy | None,
    *,
    provider: str,
    model: str,
    batch: list[str],
    logical_call_id: str | None,
    retry_index: int,
) -> AttemptReservation | None:
    if cap_policy is None or not cap_policy.bounded:
        return None
    logical_id = logical_call_id or cap_policy.new_logical_call_id("embedding")
    pricing = cap_policy.resolve_route_pricing(ExternalCallFamily.EMBEDDING, provider, model)
    return cap_policy.reserve_attempt(
        ExternalAttemptSpec(
            family=ExternalCallFamily.EMBEDDING,
            provider=pricing.pricing_key.split(".", 1)[0],
            route=model,
            operation="embeddings",
            logical_call_id=logical_id,
            max_usage=embedding_usage_bound(batch),
            pricing=pricing,
            requested_timeout_seconds=DEFAULT_EXTERNAL_TIMEOUT_SECONDS,
            is_retry=retry_index > 0,
        )
    )


def _bounded_client(client: OpenAI, reservation: AttemptReservation | None) -> OpenAI:
    if reservation is None:
        return client
    try:
        return client.with_options(
            max_retries=0,
            timeout=reservation.timeout_seconds,
        )
    except Exception:
        reservation.cancel_pre_dispatch("client_configuration_failed")
        raise


def _dispatch(
    reservation: AttemptReservation | None,
    operation: Any,
) -> Any:
    if reservation is None:
        return operation()
    reservation.mark_dispatched()
    try:
        return operation()
    except Exception:
        reservation.settle_conservative("dispatch_outcome_ambiguous")
        raise


def _model_usage(response: Any) -> TokenUsage | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    input_tokens = getattr(usage, "prompt_tokens", None)
    if input_tokens is None:
        input_tokens = getattr(usage, "input_tokens", None)
    output_tokens = getattr(usage, "completion_tokens", None)
    if output_tokens is None:
        output_tokens = getattr(usage, "output_tokens", None)
    if input_tokens is None and output_tokens is None:
        return None
    input_details = getattr(usage, "prompt_tokens_details", None)
    if input_details is None:
        input_details = getattr(usage, "input_tokens_details", None)
    output_details = getattr(usage, "completion_tokens_details", None)
    if output_details is None:
        output_details = getattr(usage, "output_tokens_details", None)
    return TokenUsage(
        input_tokens=int(input_tokens or 0),
        cached_input_tokens=int(getattr(input_details, "cached_tokens", 0) or 0),
        output_tokens=int(output_tokens or 0),
        reasoning_tokens=int(getattr(output_details, "reasoning_tokens", 0) or 0),
    )


def _settle_model(
    reservation: AttemptReservation | None,
    response: Any,
) -> None:
    if reservation is not None:
        reservation.settle_observed(_model_usage(response))


def response_text(resp: Any) -> str:
    if hasattr(resp, "choices") and resp.choices:
        if hasattr(resp.choices[0], "message") and hasattr(resp.choices[0].message, "content"):
            return resp.choices[0].message.content or ""
    if hasattr(resp, "output_text") and resp.output_text:
        return resp.output_text
    parts = []
    for item in getattr(resp, "output", []) or []:
        for c in getattr(item, "content", []) or []:
            txt = getattr(c, "text", None)
            if txt:
                parts.append(txt)
    if parts:
        return "\n".join(parts).strip()
    return str(resp)


def _record_model_cost(
    cost_accumulator: Optional[CostAccumulator],
    *,
    phase: str,
    model: str,
    prompt: str,
    system_prompt: str,
    response: Any = None,
    output_text: str = "",
) -> None:
    if cost_accumulator is None:
        return
    input_tokens, output_tokens = extract_usage_tokens(response) if response is not None else (None, None)
    if input_tokens is None:
        input_tokens = estimate_tokens(prompt) + estimate_tokens(system_prompt)
    if output_tokens is None:
        output_tokens = estimate_tokens(output_text)
    cost_accumulator.record_model_call(
        phase=phase,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def _tracked_stream(
    stream: Generator[str, None, None],
    cost_accumulator: Optional[CostAccumulator],
    *,
    phase: str,
    model: str,
    prompt: str,
    system_prompt: str,
    reservation: AttemptReservation | None = None,
    close_stream: Callable[[], Any] | None = None,
) -> Generator[str, None, None]:
    parts: list[str] = []
    try:
        for chunk in stream:
            if reservation is not None and reservation.remaining_seconds <= 0:
                raise RunCapExceeded(
                    "deadline_exhausted",
                    family=ExternalCallFamily.MODEL,
                )
            if isinstance(chunk, str):
                parts.append(chunk)
            yield chunk
    finally:
        if close_stream is not None:
            try:
                close_stream()
            except Exception:
                pass
        if reservation is not None:
            reservation.settle_conservative("stream_usage_unavailable")
        _record_model_cost(
            cost_accumulator,
            phase=phase,
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            output_text="".join(parts),
        )


@mark_cap_aware
@retry_with_backoff(max_retries=3, base_delay=1.5)
def ask_model(
    prompt: str,
    system_prompt: str,
    provider: str = "OpenAI",
    model: str = "gpt-5.4-mini",
    effort: str = "low",
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    stream: bool = False,
    require_json: bool = False,
    use_reasoning: bool = True,
    cost_accumulator: Optional[CostAccumulator] = None,
    cost_phase: str = "model",
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    cap_policy: RunCapPolicy | None = None,
    logical_call_id: str | None = None,
    _physical_retry_index: int = 0,
) -> Union[str, Generator[str, None, None]]:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    response_format = {"type": "json_object"} if require_json else None

    if provider == "Local (LM Studio)":
        local_client = OpenAI(base_url=base_url, api_key="lm-studio")
        reservation = _reserve_model_attempt(
            cap_policy,
            provider=provider,
            model=model,
            operation="chat_stream" if stream else "chat",
            prompt=prompt,
            system_prompt=system_prompt,
            logical_call_id=logical_call_id,
            retry_index=_physical_retry_index,
        )
        local_client = _bounded_client(local_client, reservation)
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": 0.3 if temperature is None else temperature,
            "stream": stream,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if response_format:
            kwargs["response_format"] = response_format
        resp = _dispatch(
            reservation,
            lambda: local_client.chat.completions.create(**kwargs),
        )
        if stream:

            def generator():
                try:
                    for chunk in resp:
                        if chunk.choices and chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content
                except Exception:
                    yield "\n\n*[Connection lost]*"

            return _tracked_stream(
                generator(),
                cost_accumulator,
                phase=cost_phase,
                model=model,
                prompt=prompt,
                system_prompt=system_prompt,
                reservation=reservation,
                close_stream=getattr(resp, "close", None),
            )
        text = resp.choices[0].message.content or ""
        _settle_model(reservation, resp)
        _record_model_cost(
            cost_accumulator,
            phase=cost_phase,
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            response=resp,
            output_text=text,
        )
        return text

    if provider == "OpenRouter":
        if not api_key:
            raise ValueError("OpenRouter API key is missing!")
        or_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        reservation = _reserve_model_attempt(
            cap_policy,
            provider=provider,
            model=model,
            operation="chat_stream" if stream else "chat",
            prompt=prompt,
            system_prompt=system_prompt,
            logical_call_id=logical_call_id,
            retry_index=_physical_retry_index,
        )
        or_client = _bounded_client(or_client, reservation)
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": 0.3 if temperature is None else temperature,
            "extra_headers": {"HTTP-Referer": "https://localhost", "X-Title": "Research Pipeline"},
            "stream": stream,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if response_format:
            kwargs["response_format"] = response_format
        resp = _dispatch(
            reservation,
            lambda: or_client.chat.completions.create(**kwargs),
        )
        if stream:

            def generator():
                try:
                    for chunk in resp:
                        if chunk.choices and chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content
                except Exception:
                    yield "\n\n*[Connection lost]*"

            return _tracked_stream(
                generator(),
                cost_accumulator,
                phase=cost_phase,
                model=model,
                prompt=prompt,
                system_prompt=system_prompt,
                reservation=reservation,
                close_stream=getattr(resp, "close", None),
            )
        text = resp.choices[0].message.content or ""
        _settle_model(reservation, resp)
        _record_model_cost(
            cost_accumulator,
            phase=cost_phase,
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            response=resp,
            output_text=text,
        )
        return text

    openai_client = get_openai_client()
    kwargs = {"model": model, "messages": messages}

    is_reasoning_model = model.lower() in ["gpt-5.4", "gpt-5.4-mini", "o1", "o1-mini", "o1-preview", "o3-mini"]
    if effort in ["low", "medium", "high"] and is_reasoning_model and use_reasoning:
        kwargs["reasoning_effort"] = effort
    if temperature is not None:
        kwargs["temperature"] = temperature
    elif not (is_reasoning_model and use_reasoning):
        kwargs["temperature"] = 0.3

    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    if cap_policy is not None and cap_policy.bounded:
        kwargs.pop("max_tokens", None)
        kwargs["max_completion_tokens"] = min(
            max(1, int(max_tokens or MODEL_OUTPUT_TOKEN_LIMIT)),
            MODEL_OUTPUT_TOKEN_LIMIT,
        )

    if response_format:
        kwargs["response_format"] = response_format

    if stream:
        try:
            reservation = _reserve_model_attempt(
                cap_policy,
                provider=provider,
                model=model,
                operation="chat_stream",
                prompt=prompt,
                system_prompt=system_prompt,
                logical_call_id=logical_call_id,
                retry_index=_physical_retry_index,
            )
            request_client = _bounded_client(openai_client, reservation)
            stream_kwargs = dict(kwargs)
            if reservation is not None:
                stream_kwargs["stream_options"] = {"include_usage": True}
            resp = _dispatch(
                reservation,
                lambda: request_client.chat.completions.create(
                    **stream_kwargs,
                    stream=True,
                ),
            )

            def generator():
                try:
                    for chunk in resp:
                        if chunk.choices and chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content
                except Exception as e:
                    if reservation is not None:
                        raise
                    yield f"\n\n*[Connection lost: {e}]*"

            return _tracked_stream(
                generator(),
                cost_accumulator,
                phase=cost_phase,
                model=model,
                prompt=prompt,
                system_prompt=system_prompt,
                reservation=reservation,
                close_stream=getattr(resp, "close", None),
            )
        except RunCapExceeded:
            raise
        except Exception:
            if cap_policy is not None and cap_policy.should_disable_fallback():
                raise
            try:
                reservation = _reserve_model_attempt(
                    cap_policy,
                    provider=provider,
                    model=model,
                    operation="chat",
                    prompt=prompt,
                    system_prompt=system_prompt,
                    logical_call_id=logical_call_id,
                    retry_index=_physical_retry_index,
                    fallback=True,
                )
                request_client = _bounded_client(openai_client, reservation)
                resp = _dispatch(
                    reservation,
                    lambda: request_client.chat.completions.create(**kwargs),
                )
                _settle_model(reservation, resp)
                final_text = resp.choices[0].message.content or ""
                usage_response = resp
            except RunCapExceeded:
                raise
            except Exception:
                reservation = _reserve_model_attempt(
                    cap_policy,
                    provider=provider,
                    model=model,
                    operation="responses",
                    prompt=prompt,
                    system_prompt=system_prompt,
                    logical_call_id=logical_call_id,
                    retry_index=_physical_retry_index,
                    fallback=True,
                )
                request_client = _bounded_client(openai_client, reservation)
                response_kwargs = {
                    "model": model,
                    "input": messages,
                    "reasoning": {"effort": effort},
                }
                if reservation is not None:
                    response_kwargs["max_output_tokens"] = MODEL_OUTPUT_TOKEN_LIMIT
                resp = _dispatch(
                    reservation,
                    lambda: request_client.responses.create(**response_kwargs),
                )
                _settle_model(reservation, resp)
                final_text = response_text(resp)
                usage_response = resp

            def fake_generator():
                chunk_size = 20
                for i in range(0, len(final_text), chunk_size):
                    yield final_text[i : i + chunk_size]
                    time.sleep(0.01)

            _record_model_cost(
                cost_accumulator,
                phase=cost_phase,
                model=model,
                prompt=prompt,
                system_prompt=system_prompt,
                response=usage_response,
                output_text=final_text,
            )
            return fake_generator()

    try:
        reservation = _reserve_model_attempt(
            cap_policy,
            provider=provider,
            model=model,
            operation="chat",
            prompt=prompt,
            system_prompt=system_prompt,
            logical_call_id=logical_call_id,
            retry_index=_physical_retry_index,
        )
        request_client = _bounded_client(openai_client, reservation)
        resp = _dispatch(
            reservation,
            lambda: request_client.chat.completions.create(**kwargs),
        )
        _settle_model(reservation, resp)
        text = resp.choices[0].message.content or ""
        _record_model_cost(
            cost_accumulator,
            phase=cost_phase,
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            response=resp,
            output_text=text,
        )
        return text
    except RunCapExceeded:
        raise
    except Exception:
        if cap_policy is not None and cap_policy.should_disable_fallback():
            raise
        reservation = _reserve_model_attempt(
            cap_policy,
            provider=provider,
            model=model,
            operation="responses",
            prompt=prompt,
            system_prompt=system_prompt,
            logical_call_id=logical_call_id,
            retry_index=_physical_retry_index,
            fallback=True,
        )
        request_client = _bounded_client(openai_client, reservation)
        response_kwargs = {
            "model": model,
            "input": messages,
            "reasoning": {"effort": effort},
        }
        if reservation is not None:
            response_kwargs["max_output_tokens"] = MODEL_OUTPUT_TOKEN_LIMIT
        resp = _dispatch(
            reservation,
            lambda: request_client.responses.create(**response_kwargs),
        )
        _settle_model(reservation, resp)
        text = response_text(resp)
        _record_model_cost(
            cost_accumulator,
            phase=cost_phase,
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            response=resp,
            output_text=text,
        )
        return text


@mark_cap_aware
@retry_with_backoff(max_retries=3, base_delay=1.0)
def embed_texts(
    texts: List[str],
    provider: str = "OpenAI",
    model: str = "text-embedding-3-small",
    base_url: Optional[str] = None,
    cost_accumulator: Optional[CostAccumulator] = None,
    cost_phase: str = "embedding",
    cap_policy: RunCapPolicy | None = None,
    logical_call_id: str | None = None,
    _physical_retry_index: int = 0,
) -> List[List[float]]:
    if not texts:
        return []

    if provider == "Local (LM Studio)":
        embed_client = OpenAI(base_url=base_url, api_key="lm-studio")
    else:
        embed_client = get_openai_client()

    batch_size = 100
    all_embeddings = []
    effective_logical_id = logical_call_id
    if effective_logical_id is None and cap_policy is not None and cap_policy.bounded:
        effective_logical_id = cap_policy.new_logical_call_id("embedding")

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        reservation = _reserve_embedding_attempt(
            cap_policy,
            provider=provider,
            model=model,
            batch=batch,
            logical_call_id=effective_logical_id,
            retry_index=_physical_retry_index,
        )
        request_client = _bounded_client(embed_client, reservation)
        resp = _dispatch(
            reservation,
            lambda: request_client.embeddings.create(model=model, input=batch),
        )
        input_tokens, _ = extract_usage_tokens(resp)
        if reservation is not None:
            reservation.settle_observed(
                TokenUsage(embedding_tokens=int(input_tokens)) if input_tokens is not None else None
            )
        if input_tokens is None:
            input_tokens = estimate_tokens(batch)
        if cost_accumulator is not None:
            cost_accumulator.record_embedding_call(
                phase=cost_phase,
                model=model,
                input_tokens=input_tokens,
            )
        all_embeddings.extend([d.embedding for d in resp.data])

    return all_embeddings


def compute_similarities(q_emb: List[float], doc_embs: List[List[float]]) -> np.ndarray:
    if not doc_embs:
        return np.array([])
    q_vec = np.array(q_emb)
    embs_matrix = np.array(doc_embs)
    dot_products = np.dot(embs_matrix, q_vec)
    norms = np.linalg.norm(embs_matrix, axis=1) * np.linalg.norm(q_vec)
    return np.divide(dot_products, norms, out=np.zeros_like(dot_products), where=norms != 0)
