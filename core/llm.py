"""LLM, embedding, and similarity helpers usable outside Streamlit."""

from __future__ import annotations

import logging
import os
import time
from functools import lru_cache, wraps
from typing import Any, Generator, List, Optional, Union

import numpy as np
from exa_py import Exa
from openai import OpenAI

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
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} attempts. Error: {e}"
                        )
                        raise
                    time.sleep(base_delay * (2**attempt))

        return wrapper

    return decorator


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
) -> Generator[str, None, None]:
    parts: list[str] = []
    try:
        for chunk in stream:
            if isinstance(chunk, str):
                parts.append(chunk)
            yield chunk
    finally:
        _record_model_cost(
            cost_accumulator,
            phase=phase,
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            output_text="".join(parts),
        )


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
) -> Union[str, Generator[str, None, None]]:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    response_format = {"type": "json_object"} if require_json else None

    if provider == "Local (LM Studio)":
        local_client = OpenAI(base_url=base_url, api_key="lm-studio")
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
        resp = local_client.chat.completions.create(**kwargs)
        if stream:

            def generator():
                try:
                    for chunk in resp:
                        if chunk.choices and chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content
                except Exception:
                    yield "\n\n*[Connection lost]*"

            return _tracked_stream(
                generator(), cost_accumulator, phase=cost_phase, model=model, prompt=prompt, system_prompt=system_prompt
            )
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

    if provider == "OpenRouter":
        if not api_key:
            raise ValueError("OpenRouter API key is missing!")
        or_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
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
        resp = or_client.chat.completions.create(**kwargs)
        if stream:

            def generator():
                try:
                    for chunk in resp:
                        if chunk.choices and chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content
                except Exception:
                    yield "\n\n*[Connection lost]*"

            return _tracked_stream(
                generator(), cost_accumulator, phase=cost_phase, model=model, prompt=prompt, system_prompt=system_prompt
            )
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

    if response_format:
        kwargs["response_format"] = response_format

    if stream:
        try:
            resp = openai_client.chat.completions.create(**kwargs, stream=True)

            def generator():
                try:
                    for chunk in resp:
                        if chunk.choices and chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content
                except Exception as e:
                    yield f"\n\n*[Connection lost: {e}]*"

            return _tracked_stream(
                generator(), cost_accumulator, phase=cost_phase, model=model, prompt=prompt, system_prompt=system_prompt
            )
        except Exception:
            try:
                resp = openai_client.chat.completions.create(**kwargs)
                final_text = resp.choices[0].message.content or ""
                usage_response = resp
            except Exception:
                resp = openai_client.responses.create(model=model, input=messages, reasoning={"effort": effort})
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
        resp = openai_client.chat.completions.create(**kwargs)
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
    except Exception:
        resp = openai_client.responses.create(model=model, input=messages, reasoning={"effort": effort})
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


@retry_with_backoff(max_retries=3, base_delay=1.0)
def embed_texts(
    texts: List[str],
    provider: str = "OpenAI",
    model: str = "text-embedding-3-small",
    base_url: Optional[str] = None,
    cost_accumulator: Optional[CostAccumulator] = None,
    cost_phase: str = "embedding",
) -> List[List[float]]:
    if not texts:
        return []

    if provider == "Local (LM Studio)":
        embed_client = OpenAI(base_url=base_url, api_key="lm-studio")
    else:
        embed_client = get_openai_client()

    batch_size = 100
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = embed_client.embeddings.create(model=model, input=batch)
        input_tokens, _ = extract_usage_tokens(resp)
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
