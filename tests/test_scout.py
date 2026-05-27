import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.pipeline import QUANT_REPORT_TYPES, run_scout, should_skip_quant_scout
from core.prompts import ROUTER_REPORT_TYPES, SCOUT_REGISTRY


class _StatusStub:
    def __init__(self) -> None:
        self.messages = []

    def write(self, message: str) -> None:
        self.messages.append(message)


def test_quant_scout_returns_directed_queries() -> None:
    payload = {
        "normalization_inputs": [{"variable": "cpi", "reason": "normalize inflation"}],
        "hidden_dependencies": [],
        "data_vintage": "same-year cost basis",
        "assumption_risks": ["nominal costs may not be comparable"],
        "directed_queries": ["airline cpi adjusted casm", "fleet age seat density", "fuel hedge exposure data"],
    }

    result = run_scout(
        scout_key="quant_scout",
        core_topic="MD-80 vs 777 unit costs",
        chunks=[{"text": "sample evidence", "url": "https://example.com"}],
        ask_model=lambda *args, **kwargs: json.dumps(payload),
        clean_json_response=lambda x: x,
        fast_provider="OpenAI",
        fast_model="gpt-5.4-mini",
        status_container=_StatusStub(),
    )

    assert isinstance(result, dict)
    assert "directed_queries" in result
    assert isinstance(result["directed_queries"], list)
    assert result["directed_queries"]
    assert all(isinstance(q, str) and q.strip() for q in result["directed_queries"])


def test_quant_scout_preserves_entity_separated_metric_economics_queries() -> None:
    captured: dict[str, str] = {}
    payload = {
        "normalization_inputs": [],
        "hidden_dependencies": [],
        "data_vintage": "matched stage length and cost basis",
        "assumption_risks": ["cost per passenger mile depends on seat layout and load factor"],
        "directed_queries": [
            "MD-80 CASM cents per seat-mile",
            "MD-80 block hour cost operating cost",
            "777-300ER CASM cost per seat-mile",
            "777-300ER DOC fuel burn operating cost",
        ],
    }

    def ask_model(user_message: str, system_prompt: str, **_kwargs: object) -> str:
        captured["user_message"] = user_message
        captured["system_prompt"] = system_prompt
        return json.dumps(payload)

    result = run_scout(
        scout_key="quant_scout",
        core_topic="cost per passenger mile of an MD-80 vs 777-300ER",
        chunks=[
            {
                "text": "Generic aircraft specifications mention seats and range but no economics.",
                "url": "https://example.com/specs",
            }
        ],
        ask_model=ask_model,
        clean_json_response=lambda x: x,
        fast_provider="OpenAI",
        fast_model="gpt-5.4-mini",
        status_container=_StatusStub(),
    )

    assert "cost per passenger mile of an MD-80 vs 777-300ER" in captured["user_message"]
    directed = result["directed_queries"]
    joined = " ".join(directed).lower()
    assert "md-80" in joined
    assert "777-300er" in joined
    assert any(
        term in joined
        for term in (
            "casm",
            "cost per seat-mile",
            "block hour cost",
            "doc",
            "fuel burn",
            "operating cost",
        )
    )
    assert all("md-80 777-300er" not in query.lower() for query in directed)
    assert all("vs" not in query.lower().split() for query in directed)


def test_scout_failure_is_nonfatal() -> None:
    result = run_scout(
        scout_key="quant_scout",
        core_topic="cost comparison",
        chunks=[{"text": "sample", "url": "https://example.com"}],
        ask_model=lambda *args, **kwargs: (_ for _ in ()).throw(Exception("boom")),
        clean_json_response=lambda x: x,
        fast_provider="OpenAI",
        fast_model="gpt-5.4-mini",
        status_container=_StatusStub(),
    )

    assert result is None


def test_scout_registry_keys_match_report_types() -> None:
    for key, config in SCOUT_REGISTRY.items():
        prompt_key = config.get("prompt_key")
        assert isinstance(prompt_key, str) and prompt_key
        assert key in QUANT_REPORT_TYPES or key in ROUTER_REPORT_TYPES


def test_scout_queries_replace_expander() -> None:
    original_queries = ["md80 direct operating cost", "boeing 777 operating cost"]
    report_type = "cost_analysis"
    complexity = "high"
    iteration = 1
    max_queries = 2
    scout_query_cap = 4

    scout_payload = {
        "normalization_inputs": [],
        "hidden_dependencies": [],
        "data_vintage": "matched period",
        "assumption_risks": [],
        "directed_queries": ["airline casm normalization inputs", "fuel price period average", "seat density configuration mix"],
    }
    scout_context = run_scout(
        scout_key="quant_scout",
        core_topic="MD-80 vs 777 costs",
        chunks=[{"text": "first pass evidence", "url": "https://example.com"}],
        ask_model=lambda *args, **kwargs: json.dumps(scout_payload),
        clean_json_response=lambda x: x,
        fast_provider="OpenAI",
        fast_model="gpt-5.4-mini",
        status_container=_StatusStub(),
    )

    current_queries = list(original_queries)
    if iteration == 1 and complexity != "low":
        scout_config = SCOUT_REGISTRY.get(report_type)
        if scout_config and scout_context and scout_config.get("replaces_expander"):
            directed = scout_context.get("directed_queries", [])
            if directed:
                current_queries = [str(q)[:300] for q in directed[:scout_query_cap] if str(q).strip()]

    assert current_queries == scout_payload["directed_queries"][:scout_query_cap]
    assert current_queries != original_queries
    assert len(current_queries) > max_queries


def test_should_skip_quant_scout_when_numeric_evidence_is_sufficient() -> None:
    chunks = [
        {"credibility": 3, "text": "Fare was 100 in 1912 and 200 today"},
        {"credibility": 2, "text": "Price index reached 350 in 2024"},
        {"credibility": 4, "text": "Ticket cost ranged from 50 to 500"},
        {"credibility": 2, "text": "Duration 6 days, route 3000 miles"},
        {"credibility": 1, "text": "low credibility filler"},
    ]
    assert should_skip_quant_scout("cost_analysis", chunks) is True


def test_should_not_skip_quant_scout_when_evidence_is_thin() -> None:
    chunks = [
        {"credibility": 3, "text": "Some mentions without numbers"},
        {"credibility": 2, "text": "Another qualitative mention"},
        {"credibility": 1, "text": "Low credibility numeric 123"},
    ]
    assert should_skip_quant_scout("cost_analysis", chunks) is False
