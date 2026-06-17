from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.followup_deliberation import ProviderJobKind, clean_text, clean_token
from core.followup_provider_result_set_diagnostics import (
    DISCOVERY_UNCONSTRAINED,
    build_official_current_discovery_diagnostics,
    sanitize_result_set_diagnostics,
)
from core.followup_search_freshness_policy import (
    build_search_freshness_policy_diagnostics,
)

PHASE_ID = "AG-96I3E"
SCHEMA_VERSION = "ag96i3e_brokered_provider_neutral_discovery_validation_v1"
OUTPUT_DIR = ROOT / "output"
LIVE_SPEND_WARNING = "This command may spend exactly one live provider/search call."
FIXTURE_PROVIDER = "fixture"
MAX_RESULTS_LIMIT = 10
SUPPORTED_PROVIDERS = frozenset({"brave", "tavily", "linkup", FIXTURE_PROVIDER})
DEFERRED_PROVIDERS = {
    "exa": (
        "deferred: current wrapper uses search_and_contents/text retrieval, so this "
        "phase does not treat it as an unambiguous single search-only provider call"
    ),
}
LIVE_BUDGET = {
    "max_provider_search_calls": 1,
    "max_results_limit": MAX_RESULTS_LIMIT,
    "max_fetch_read_attempts": 0,
    "max_model_calls": 0,
    "max_author_executor_calls": 0,
    "retries_allowed": False,
}


class ProviderCallBudget:
    def __init__(self, *, max_provider_search_calls: int = 1) -> None:
        self.max_provider_search_calls = max_provider_search_calls
        self.provider_search_call_count = 0

    def mark_provider_search_call(self) -> None:
        self.provider_search_call_count += 1
        if self.provider_search_call_count > self.max_provider_search_calls:
            raise RuntimeError("provider search call budget exceeded")


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    provider = clean_token(args.provider, limit=80)
    if provider not in SUPPORTED_PROVIDERS:
        reason = DEFERRED_PROVIDERS.get(provider, "unsupported provider")
        print(
            f"refusing unsupported provider surface: {args.provider} ({reason})",
            file=sys.stderr,
        )
        return 2
    fixture_mode = provider == FIXTURE_PROVIDER
    if not fixture_mode and not args.confirm_live_provider_call:
        print(
            "refusing to run brokered discovery validation: pass "
            "--confirm-live-provider-call to acknowledge live-call spend",
            file=sys.stderr,
        )
        return 2

    query = clean_text(args.query, limit=500)
    if not query:
        print("refusing empty query", file=sys.stderr)
        return 2

    output_path = _resolve_output_path(args.output)
    if not _is_allowed_output_path(output_path):
        print(
            "refusing to write discovery validation packet outside ignored repo "
            f"output/ path: {output_path}",
            file=sys.stderr,
        )
        return 2

    max_results = int(args.max_results)
    if max_results < 1:
        print("refusing max-results below 1", file=sys.stderr)
        return 2
    if max_results > MAX_RESULTS_LIMIT:
        print(f"refusing max-results above {MAX_RESULTS_LIMIT}", file=sys.stderr)
        return 2

    if not fixture_mode and not _provider_config_available(provider):
        print(
            f"refusing provider call: required {provider} provider config is missing",
            file=sys.stderr,
        )
        return 3

    freshness_policy = _build_freshness_policy(
        query=query,
        freshness_intent=args.freshness_intent,
    )
    budget = ProviderCallBudget()
    if fixture_mode:
        raw_results = _fixture_results()
    else:
        print(LIVE_SPEND_WARNING)
        try:
            raw_results = list(
                _dispatch_provider(
                    provider,
                    query,
                    max_results,
                    budget=budget,
                    freshness_policy=freshness_policy,
                )
            )
        except Exception as exc:
            print(
                "provider call failed before sanitized packet creation: "
                f"{type(exc).__name__}",
                file=sys.stderr,
            )
            return 1

    if budget.provider_search_call_count > LIVE_BUDGET["max_provider_search_calls"]:
        print("provider search call budget exceeded", file=sys.stderr)
        return 1

    packet = build_validation_packet(
        provider=provider,
        query=query,
        job_id=args.job_id,
        max_results=max_results,
        raw_results=raw_results,
        provider_search_call_count=budget.provider_search_call_count,
        fixture_mode=fixture_mode,
        freshness_policy_diagnostics=freshness_policy,
    )

    rendered = json.dumps(packet, indent=2, sort_keys=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered + "\n", encoding="utf-8")
    print(f"wrote sanitized AG-96I3E discovery validation packet to {output_path}")
    return 0


