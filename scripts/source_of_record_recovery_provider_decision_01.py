"""SEAM-DIAGNOSTIC: source-of-record recovery provider decision harness.

Harness label: SEAM-DIAGNOSTIC
Ordinary product path guarded or fed: generic single-relation source-obligation
recovery acquisition provider-role config.
Runtime consumer: core.single_relation_source_obligation_recovery_authorization
recovery plan consumed by proplex.mvp_single_relation_live_dogfood_run.
Why ordinary product-path work cannot be done directly: this phase licenses one
bounded provider-role comparison before changing the recovery provider role.
Integration deadline: current phase, if one extraction-capable provider safely
wins; otherwise recommend a follow-up with the precise blocker.
Exit condition: selected provider is wired into the recovery role/config seam,
or the packet records no safe winner and this harness remains uncommitted
operator output only.
Why this is not a shadow product path: it calls the same product-owned provider
acquisition adapter and uses the same bounded-window selector as the recovery
lane; it does not answer the user query or bypass the runner.
Forbidden interpretation: this is not product correctness, source authority,
source-obligation satisfaction, citation eligibility, D-prime admission, FAP,
Author, fetch/read validation, or a global provider default.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from core.generic_product_provider_acquisition import (
    BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_CREDENTIAL_UNAVAILABLE,
    EXTRACTION_CAPABLE_PROVIDERS,
    SCOUT_ONLY_PROVIDERS,
    ProductProviderAcquisitionRequest,
    ProductProviderAcquisitionRunner,
    build_generic_product_provider_acquisition_runner,
)
from core.generic_query_to_relation_planning import build_generic_query_relation_plan
from core.source_of_record_recovery_provider_config import (
    SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER_ROLE,
    SOURCE_OF_RECORD_RECOVERY_SCOUT_PROVIDER_ROLE,
)
from proplex import mvp_single_relation_live_dogfood_run as dogfood

PHASE_NAME = (
    "GENERIC-SINGLE-RELATION-SOURCE-OF-RECORD-RECOVERY-EXTRACTION-"
    "PROVIDER-DECISION-01"
)
SCHEMA_VERSION = "source_of_record_recovery_provider_decision_packet_v1"
DEFAULT_OUTPUT_ROOT = Path("output") / "source_of_record_recovery_provider_decision_01"
PACKET_NAME = "provider_decision_packet.json"
FIXED_COMPARISON_QUERY = (
    "USCIS N-400 Form N-400 paper filing fee paper current official fee "
    "schedule filing fees form instructions"
)
DIAGNOSTIC_RELATION_QUERY = (
    "What is the current USCIS Form N-400 paper filing fee?"
)
DOMAIN_CONSTRAINTS = ("uscis.gov",)
PROVIDER_ORDER = ("tavily", "linkup", "exa", "brave", "serper")
MAX_RESULTS = 5

QUALITY_OFFICIAL_ANSWER = "official_answer_bearing_extracted_material_found"
QUALITY_OFFICIAL_NOT_ANSWER = "official_material_found_but_not_answer_bearing"
QUALITY_NON_OFFICIAL_ANSWER = "answer_bearing_non_official_only"
QUALITY_SCOUT_ONLY = "scout_only_needs_extraction"
QUALITY_NO_USEFUL = "no_useful_candidates"
QUALITY_UNAVAILABLE = "provider_unavailable"
QUALITY_FAILED = "provider_failed_closed"


@dataclass(frozen=True, slots=True)
class ProviderDecisionComparisonResult:
    return_code: int
    packet_path: Path
    selected_provider: str | None
    blocker: str | None
    packet: dict[str, Any]


def run_source_of_record_recovery_provider_decision_comparison(
    *,
    repo_root: str | Path,
    output_root: str | Path | None = None,
    run_id: str | None = None,
    confirm_live_provider_comparison: bool = False,
    product_provider_acquisition_runner: ProductProviderAcquisitionRunner | None = None,
) -> ProviderDecisionComparisonResult:
    root = Path(repo_root).resolve()
    run_id = _run_id(run_id)
    run_dir = _run_output_dir(root, output_root or DEFAULT_OUTPUT_ROOT, run_id)
    packet_path = run_dir / PACKET_NAME
    if not confirm_live_provider_comparison:
        packet = _blocked_confirmation_packet(run_id=run_id)
        _write_json(packet_path, packet)
        return ProviderDecisionComparisonResult(
            return_code=2,
            packet_path=packet_path,
            selected_provider=None,
            blocker=str(packet["decision_blocker"]),
            packet=packet,
        )

    output_blocker = _prepare_output_dir(run_dir)
    if output_blocker:
        packet = _blocked_output_packet(run_id=run_id, blocker_detail=output_blocker)
        return ProviderDecisionComparisonResult(
            return_code=2,
            packet_path=packet_path,
            selected_provider=None,
            blocker=str(packet["decision_blocker"]),
            packet=packet,
        )

    runner = (
        product_provider_acquisition_runner
        or build_generic_product_provider_acquisition_runner()
    )
    relation_plan = build_generic_query_relation_plan(DIAGNOSTIC_RELATION_QUERY)
    acquisition_plan = dogfood._build_fast_acquisition_plan(relation_plan)
    provider_diagnostics: list[dict[str, Any]] = []
    for provider in PROVIDER_ORDER:
        provider_diagnostics.append(
            _run_provider_comparison(
                provider=provider,
                runner=runner,
                root=root,
                run_dir=run_dir,
                relation_plan=relation_plan,
                acquisition_plan=acquisition_plan,
            )
        )
    selected = _select_provider(provider_diagnostics)
    blocker = None
    if selected is None:
        blocker = "NO_SAFE_SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER_SELECTED"
    packet = _decision_packet(
        run_id=run_id,
        provider_diagnostics=provider_diagnostics,
        selected_provider=selected,
        blocker=blocker,
    )
    _write_json(packet_path, packet)
    return ProviderDecisionComparisonResult(
        return_code=0 if selected else 2,
        packet_path=packet_path,
        selected_provider=selected,
        blocker=blocker,
        packet=packet,
    )


def _run_provider_comparison(
    *,
    provider: str,
    runner: ProductProviderAcquisitionRunner,
    root: Path,
    run_dir: Path,
    relation_plan: Mapping[str, Any],
    acquisition_plan: Mapping[str, Any],
) -> dict[str, Any]:
    provider_role = (
        SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER_ROLE
        if provider in EXTRACTION_CAPABLE_PROVIDERS
        else SOURCE_OF_RECORD_RECOVERY_SCOUT_PROVIDER_ROLE
    )
    provider_response_path = run_dir / f"{provider}-sanitized-provider-response.json"
    result = runner(
        ProductProviderAcquisitionRequest(
            repo_root=root,
            output_path=provider_response_path,
            query=FIXED_COMPARISON_QUERY,
            provider=provider,
            acquisition_provider_role=provider_role,
            operation="search",
            max_results=MAX_RESULTS,
            domain_constraints=DOMAIN_CONSTRAINTS,
            include_domains=DOMAIN_CONSTRAINTS,
            source_of_record_domain_constraints=DOMAIN_CONSTRAINTS,
        )
    )
    credential_unavailable = (
        result.blocker
        == BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_CREDENTIAL_UNAVAILABLE
    )
    diagnostic: dict[str, Any] = {
        "provider": provider,
        "provider_role": provider_role,
        "operation": "search",
        "extraction_capable": provider in EXTRACTION_CAPABLE_PROVIDERS,
        "scout_only": provider in SCOUT_ONLY_PROVIDERS,
        "provider_available": result.return_code == 0,
        "credential_unavailable": credential_unavailable,
        "provider_call_attempted": result.provider_calls_attempted > 0,
        "provider_call_completed": result.provider_calls_completed > 0,
        "provider_calls_attempted": result.provider_calls_attempted,
        "provider_calls_completed": result.provider_calls_completed,
        "provider_response_path": _display_path(provider_response_path)
        if provider_response_path.exists()
        else None,
        "failure_blocker": result.blocker,
        "failure_detail": result.detail,
        "results_returned": 0,
        "url_bound_result_count": 0,
        "official_source_of_record_looking_result_count": 0,
        "extracted_text_available_count": 0,
        "official_extracted_text_candidate_count": 0,
        "answer_bearing_bounded_window_candidate_count": 0,
        "official_answer_bearing_bounded_window_candidate_count": 0,
        "scout_only_promising_url_signal_count": 0,
        "best_observed_candidate_ref": {},
        "raw_private_retention_false": True,
        "closed_surface_flags": _closed_surface_flags(),
    }
    if result.return_code != 0:
        diagnostic["acquisition_quality_bucket"] = (
            QUALITY_UNAVAILABLE if credential_unavailable else QUALITY_FAILED
        )
        return diagnostic

    payload = _read_json(provider_response_path)
    payload_results = [
        _safe_mapping(item)
        for item in payload.get("results", [])
        if isinstance(item, Mapping)
    ][:MAX_RESULTS]
    result_diagnostics = [
        _candidate_diagnostic(
            provider=provider,
            item=item,
            relation_plan=relation_plan,
            acquisition_plan=acquisition_plan,
        )
        for item in payload_results
    ]
    diagnostic["results_returned"] = len(result_diagnostics)
    diagnostic["url_bound_result_count"] = sum(
        1 for item in result_diagnostics if item["url_bound_result"]
    )
    diagnostic["official_source_of_record_looking_result_count"] = sum(
        1
        for item in result_diagnostics
        if item["official_source_of_record_looking"]
    )
    diagnostic["extracted_text_available_count"] = sum(
        1 for item in result_diagnostics if item["extracted_text_available"]
    )
    diagnostic["official_extracted_text_candidate_count"] = sum(
        1
        for item in result_diagnostics
        if item["official_source_of_record_looking"] and item["extracted_text_available"]
    )
    diagnostic["answer_bearing_bounded_window_candidate_count"] = sum(
        1 for item in result_diagnostics if item["answer_bearing_bounded_window"]
    )
    diagnostic["official_answer_bearing_bounded_window_candidate_count"] = sum(
        1
        for item in result_diagnostics
        if item["official_answer_bearing_bounded_window"]
    )
    diagnostic["scout_only_promising_url_signal_count"] = (
        diagnostic["official_source_of_record_looking_result_count"]
        if provider in SCOUT_ONLY_PROVIDERS
        else 0
    )
    diagnostic["best_observed_candidate_ref"] = _best_candidate_ref(
        result_diagnostics
    )
    diagnostic["result_diagnostics"] = result_diagnostics
    diagnostic["raw_private_retention_false"] = (
        payload.get("raw_provider_payload_retained") is False
        and payload.get("raw_search_response_retained") is False
        and all(
            item.get("raw_provider_payload_retained") is False
            and item.get("raw_search_response_retained") is False
            for item in payload_results
        )
    )
    diagnostic["acquisition_quality_bucket"] = _quality_bucket(diagnostic)
    return diagnostic


def _candidate_diagnostic(
    *,
    provider: str,
    item: Mapping[str, Any],
    relation_plan: Mapping[str, Any],
    acquisition_plan: Mapping[str, Any],
) -> dict[str, Any]:
    url = _clean_text(item.get("url"), limit=700) or ""
    domain = _clean_domain(item.get("domain")) or urlparse(url).netloc.lower()
    official = _domain_matches_constraints(domain, DOMAIN_CONSTRAINTS)
    extracted_text = _clean_text(item.get("provider_extracted_text"), limit=20_000)
    selection = (
        dogfood._bounded_plan_text_selection(
            extracted_text,
            relation_plan=relation_plan,
            acquisition_plan=acquisition_plan,
        )
        if extracted_text
        else None
    )
    candidate_for_score = {
        "result_rank": _bounded_int(item.get("result_rank"), default=999),
        "fetch_read_priority_rank": _bounded_int(
            item.get("result_rank"),
            default=999,
        ),
        "candidate_selection_features": {
            "source_of_record_domain_signal": official,
            "official_domain_signal": official,
            "public_agency_domain_signal": official,
        },
    }
    score = (
        dogfood._candidate_window_score(candidate_for_score, selection)
        if selection
        else ()
    )
    answer_bearing = bool(
        selection
        and selection.matched_value_token_kind_count > 0
        and selection.matched_anchor_count > 0
    )
    selection_metadata = selection.to_metadata() if selection else {}
    if selection_metadata:
        selection_metadata.pop("bounded_text", None)
    return {
        "provider": provider,
        "title": _clean_text(item.get("title"), limit=220),
        "url": url,
        "domain": domain,
        "result_rank": _bounded_int(item.get("result_rank"), default=0),
        "provider_call_index": _bounded_int(
            item.get("provider_call_index"),
            default=1,
        ),
        "url_bound_result": _is_valid_http_url(url),
        "official_source_of_record_looking": official,
        "extracted_text_available": bool(extracted_text),
        "provider_extracted_text_char_count": _bounded_int(
            item.get("provider_extracted_text_char_count"),
            default=len(extracted_text or ""),
        ),
        "provider_extracted_text_digest": _clean_text(
            item.get("provider_extracted_text_digest")
            or item.get("provider_extracted_source_text_digest"),
            limit=128,
        ),
        "answer_bearing_bounded_window": answer_bearing,
        "official_answer_bearing_bounded_window": bool(answer_bearing and official),
        "bounded_window_score": list(score),
        "bounded_window_selection_metadata": selection_metadata,
        "not_evidence": True,
        "not_citation_eligible": True,
        "not_source_obligation_satisfaction": True,
        "source_authority_created": False,
    }


def _quality_bucket(diagnostic: Mapping[str, Any]) -> str:
    if not diagnostic.get("provider_available"):
        return (
            QUALITY_UNAVAILABLE
            if diagnostic.get("credential_unavailable")
            else QUALITY_FAILED
        )
    if diagnostic.get("scout_only"):
        if _bounded_int(diagnostic.get("scout_only_promising_url_signal_count")):
            return QUALITY_SCOUT_ONLY
        return QUALITY_NO_USEFUL
    if _bounded_int(diagnostic.get("official_answer_bearing_bounded_window_candidate_count")):
        return QUALITY_OFFICIAL_ANSWER
    if _bounded_int(diagnostic.get("official_extracted_text_candidate_count")):
        return QUALITY_OFFICIAL_NOT_ANSWER
    if _bounded_int(diagnostic.get("answer_bearing_bounded_window_candidate_count")):
        return QUALITY_NON_OFFICIAL_ANSWER
    return QUALITY_NO_USEFUL


def _select_provider(provider_diagnostics: Sequence[Mapping[str, Any]]) -> str | None:
    eligible: list[tuple[tuple[int, ...], int, str]] = []
    for order_index, diagnostic in enumerate(provider_diagnostics):
        if diagnostic.get("provider") not in EXTRACTION_CAPABLE_PROVIDERS:
            continue
        if diagnostic.get("raw_private_retention_false") is not True:
            continue
        if diagnostic.get("acquisition_quality_bucket") != QUALITY_OFFICIAL_ANSWER:
            continue
        best = _safe_mapping(diagnostic.get("best_observed_candidate_ref"))
        score = tuple(
            _bounded_int(item, default=0)
            for item in _safe_sequence(best.get("bounded_window_score"))
        )
        eligible.append((score, -order_index, str(diagnostic["provider"])))
    if not eligible:
        return None
    return max(eligible)[2]


def _best_candidate_ref(
    result_diagnostics: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    candidates = [
        item
        for item in result_diagnostics
        if item.get("extracted_text_available") and item.get("url_bound_result")
    ]
    if not candidates:
        official_urls = [
            item for item in result_diagnostics if item.get("official_source_of_record_looking")
        ]
        if not official_urls:
            return {}
        item = official_urls[0]
        return {
            "provider": item.get("provider"),
            "title": item.get("title"),
            "url": item.get("url"),
            "domain": item.get("domain"),
            "result_rank": item.get("result_rank"),
            "scout_or_url_signal_only": True,
        }
    item = max(
        candidates,
        key=lambda candidate: tuple(
            _bounded_int(score, default=0)
            for score in _safe_sequence(candidate.get("bounded_window_score"))
        ),
    )
    return {
        "provider": item.get("provider"),
        "title": item.get("title"),
        "url": item.get("url"),
        "domain": item.get("domain"),
        "result_rank": item.get("result_rank"),
        "official_source_of_record_looking": item.get(
            "official_source_of_record_looking"
        ),
        "answer_bearing_bounded_window": item.get("answer_bearing_bounded_window"),
        "official_answer_bearing_bounded_window": item.get(
            "official_answer_bearing_bounded_window"
        ),
        "provider_extracted_text_char_count": item.get(
            "provider_extracted_text_char_count"
        ),
        "provider_extracted_text_digest": item.get("provider_extracted_text_digest"),
        "bounded_window_score": item.get("bounded_window_score"),
        "bounded_window_selection_metadata": item.get(
            "bounded_window_selection_metadata"
        ),
    }


def _decision_packet(
    *,
    run_id: str,
    provider_diagnostics: Sequence[Mapping[str, Any]],
    selected_provider: str | None,
    blocker: str | None,
) -> dict[str, Any]:
    providers_attempted = [
        str(item.get("provider"))
        for item in provider_diagnostics
        if item.get("provider_call_attempted")
    ]
    credentials_unavailable = [
        str(item.get("provider"))
        for item in provider_diagnostics
        if item.get("credential_unavailable")
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_name": PHASE_NAME,
        "run_id": run_id,
        "created_at": _observed_at(),
        "request_kind": "source_of_record_recovery_provider_decision",
        "comparison_job": {
            "query": FIXED_COMPARISON_QUERY,
            "domain_constraints": list(DOMAIN_CONSTRAINTS),
            "max_results": MAX_RESULTS,
            "provider_order": list(PROVIDER_ORDER),
            "manual_browser_source_lookup_used": False,
            "fetch_read_used": False,
            "dprime_model_calls_used": False,
            "fap_used": False,
            "author_used": False,
            "broker_doorman_used": False,
        },
        "provider_role": SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER_ROLE,
        "provider_role_decision_scope": "source_of_record_recovery_acquisition_only",
        "not_global_provider_default": True,
        "providers_attempted": providers_attempted,
        "credentials_unavailable": credentials_unavailable,
        "provider_call_counts": {
            "total_logical_provider_calls_attempted": sum(
                _bounded_int(item.get("provider_calls_attempted"))
                for item in provider_diagnostics
            ),
            "total_logical_provider_calls_completed": sum(
                _bounded_int(item.get("provider_calls_completed"))
                for item in provider_diagnostics
            ),
            "fetch_read_calls": 0,
            "model_calls": 0,
            "broker_doorman_calls": 0,
            "manual_browser_or_source_lookup_calls": 0,
        },
        "provider_diagnostics": list(provider_diagnostics),
        "quality_bucket_by_provider": {
            str(item.get("provider")): item.get("acquisition_quality_bucket")
            for item in provider_diagnostics
        },
        "best_observed_official_answer_bearing_extracted_candidate": (
            _best_official_answer_bearing_candidate(provider_diagnostics)
        ),
        "selected_source_of_record_recovery_extraction_provider": selected_provider,
        "selected_provider_role": (
            SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER_ROLE
            if selected_provider
            else None
        ),
        "decision_blocker": blocker,
        "selection_rule": {
            "provider_must_be_extraction_capable": True,
            "provider_must_return_url_bound_extracted_text": True,
            "official_source_of_record_looking_required": True,
            "official_answer_bearing_bounded_window_required": True,
            "raw_private_retention_must_remain_false": True,
            "scout_only_providers_cannot_win": True,
        },
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
        "raw_private_retention": False,
        "closed_surface_flags": _closed_surface_flags(),
    }


def _best_official_answer_bearing_candidate(
    provider_diagnostics: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    candidates: list[Mapping[str, Any]] = []
    for provider in provider_diagnostics:
        candidates.extend(
            item
            for item in _safe_sequence(provider.get("result_diagnostics"))
            if isinstance(item, Mapping)
            and item.get("official_answer_bearing_bounded_window")
        )
    if not candidates:
        return {}
    best = _best_candidate_ref(candidates)
    return best


def _blocked_confirmation_packet(*, run_id: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_name": PHASE_NAME,
        "run_id": run_id,
        "created_at": _observed_at(),
        "request_kind": "source_of_record_recovery_provider_decision",
        "decision_blocker": "CONFIRM_LIVE_PROVIDER_COMPARISON_REQUIRED",
        "providers_attempted": [],
        "provider_call_counts": {
            "total_logical_provider_calls_attempted": 0,
            "total_logical_provider_calls_completed": 0,
            "fetch_read_calls": 0,
            "model_calls": 0,
            "broker_doorman_calls": 0,
            "manual_browser_or_source_lookup_calls": 0,
        },
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
        "raw_private_retention": False,
        "closed_surface_flags": _closed_surface_flags(),
    }


def _blocked_output_packet(*, run_id: str, blocker_detail: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_name": PHASE_NAME,
        "run_id": run_id,
        "created_at": _observed_at(),
        "request_kind": "source_of_record_recovery_provider_decision",
        "decision_blocker": "PROVIDER_DECISION_PACKET_OUTPUT_UNAVAILABLE",
        "decision_blocker_detail": blocker_detail,
        "providers_attempted": [],
        "provider_call_counts": {
            "total_logical_provider_calls_attempted": 0,
            "total_logical_provider_calls_completed": 0,
            "fetch_read_calls": 0,
            "model_calls": 0,
            "broker_doorman_calls": 0,
            "manual_browser_or_source_lookup_calls": 0,
        },
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
        "raw_private_retention": False,
        "closed_surface_flags": _closed_surface_flags(),
    }


def _closed_surface_flags() -> dict[str, bool]:
    return {
        "source_authority_created": False,
        "source_obligation_satisfied": False,
        "citation_eligible": False,
        "dprime_admission_created": False,
        "fap_created": False,
        "author_created": False,
        "product_correctness_claimed": False,
        "global_provider_chooser_created": False,
        "hidden_fallback_loop_created": False,
    }


def _read_json(path: Path) -> dict[str, Any]:
    decoded = json.loads(path.read_text(encoding="utf-8"))
    return dict(decoded) if isinstance(decoded, Mapping) else {}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _prepare_output_dir(run_dir: Path) -> str | None:
    try:
        run_dir.mkdir(parents=True, exist_ok=True)
        probe = run_dir / ".provider-decision-write-test.tmp"
        probe.write_text("ok\n", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return f"provider decision packet directory unavailable: {exc}"
    return None


def _run_id(value: str | None = None) -> str:
    text = _clean_text(value, limit=120)
    if text:
        return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in text)
    return "source-of-record-recovery-provider-decision-" + datetime.now(UTC).strftime(
        "%Y%m%dT%H%M%SZ"
    )


def _run_output_dir(root: Path, output_root: str | Path, run_id: str) -> Path:
    output = Path(output_root)
    if not output.is_absolute():
        output = root / output
    return output / run_id


def _observed_at() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve())
    except OSError:
        return str(path)


def _domain_matches_constraints(domain: str, constraints: Sequence[str]) -> bool:
    clean = _clean_domain(domain) or ""
    for constraint in constraints:
        expected = _clean_domain(constraint) or ""
        if clean == expected or clean.endswith(f".{expected}"):
            return True
    return False


def _is_valid_http_url(value: Any) -> bool:
    text = _clean_text(value, limit=700)
    if not text:
        return False
    parsed = urlparse(text)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _clean_domain(value: Any) -> str | None:
    text = _clean_text(value, limit=260)
    if not text:
        return None
    parsed = urlparse(text if "://" in text else f"https://{text}")
    domain = (parsed.netloc or parsed.path).casefold().strip("/")
    return domain[4:] if domain.startswith("www.") else domain


def _bounded_int(value: Any, *, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return parsed if parsed > 0 else default


def _clean_text(value: Any, *, limit: int) -> str | None:
    if value is None or isinstance(value, Mapping | list | tuple | set | frozenset):
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_sequence(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    return list(value)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=PHASE_NAME)
    parser.add_argument(
        "--confirm-live-provider-comparison",
        action="store_true",
        help="Run the one licensed live provider comparison job.",
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    result = run_source_of_record_recovery_provider_decision_comparison(
        repo_root=args.repo_root,
        output_root=args.output_root,
        run_id=args.run_id,
        confirm_live_provider_comparison=args.confirm_live_provider_comparison,
    )
    selected = result.selected_provider or "none"
    blocker = result.blocker or "none"
    print(f"provider_decision_packet: {result.packet_path}")
    print(f"selected_provider: {selected}")
    print(f"blocker: {blocker}")
    return result.return_code


if __name__ == "__main__":
    raise SystemExit(main())
