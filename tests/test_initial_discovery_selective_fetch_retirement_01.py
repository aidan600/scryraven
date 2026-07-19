"""Offline product-path proof for initial-discovery selective-fetch retirement.

Test class: phase_focus / offline_product_path_proof / PRODUCT-PATH-REGRESSION.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

import pytest

import core.pipeline as pipeline
import core.search_providers as provider_adapters
from core.cap_enforcement import RunCapPolicy
from tests.helpers.offline_ordinary_pipeline import (
    OFFLINE_SEARCH_PROVIDER_ENV_KEYS,
    execution_event_from_log,
    run_post_retirement_ordinary_pipeline,
)

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"


def _result(*, provider: str, raw_content: Any) -> dict[str, Any]:
    result = {
        "title": f"{provider.title()} provider result",
        "url": f"https://{provider}.example.test/current-rule",
        "domain": f"{provider}.example.test",
        "credibility": 4,
        "snippet": "Provider-returned bounded snippet. " * 12,
        "raw_content": raw_content,
    }
    if provider == "exa":
        result["_exa_score"] = 0.73
    return result


def _run_provider(
    monkeypatch: pytest.MonkeyPatch,
    *,
    provider: str,
    complexity: str,
    result_factory: Callable[[], dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[tuple[str, dict[str, Any]]]]:
    calls: list[tuple[str, dict[str, Any]]] = []

    def selected(query: str, **kwargs: Any) -> tuple[list[dict[str, Any]], list[str]]:
        calls.append((query, dict(kwargs)))
        return [result_factory()], []

    def unexpected(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("only the selected DISCOVER provider may run")

    monkeypatch.setattr(pipeline, "search_web_results", unexpected)
    monkeypatch.setattr(pipeline, "search_linkup_results", unexpected)
    monkeypatch.setattr(pipeline, "search_exa_results", unexpected)
    if provider == "tavily":
        monkeypatch.setattr(pipeline, "search_web_results", selected)
    elif provider == "linkup":
        monkeypatch.setenv("LINKUP_API_KEY", "offline-placeholder")
        monkeypatch.setattr(pipeline, "search_linkup_results", selected)
    else:
        monkeypatch.setenv("EXA_API_KEY", "offline-placeholder")
        monkeypatch.setattr(pipeline, "search_exa_results", selected)

    passages = pipeline.process_search_queries(
        ["offline current rule"],
        "general",
        complexity,
        "advanced" if complexity == "high" else "basic",
        8,
        [],
        [],
        [1.0, 0.0],
        set(),
        set(),
        "offline-embed-provider",
        "offline-embed-model",
        None,
        lambda texts, **_kwargs: [[1.0, 0.0] for _ in texts],
        lambda _query, embeddings: [0.8 for _ in embeddings],
        search_providers=[provider],
        provider_role="main_retrieval",
        iteration=2,
    )
    return passages, calls


@pytest.mark.parametrize(
    ("provider", "complexity", "raw_content", "material_kind"),
    [
        (
            "tavily",
            "low",
            {"nested": "must not stringify into discovery material"},
            "provider_returned_snippet",
        ),
        (
            "linkup",
            "medium",
            "Linkup provider-returned excerpt. " * 30,
            "provider_returned_excerpt",
        ),
        (
            "exa",
            "high",
            "Exa provider-returned excerpt. " * 30,
            "provider_returned_excerpt",
        ),
    ],
)
def test_fast_balanced_and_deep_rank_only_provider_returned_material(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    complexity: str,
    raw_content: Any,
    material_kind: str,
) -> None:
    passages, calls = _run_provider(
        monkeypatch,
        provider=provider,
        complexity=complexity,
        result_factory=lambda: _result(provider=provider, raw_content=raw_content),
    )

    assert len(calls) == 1
    assert passages
    passage = passages[0]
    assert passage["title"] == f"{provider.title()} provider result"
    assert passage["url"] == f"https://{provider}.example.test/current-rule"
    assert passage["provider_name"] == provider
    assert passage["provider_role"] == "main_retrieval"
    assert passage["retrieval_pass_id"] == "main_retrieval:2"
    assert passage["provider_rank_or_position"] == 1
    assert passage["query_preview"] == "offline current rule"
    assert passage["evidence_material_type"] == "snippet_only"
    assert passage["source_material_type"] == "snippet_only"
    assert passage["discovery_material_type"] == material_kind
    assert passage["provider_material_kind"] == material_kind
    assert passage["provider_returned"] is True
    assert passage["snippet_only"] is True
    assert passage["full_page_fetched"] is False
    assert passage["product_fetch_read_executed"] is False
    assert passage["separate_exact_url_transport_performed"] is False
    assert passage["provider_internal_acquisition_unobserved"] is True
    assert "raw_content" not in passage
    assert "[FULL_PAGE]" not in passage["text"]
    if provider == "tavily":
        assert "nested" not in passage["text"]
        assert "Provider-returned bounded snippet" in passage["text"]
    if provider == "exa":
        assert passage["_exa_score"] == 0.73
    assert passage["score"] == pytest.approx(0.64)


def test_single_provider_material_ranking_is_deterministic_offline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first, _ = _run_provider(
        monkeypatch,
        provider="tavily",
        complexity="high",
        result_factory=lambda: _result(
            provider="tavily",
            raw_content="Deterministic provider excerpt. " * 30,
        ),
    )
    second, _ = _run_provider(
        monkeypatch,
        provider="tavily",
        complexity="high",
        result_factory=lambda: _result(
            provider="tavily",
            raw_content="Deterministic provider excerpt. " * 30,
        ),
    )

    assert first == second


def test_multi_query_provider_ranking_ignores_future_completion_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queries = ["alpha rule", "beta rule"]

    def provider_result(provider: str, query: str) -> dict[str, Any]:
        query_slug = query.replace(" ", "-")
        return {
            "title": f"{provider.title()} {query}",
            "url": f"https://{provider}.example.test/{query_slug}",
            "domain": f"{provider}.example.test",
            "credibility": 1,
            "snippet": f"Provider-returned {provider} material for {query}. " * 8,
        }

    monkeypatch.setenv("LINKUP_API_KEY", "offline-placeholder")
    monkeypatch.setattr(
        pipeline,
        "search_web_results",
        lambda query, **_kwargs: ([provider_result("tavily", query)], []),
    )
    monkeypatch.setattr(
        pipeline,
        "search_linkup_results",
        lambda query, **_kwargs: ([provider_result("linkup", query)], []),
    )

    def run(*, reverse_completion: bool) -> list[tuple[str, str, str, float]]:
        monkeypatch.setattr(
            pipeline.concurrent.futures,
            "as_completed",
            lambda futures: (
                list(reversed(list(futures)))
                if reverse_completion
                else list(futures)
            ),
        )
        passages = pipeline.process_search_queries(
            queries,
            "general",
            "low",
            "basic",
            8,
            [],
            [],
            None,
            set(),
            set(),
            "offline-embed-provider",
            "offline-embed-model",
            None,
            lambda *_args, **_kwargs: [],
            lambda *_args, **_kwargs: [],
            search_providers=["tavily", "linkup"],
        )
        return [
            (
                str(passage["provider_name"]),
                str(passage["query_preview"]),
                str(passage["url"]),
                float(passage["rrf_score"]),
            )
            for passage in passages
        ]

    forward = run(reverse_completion=False)
    reverse = run(reverse_completion=True)

    assert reverse == forward
    assert forward == [
        (
            "tavily",
            "alpha rule",
            "https://tavily.example.test/alpha-rule",
            pytest.approx(1.0 / 61.0),
        ),
        (
            "linkup",
            "alpha rule",
            "https://linkup.example.test/alpha-rule",
            pytest.approx(1.0 / 61.0),
        ),
        (
            "tavily",
            "beta rule",
            "https://tavily.example.test/beta-rule",
            pytest.approx(1.0 / 62.0),
        ),
        (
            "linkup",
            "beta rule",
            "https://linkup.example.test/beta-rule",
            pytest.approx(1.0 / 62.0),
        ),
    ]


class _OfflineResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


def test_tavily_discover_adapter_normalizes_provider_material_offline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    def post(url: str, **kwargs: Any) -> _OfflineResponse:
        calls.append((url, kwargs))
        return _OfflineResponse(
            {
                "results": [
                    {
                        "title": "  Tavily title  ",
                        "url": "https://tavily.example.test/rule",
                        "content": "  Tavily snippet  ",
                        "raw_content": "Tavily provider excerpt",
                    }
                ],
                "images": [],
            }
        )

    monkeypatch.setenv("TAVILY_API_KEY", "offline-placeholder")
    monkeypatch.setattr(provider_adapters.requests, "post", post)

    results, images = provider_adapters.search_web_results("offline rule")

    assert images == []
    assert len(calls) == 1
    assert calls[0][0] == "https://api.tavily.com/search"
    assert calls[0][1]["json"]["include_raw_content"] is True
    assert results[0]["title"] == "Tavily title"
    assert results[0]["snippet"] == "Tavily snippet"
    assert results[0]["raw_content"] == "Tavily provider excerpt"
    assert results[0]["domain"] == "tavily.example.test"


def test_linkup_discover_adapter_normalizes_provider_material_offline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    def post(url: str, **kwargs: Any) -> _OfflineResponse:
        calls.append((url, kwargs))
        return _OfflineResponse(
            {
                "results": [
                    {
                        "name": "Linkup title",
                        "url": "https://linkup.example.test/rule",
                        "content": "Linkup provider excerpt",
                    }
                ]
            }
        )

    monkeypatch.setenv("LINKUP_API_KEY", "offline-placeholder")
    monkeypatch.setattr(provider_adapters.requests, "post", post)

    results, images = provider_adapters.search_linkup_results("offline rule")

    assert images == []
    assert len(calls) == 1
    assert calls[0][0] == "https://api.linkup.so/v1/search"
    assert results[0]["title"] == "Linkup title"
    assert results[0]["snippet"] == "Linkup provider excerpt"
    assert results[0]["raw_content"] == "Linkup provider excerpt"
    assert results[0]["domain"] == "linkup.example.test"


def test_exa_discover_adapter_normalizes_provider_material_offline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    class _OfflineExa:
        def search_and_contents(self, query: str, **kwargs: Any) -> Any:
            calls.append((query, kwargs))
            return SimpleNamespace(
                results=[
                    SimpleNamespace(
                        title="Exa title",
                        url="https://exa.example.test/rule",
                        text="Exa provider excerpt",
                        score=0.73,
                    )
                ]
            )

    monkeypatch.setenv("EXA_API_KEY", "offline-placeholder")
    monkeypatch.setattr(provider_adapters, "get_exa_client", _OfflineExa)

    results, images = provider_adapters.search_exa_results("offline rule")

    assert images == []
    assert calls == [("offline rule", {"num_results": 6, "type": "neural", "text": True})]
    assert results[0]["title"] == "Exa title"
    assert results[0]["snippet"] == "Exa provider excerpt"
    assert results[0]["raw_content"] == "Exa provider excerpt"
    assert results[0]["domain"] == "exa.example.test"
    assert results[0]["_exa_score"] == 0.73


def test_deep_preserves_material_buckets_thresholds_and_chunk_sizes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results = [
        {
            "title": "Long boundary",
            "url": "https://example.test/long-boundary",
            "domain": "example.test",
            "credibility": 4,
            "raw_content": "l" * 200,
        },
        {
            "title": "Long accepted",
            "url": "https://example.test/long-accepted",
            "domain": "example.test",
            "credibility": 4,
            "raw_content": "L" * 201,
        },
        {
            "title": "Short boundary",
            "url": "https://example.test/short-boundary",
            "domain": "example.test",
            "credibility": 1,
            "raw_content": "s" * 150,
        },
        {
            "title": "Short accepted",
            "url": "https://example.test/short-accepted",
            "domain": "example.test",
            "credibility": 1,
            "raw_content": "S" * 151,
        },
    ]
    chunk_sizes: list[int] = []

    def record_chunk_size(text: str, *, chunk_size: int) -> list[str]:
        chunk_sizes.append(chunk_size)
        return [text]

    monkeypatch.setattr(
        pipeline, "search_web_results", lambda *_args, **_kwargs: (results, [])
    )
    monkeypatch.setattr(pipeline, "chunk_text", record_chunk_size)

    passages = pipeline.process_search_queries(
        ["offline bucket proof"],
        "general",
        "high",
        "advanced",
        8,
        [],
        [],
        None,
        set(),
        set(),
        "offline-embed-provider",
        "offline-embed-model",
        None,
        lambda *_args, **_kwargs: [],
        lambda *_args, **_kwargs: [],
        search_providers=["tavily"],
    )

    assert [passage["url"] for passage in passages] == [
        "https://example.test/short-accepted",
        "https://example.test/long-accepted",
    ]
    assert chunk_sizes == [1200, 2000]
    assert all(passage["text"].startswith("[SNIPPET] ") for passage in passages)


def test_deep_preserves_embedding_bound_rrf_blend_gate_and_entity_floor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results = [
        {
            "title": "Rejected",
            "url": "https://example.test/rejected",
            "domain": "example.test",
            "credibility": 0,
            "raw_content": "Below the existing blended-score threshold. " * 5,
            "rrf_score": 0.0,
        },
        {
            "title": "Target Entity current rule",
            "url": "https://example.test/entity-floor",
            "domain": "example.test",
            "credibility": 0,
            "raw_content": "Target Entity provider material. " * 8,
            "rrf_score": 0.0,
        },
        {
            "title": "Blended",
            "url": "https://example.test/blended",
            "domain": "example.test",
            "credibility": 4,
            "raw_content": "B" * 9000,
            "rrf_score": 0.025,
        },
    ]
    embedded_texts: list[str] = []

    def embed(texts: list[str], **_kwargs: Any) -> list[list[float]]:
        embedded_texts.extend(texts)
        return [[float(index)] for index in range(len(texts))]

    def similarities(
        _query: list[float], embeddings: list[list[float]]
    ) -> list[float]:
        return [0.1, 0.0, 0.2][: len(embeddings)]

    monkeypatch.setattr(
        pipeline, "search_web_results", lambda *_args, **_kwargs: (results, [])
    )
    monkeypatch.setattr(
        pipeline, "chunk_text", lambda text, *, chunk_size: [text]
    )

    passages = pipeline.process_search_queries(
        ["offline scoring proof"],
        "general",
        "high",
        "advanced",
        8,
        [],
        [],
        [1.0],
        set(),
        set(),
        "offline-embed-provider",
        "offline-embed-model",
        None,
        embed,
        similarities,
        search_providers=["tavily"],
        entity_hint="Target Entity",
    )

    by_url = {passage["url"]: passage for passage in passages}
    assert "https://example.test/rejected" not in by_url
    assert by_url["https://example.test/entity-floor"]["score"] == pytest.approx(
        0.185
    )
    assert by_url["https://example.test/blended"]["score"] == pytest.approx(0.265)
    assert [len(text) for text in embedded_texts] == [
        len("[SNIPPET] " + results[0]["raw_content"]),
        len("[SNIPPET] " + results[1]["raw_content"]),
        8000,
    ]


@pytest.mark.parametrize(("complexity", "expected"), [("low", 10), ("medium", 25), ("high", 40)])
def test_existing_mode_candidate_limits_are_preserved(
    monkeypatch: pytest.MonkeyPatch,
    complexity: str,
    expected: int,
) -> None:
    results = [
        {
            "title": f"Result {index}",
            "url": f"https://example.test/{index}",
            "domain": "example.test",
            "credibility": 1,
            "snippet": "Provider-returned bounded candidate material. " * 8,
        }
        for index in range(45)
    ]
    monkeypatch.setattr(
        pipeline,
        "search_web_results",
        lambda *_args, **_kwargs: (results, []),
    )

    passages = pipeline.process_search_queries(
        ["offline cap proof"],
        "general",
        complexity,
        "basic",
        45,
        [],
        [],
        None,
        set(),
        set(),
        "offline-embed-provider",
        "offline-embed-model",
        None,
        lambda *_args, **_kwargs: [],
        lambda *_args, **_kwargs: [],
        search_providers=["tavily"],
    )

    assert len(passages) == expected
    assert [passage["url"] for passage in passages] == [
        f"https://example.test/{index}" for index in range(expected)
    ]


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def test_ordinary_discovery_has_a_durable_no_exact_url_transport_boundary() -> None:
    provider_transport_owner = CORE / "search_providers.py"
    acquisition_transport_owner = CORE / "acquisition_adapters.py"
    explicitly_nonordinary_dogfood = {
        ROOT / "proplex" / "mvp_live_dogfood_run.py",
        ROOT / "proplex" / "mvp_single_relation_live_dogfood_run.py",
    }
    ordinary_files = (
        set(CORE.glob("*.py"))
        | set((ROOT / "proplex").glob("*.py"))
    ).difference(
        {
            provider_transport_owner,
            acquisition_transport_owner,
            *explicitly_nonordinary_dogfood,
        }
    )
    forbidden_symbols = {
        "fetch_page",
        "fetch_url_text",
        "_apply_source_custody_fetch_read_policy",
        "ordinary_live_source_fetch_read",
        "legacy_linkup_fetch",
    }
    forbidden_network_calls = {
        "requests.get",
        "requests.post",
        "requests.request",
        "httpx.get",
        "httpx.post",
        "httpx.request",
        "urllib.request.urlopen",
        "request.urlopen",
        "urlopen",
        "build_opener",
    }
    forbidden_network_imports = {
        "aiohttp",
        "httpx",
        "requests",
        "urllib.request",
    }
    forbidden_product_imports = {
        "proplex.mvp_live_dogfood_run",
        "proplex.mvp_single_relation_live_dogfood_run",
    }
    for path in ordinary_files:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        assert imports.isdisjoint(forbidden_network_imports), path
        if path.name != "__main__.py":
            assert imports.isdisjoint(forbidden_product_imports), path
        dynamic_network_imports = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and _dotted_name(node.func) in {"__import__", "importlib.import_module"}
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value in forbidden_network_imports
        ]
        assert dynamic_network_imports == [], path
        identifiers = {
            node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
        }
        identifiers.update(
            node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
        )
        identifiers.update(
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        assert forbidden_symbols.isdisjoint(identifiers), path
        calls = {
            _dotted_name(node.func)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
        }
        assert calls.isdisjoint(forbidden_network_calls), path

    cli_path = ROOT / "proplex" / "__main__.py"
    cli_tree = ast.parse(cli_path.read_text(encoding="utf-8"))
    parents = {
        child: node
        for node in ast.walk(cli_tree)
        for child in ast.iter_child_nodes(node)
    }
    explicit_dogfood_flags = {
        "_run_mvp_live_dogfood_run": {"mvp_live_dogfood_run"},
        "_run_mvp_single_relation_live_dogfood_run": {
            "mvp_single_relation_live_dogfood_run",
            "mvp_current_source_of_record_single_fact_run",
        },
    }
    for helper_name, required_flags in explicit_dogfood_flags.items():
        helper_calls = [
            node
            for node in ast.walk(cli_tree)
            if isinstance(node, ast.Call)
            and _dotted_name(node.func) == helper_name
        ]
        assert len(helper_calls) == 1
        ancestors: list[ast.AST] = []
        current: ast.AST | None = helper_calls[0]
        while current in parents:
            current = parents[current]
            ancestors.append(current)
        guarding_flags = {
            node.attr
            for ancestor in ancestors
            if isinstance(ancestor, ast.If)
            for node in ast.walk(ancestor.test)
            if isinstance(node, ast.Attribute)
        }
        assert guarding_flags.intersection(required_flags), helper_name

    provider_tree = ast.parse(
        provider_transport_owner.read_text(encoding="utf-8")
    )
    provider_http_calls: set[tuple[str, str, str]] = set()
    for function in (
        node
        for node in ast.walk(provider_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ):
        for call in (
            node for node in ast.walk(function) if isinstance(node, ast.Call)
        ):
            dotted = _dotted_name(call.func)
            if dotted not in {"requests.post", "httpx.get"}:
                continue
            assert call.args and isinstance(call.args[0], ast.Constant), function.name
            assert isinstance(call.args[0].value, str), function.name
            provider_http_calls.add(
                (function.name, dotted, call.args[0].value)
            )
    assert provider_http_calls == {
        (
            "search_web_results",
            "requests.post",
            "https://api.tavily.com/search",
        ),
        (
            "search_linkup_results",
            "requests.post",
            "https://api.linkup.so/v1/search",
        ),
        (
            "_brave_search_results",
            "httpx.get",
            "https://api.search.brave.com/res/v1/web/search",
        ),
        (
            "_serper_search_results",
            "requests.post",
            "https://google.serper.dev/search",
        ),
    }
    exa_search_calls = [
        (function.name, call)
        for function in ast.walk(provider_tree)
        if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef))
        and function.name == "_search"
        for call in ast.walk(function)
        if isinstance(call, ast.Call)
        and _dotted_name(call.func).endswith(".search_and_contents")
    ]
    assert len(exa_search_calls) == 1
    exa_owner, exa_call = exa_search_calls[0]
    assert exa_owner == "_search"
    assert exa_call.args and isinstance(exa_call.args[0], ast.Name)
    assert exa_call.args[0].id == "query"

    dispatch_calls: list[tuple[Path, ast.Call, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    offline_validation_dispatch_calls: list[
        tuple[Path, ast.Call, ast.FunctionDef | ast.AsyncFunctionDef]
    ] = []
    for path in CORE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for function in (
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ):
            for node in ast.walk(function):
                if not isinstance(node, ast.Call):
                    continue
                called = _dotted_name(node.func)
                if called in {"dispatch_acquisition"} or called.endswith(
                    ".dispatch_acquisition"
                ):
                    dispatch_calls.append((path, node, function))
                if called.endswith(
                    "dispatch_acquisition_for_offline_target_safety_validation"
                ):
                    offline_validation_dispatch_calls.append(
                        (path, node, function)
                    )
    assert len(dispatch_calls) == 1
    path, call, function = dispatch_calls[0]
    assert path.name == "authorized_acquisition_runtime.py"
    before_transport = next(
        keyword for keyword in call.keywords if keyword.arg == "before_transport"
    )
    assert _dotted_name(before_transport.value) == (
        "claim_immediately_before_transport"
    )
    function_calls = {
        _dotted_name(node.func)
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
    }
    assert "run_kernel.claim_acquisition_execution" in function_calls
    assert len(offline_validation_dispatch_calls) == 1
    offline_path, offline_call, offline_function = (
        offline_validation_dispatch_calls[0]
    )
    assert offline_path.name == "authorized_acquisition_runtime.py"
    assert offline_function is function
    offline_before_transport = next(
        keyword
        for keyword in offline_call.keywords
        if keyword.arg == "before_transport"
    )
    assert _dotted_name(offline_before_transport.value) == (
        "claim_immediately_before_transport"
    )

    run_config_tree = ast.parse((CORE / "run_config.py").read_text(encoding="utf-8"))
    annotations = {
        node.target.id: ast.unparse(node.annotation)
        for node in ast.walk(run_config_tree)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }
    assert annotations["ordinary_live_source_acquisition_transports"] == (
        "AcquisitionTransports | None"
    )
    cli_source = (ROOT / "proplex" / "__main__.py").read_text(encoding="utf-8")
    assert "process_search_queries=process_search_queries" in cli_source
    assert "ordinary_live_source_fetch_read" not in cli_source


def test_discovery_admission_and_exact_url_transport_telemetry_are_separate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cap_policy = RunCapPolicy(
        max_search_dispatches=8,
        max_fetch_read_operations=0,
        max_author_model_calls=4,
        max_smart_search_judgment_model_calls=0,
        max_retries=2,
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        cap_policy=cap_policy,
        environment_overrides={
            OFFLINE_SEARCH_PROVIDER_ENV_KEYS["tavily"]: "offline-placeholder"
        },
    )

    trace = outcome.execution_trace
    execution_record = execution_event_from_log(tmp_path / "execution.jsonl")
    admitted_count = trace["discover_candidate_urls_admitted"]

    assert harness.search_calls
    assert outcome.seen_urls
    assert admitted_count == len(outcome.seen_urls)
    assert admitted_count > 0
    assert trace["urls_fetched"] == 0
    assert execution_record["discover_candidate_urls_admitted"] == admitted_count
    assert execution_record["urls_fetched"] == 0
    assert execution_record["execution_trace"][
        "discover_candidate_urls_admitted"
    ] == admitted_count
    assert execution_record["execution_trace"]["urls_fetched"] == 0
    assert cap_policy.fetch_read_operations == 0
    assert harness.forbidden_live_calls == []


def test_all_discovery_admission_totals_use_only_the_admission_accumulator() -> None:
    orchestrator_source = (CORE / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )

    assert "total_urls_fetched" not in orchestrator_source
    assert orchestrator_source.count("discover_candidate_urls_admitted +=") == 4
    for delta_expression in (
        "main_retrieval_outcome.seen_url_delta",
        "retry_outcome.seen_url_delta",
        "source_class_recovery_result.total_urls_delta",
        'conflict_resolution_execution["new_url_count"]',
    ):
        assert delta_expression in orchestrator_source
    assert "urls_fetched +=" not in orchestrator_source
    assert "urls_fetched = 0" in orchestrator_source