def build_validation_packet(
    *,
    provider: str,
    query: str,
    job_id: str,
    max_results: int,
    raw_results: Iterable[Mapping[str, Any]],
    provider_search_call_count: int,
    fixture_mode: bool = False,
    include_domains: Iterable[str] | None = None,
    domain_constraints: Iterable[str] | None = None,
    freshness_intent: str | None = None,
    freshness_policy_diagnostics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_results = normalize_provider_results(
        raw_results,
        provider=provider,
        max_results=max_results,
    )
    diagnostics = _build_diagnostics(
        normalized_results,
        provider=provider,
        query=query,
        job_id=job_id,
        include_domains=include_domains,
        domain_constraints=domain_constraints,
    )
    freshness_policy = dict(
        freshness_policy_diagnostics
        or _build_freshness_policy(query=query, freshness_intent=freshness_intent)
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "brokered_provider_neutral_discovery_validation_packet",
        "phase_id": PHASE_ID,
        "owner": "AG96I3EBrokeredProviderNeutralDiscoveryValidationRunner",
        "canonical_state": False,
        "trace_only": False,
        "storage_only": False,
        "job_id": clean_text(job_id, limit=180),
        "provider": clean_token(provider, limit=80),
        "query": clean_text(query, limit=500),
        "provider_surface_role": "candidate_acquisition",
        "scout_surface_role": "provider_neutral_scout",
        "provider_job_kind": ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value,
        "acquisition_mode": DISCOVERY_UNCONSTRAINED,
        "max_results_requested": int(max_results),
        "live_validation_run": not fixture_mode,
        "fixture_mode": bool(fixture_mode),
        "live_budget": dict(LIVE_BUDGET),
        "provider_search_call_count": int(provider_search_call_count),
        "fetch_read_attempt_count": 0,
        "model_call_count": 0,
        "author_executor_call_count": 0,
        "freshness_policy_diagnostics": freshness_policy,
        "provider_result_set_diagnostics": diagnostics,
        "redaction_posture": _redaction_posture(),
        "closed_surface_flags": _closed_surface_flags(),
        "evidence_boundary": {
            "selected_candidates_are_final_evidence": False,
            "selected_candidates_are_citation_eligible": False,
            "final_evidence_requires_later_fetch_read_admission": True,
            "author_or_final_answer_activation_allowed": False,
        },
        "notes": [
            "Selected candidates are diagnostic observations only, not final evidence.",
            "Citation eligibility still requires a later fetch/read/admission phase.",
        ],
    }


def normalize_provider_results(
    raw_results: Iterable[Mapping[str, Any]],
    *,
    provider: str,
    max_results: int,
) -> list[dict[str, Any]]:
    normalized = []
    for item in list(raw_results)[:max_results]:
        mapped = dict(item) if isinstance(item, Mapping) else {}
        url = clean_text(mapped.get("url"), limit=500)
        domain = clean_text(mapped.get("domain"), limit=160) or _domain_from_url(url)
        normalized.append(
            {
                "title": clean_text(mapped.get("title") or mapped.get("name"), limit=300),
                "url": url,
                "domain": clean_text(domain, limit=160),
                "source_tier": clean_token(mapped.get("source_tier"), limit=120),
                "source_class": clean_token(mapped.get("source_class"), limit=120),
                "currentness_signal": clean_token(
                    mapped.get("currentness_signal"),
                    limit=120,
                ),
                "provider_name": clean_token(provider, limit=80),
            }
        )
    return normalized


def _build_diagnostics(
    results: list[dict[str, Any]],
    *,
    provider: str,
    query: str,
    job_id: str,
    include_domains: Iterable[str] | None = None,
    domain_constraints: Iterable[str] | None = None,
) -> dict[str, Any]:
    if include_domains or domain_constraints:
        raise ValueError(
            "discovery_unconstrained validation forbids include/domain constraints"
        )
    diagnostics = build_official_current_discovery_diagnostics(
        results,
        provider_name=provider,
        provider_surface_role="candidate_acquisition",
        provider_job_kind=ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value,
        acquisition_mode=DISCOVERY_UNCONSTRAINED,
        authorized_query_ref=f"ag96i3e:{clean_token(job_id, limit=140)}",
        authorized_query=query,
        include_domains=None,
        domain_constraints=None,
        authority_decision_present=False,
    )
    return sanitize_result_set_diagnostics(
        diagnostics,
        provider_job_kind=ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value,
        provider_name=provider,
        provider_surface_role="candidate_acquisition",
        acquisition_mode=DISCOVERY_UNCONSTRAINED,
    )


def _dispatch_provider(
    provider: str,
    query: str,
    max_results: int,
    *,
    budget: ProviderCallBudget,
    freshness_policy: Mapping[str, Any] | None = None,
) -> Iterable[Mapping[str, Any]]:
    budget.mark_provider_search_call()
    if provider == "brave":
        from core.search_providers import search_scout_results

        return search_scout_results(
            provider="brave",
            query=query,
            max_results=max_results,
            freshness_policy=freshness_policy,
            cost_phase="ag96i3e_validation",
        )
    if provider == "tavily":
        from core.search_providers import search_web_results

        search = getattr(search_web_results, "__wrapped__", search_web_results)
        results, _images = search(
            query,
            intent="general",
            complexity="low",
            max_results=max_results,
            search_depth="basic",
            include_domains=None,
            exclude_domains=None,
            cost_phase="ag96i3e_validation",
        )
        return results
    if provider == "linkup":
        from core.search_providers import search_linkup_results

        search = getattr(search_linkup_results, "__wrapped__", search_linkup_results)
        results, _images = search(
            query,
            depth="standard",
            output_type="searchResults",
            intent="general",
            max_results=max_results,
            include_domains=None,
            exclude_domains=None,
            cost_phase="ag96i3e_validation",
        )
        return results
    raise ValueError(f"unsupported provider: {provider}")


def _build_freshness_policy(
    *,
    query: str,
    freshness_intent: str | None = None,
) -> dict[str, Any]:
    return build_search_freshness_policy_diagnostics(
        authorized_query=query,
        provider_job_kind=ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value,
        acquisition_mode=DISCOVERY_UNCONSTRAINED,
        query_shape_mode="official_current_artifact_discovery",
        freshness_intent=freshness_intent,
    )


def _fixture_results() -> list[dict[str, Any]]:
    return [
        {
            "title": "Secondary bridge explanation for current discovery",
            "url": "https://example.com/bridge-current-discovery",
            "domain": "example.com",
            "snippet": "raw fixture bridge snippet must be stripped",
            "raw_content": "raw fixture bridge content must be stripped",
            "payload": {"raw_fixture_payload": "blocked_bridge_payload"},
        },
        {
            "title": "FTC current official consumer rule 2026",
            "url": "https://www.ftc.gov/legal-library/current-official-consumer-rule-2026",
            "domain": "ftc.gov",
            "snippet": "raw fixture official snippet must be stripped",
            "raw_content": "raw fixture official content must be stripped",
            "payload": {"raw_fixture_payload": "blocked_official_payload"},
        },
    ]


def _provider_config_available(provider: str) -> bool:
    env_var_by_provider = {
        "brave": "BRAVE_API_KEY",
        "tavily": "TAVILY_API_KEY",
        "linkup": "LINKUP_API_KEY",
    }
    env_var = env_var_by_provider.get(provider)
    return bool(env_var and os.environ.get(env_var))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run one broker-invoked provider-neutral official/current discovery "
            "validation call."
        )
    )
    parser.add_argument("--provider", required=True, help="Provider surface to call.")
    parser.add_argument("--query", required=True, help="Authorized query text.")
    parser.add_argument("--job-id", required=True, help="Broker allowlisted job id.")
    parser.add_argument("--output", required=True, help="Ignored output/ packet path.")
    parser.add_argument(
        "--max-results",
        type=int,
        default=5,
        help="Maximum provider results to request and sanitize. Default: 5.",
    )
    parser.add_argument(
        "--confirm-live-provider-call",
        action="store_true",
        help="Acknowledge exactly one live provider/search call may be spent.",
    )
    parser.add_argument(
        "--freshness-intent",
        choices=[
            "none",
            "latest_breaking",
            "recent_days",
            "recent_weeks",
            "recent_months",
            "current_year",
            "known_year",
            "current_or_stable",
            "historical_or_stable",
            "mixed_probe",
        ],
        help="Safe offline freshness intent override for diagnostic scout policy.",
    )
    return parser


def _resolve_output_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def _is_allowed_output_path(path: Path) -> bool:
    try:
        path.relative_to(OUTPUT_DIR.resolve())
    except ValueError:
        return False
    return _is_gitignored(path)


def _is_gitignored(path: Path) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "-q", str(path)],
        check=False,
        capture_output=True,
        cwd=ROOT,
        text=True,
    )
    return result.returncode == 0


def _domain_from_url(url: str | None) -> str | None:
    parsed = urlparse(url or "")
    domain = parsed.netloc.casefold()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain or None


def _redaction_posture() -> dict[str, bool]:
    return {
        "sanitized_ranked_results_only": True,
        "raw_provider_payloads_retained": False,
        "raw_provider_payload_retained": False,
        "raw_snippets_retained": False,
        "raw_content_retained": False,
        "raw_page_text_retained": False,
        "raw_text_retained": False,
        "raw_prompts_retained": False,
        "model_outputs_retained": False,
        "api_keys_retained": False,
        "env_values_retained": False,
        "db_rows_retained": False,
        "cache_rows_retained": False,
        "private_logs_retained": False,
        "full_traces_retained": False,
    }


def _closed_surface_flags() -> dict[str, bool]:
    return {
        "product_provider_routing_changed": False,
        "provider_selection_policy_changed": False,
        "query_generation_changed": False,
        "query_mutation_changed": False,
        "retrieval_ranking_filtering_changed": False,
        "fetch_read_invoked": False,
        "model_called": False,
        "author_executor_invoked": False,
        "citation_behavior_changed": False,
        "product_answer_behavior_changed": False,
        "evidence_ledger_authority_changed": False,
        "sufficiency_authority_changed": False,
        "final_answer_packet_authority_changed": False,
        "pipeline_orchestrator_domain_logic_changed": False,
        "source_specific_irs_branching_added": False,
    }


if __name__ == "__main__":
    raise SystemExit(main())
