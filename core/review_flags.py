from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class ReviewFlags:
    synth_insufficient: bool = False
    low_user_rating: bool = False
    scout_misfire: bool = False
    remediation_ineffective: bool = False
    linkup_tavily_misroute_news: bool = False
    query_redundancy: bool = False
    low_evidence_yield: bool = False
    high_scrutineer_severity: bool = False
    synth_declined_with_evidence: bool = False
    weak_retrieval_failure_card: bool = False


WEIGHTS = {
    "synth_insufficient": 0.15,
    "low_user_rating": 0.20,
    "scout_misfire": 0.15,
    "remediation_ineffective": 0.10,
    "linkup_tavily_misroute_news": 0.10,
    "query_redundancy": 0.10,
    "low_evidence_yield": 0.05,
    "high_scrutineer_severity": 0.15,
    "synth_declined_with_evidence": 0.55,
    "weak_retrieval_failure_card": 0.30,
}

HARD_FLAG_FIELDS = (
    "synth_insufficient",
    "low_user_rating",
    "scout_misfire",
    "high_scrutineer_severity",
)

REFUSAL_PATTERNS = [
    r"couldn'?t find (solid|reliable|on-point|specific)",
    r"I cannot verify",
    r"unable to (verify|locate|find|confirm)",
    r"no reliable, sourced basis",
    r"the (provided|available|supplied) (evidence|sources|material) (do(es)? not|cannot|fail)",
    r"I (don't|do not) have (enough|sufficient) (information|evidence|sources)",
    r"there is no (reliable|verified|sourced) (basis|information)",
    r"the source set (does not|fails to)",
]


def jaccard_query_overlap(queries_a: list[str], queries_b: list[str]) -> float:
    tokens_a = set(" ".join(queries_a).lower().split())
    tokens_b = set(" ".join(queries_b).lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def review_score(f: ReviewFlags) -> float:
    d = asdict(f)
    total = sum(WEIGHTS.get(k, 0) * (1.0 if d.get(k) else 0.0) for k in WEIGHTS)
    return min(1.0, total)


def should_auto_review(f: ReviewFlags) -> bool:
    """Return True if hard-flag combo or weighted score crosses 0.55.

    `synth_declined_with_evidence` alone has weight 0.55 and is intended to
    solo-fire review when other flags are clear (Phase A3).
    """
    d = asdict(f)
    hard = sum(1 for k in HARD_FLAG_FIELDS if d.get(k))
    if hard >= 2:
        return True
    return review_score(f) >= 0.55


def get_corpus_state(execution: dict[str, Any]) -> str:
    """Read corpus_state from execution / nested trace; map legacy corpus_weak."""
    v = execution.get("corpus_state")
    if v:
        return str(v)
    et = execution.get("execution_trace")
    if isinstance(et, dict) and et.get("corpus_state"):
        return str(et["corpus_state"])
    if execution.get("corpus_weak") is True:
        return "OFF_TOPIC"
    return "HEALTHY"


def output_matches_refusal(text: str) -> bool:
    """True when author text matches refusal / insufficient-evidence phrasing."""
    return any(re.search(p, (text or "").lower(), re.IGNORECASE) for p in REFUSAL_PATTERNS)


def _preview_matches_refusal(preview: str) -> bool:
    return output_matches_refusal(preview)


def feedback_overall_numeric(feedback: dict[str, Any] | None) -> int | None:
    """Map new 1-5 `overall` or legacy label to an integer, or None."""
    feedback = feedback or {}
    o = feedback.get("overall")
    if o is not None:
        try:
            v = int(o)
            if 1 <= v <= 5:
                return v
        except (TypeError, ValueError):
            pass
    u = feedback.get("user_rating")
    if u in ("Poor", "Fair", "Good", "Excellent"):
        return {"Poor": 1, "Fair": 2, "Good": 4, "Excellent": 5}.get(u)
    return None


def compute_review_flags(execution: dict[str, Any], feedback: dict[str, Any] | None) -> ReviewFlags:
    feedback = feedback or {}
    f = ReviewFlags()
    overall_n = feedback_overall_numeric(feedback)

    if execution.get("synth_was_insufficient") is True:
        f.synth_insufficient = True

    if (overall_n is not None and overall_n <= 2) or feedback.get("user_rating") in ("Poor", "Fair"):
        f.low_user_rating = True

    if execution.get("scout_fired"):
        sc = feedback.get("scout_contribution")
        if sc is not None and int(sc) < 3:
            f.scout_misfire = True
        elif feedback.get("scout_helpful") is False:
            f.scout_misfire = True
        elif overall_n is not None and overall_n <= 2:
            f.scout_misfire = True
        elif feedback.get("user_rating") in ("Poor", "Fair"):
            f.scout_misfire = True

    if (
        execution.get("supplemental_ran")
        and execution.get("delta_urls_supplemental", 0) < 2
        and execution.get("synth_was_insufficient")
    ):
        f.remediation_ineffective = True

    if execution.get("intent") == "news" and execution.get("pass_providers"):
        for p in execution["pass_providers"]:
            if p and "tavily" not in p:
                f.linkup_tavily_misroute_news = True
                break

    q1 = execution.get("queries_iter1") or []
    q2 = execution.get("queries_iter2") or []
    if q1 and q2 and jaccard_query_overlap(q1, q2) > 0.7:
        f.query_redundancy = True

    tc = int(execution.get("total_chunks_embedded") or 0)
    if tc < 15 and execution.get("complexity") in ("medium", "high"):
        f.low_evidence_yield = True

    if int(execution.get("scrutineer_high_flags", 0) or 0) > 0:
        f.high_scrutineer_severity = True

    corpus_state = get_corpus_state(execution)
    fc = execution.get("failure_card")
    if not isinstance(fc, dict):
        fc = {}
    fc_show = bool(fc.get("show"))
    cw = execution.get("corpus_weak") is True
    if fc_show and (
        corpus_state in ("OFF_TOPIC", "WEAK")
        or (cw and corpus_state not in ("ESTIMATE_FROM_PRIORS", "HEALTHY"))
    ):
        f.weak_retrieval_failure_card = True

    preview = (execution.get("final_output_preview") or "").lower()
    if "useful_content" in execution:
        useful = execution["useful_content"]
    else:
        useful = True
    try:
        chunks = int(execution.get("total_chunks_embedded") or 0)
    except (TypeError, ValueError):
        chunks = 0

    if (
        chunks >= 50
        and corpus_state != "OFF_TOPIC"
        and (_preview_matches_refusal(preview) or useful is False)
    ):
        f.synth_declined_with_evidence = True

    return f


def load_feedback_for_session(feedback_path: Path, session_id: str) -> dict[str, Any]:
    """Latest feedback line for this session, or empty dict.

    Picks the last line in file order for this session, or the entry with the
    greatest `timestamp_utc` when both have ISO timestamps. (Plain `timestamp`
    alone is an unreliable total order.)
    """
    if not session_id or not feedback_path.exists():
        return {}
    last_for_session: dict[str, Any] | None = None
    try:
        for line in feedback_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            if o.get("event") == "feedback" and o.get("session_id") == session_id:
                last_for_session = o
    except Exception:
        return {}
    if not last_for_session:
        return {}
    o = last_for_session
    return {
        "user_rating": o.get("user_rating"),
        "user_notes": o.get("user_notes"),
        "scout_helpful": o.get("scout_helpful"),
        "run_id": o.get("run_id"),
        "overall": o.get("overall"),
        "answer_completeness": o.get("answer_completeness"),
        "evidence_quality": o.get("evidence_quality"),
        "output_precision": o.get("output_precision"),
        "scout_contribution": o.get("scout_contribution"),
        "overall_auto": o.get("overall_auto"),
        "timestamp_utc": o.get("timestamp_utc"),
    }


def feedback_saved_fingerprint(fb: dict[str, Any] | None) -> str:
    """Stable string so we can tell when the on-disk line for a session changed."""
    if not fb:
        return ""
    payload = {k: fb.get(k) for k in (
        "answer_completeness",
        "evidence_quality",
        "output_precision",
        "scout_contribution",
        "overall",
        "user_notes",
        "user_rating",
        "timestamp_utc",
    )}
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str)


def recent_recurring_kb_hints(
    kb_path: Path, limit: int = 20, max_display: int = 5
) -> list[str]:
    """Last `limit` kb trigger lines, suggested_action for likely-recurring."""
    if not kb_path.exists():
        return []
    out: list[str] = []
    try:
        lines = kb_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        kb = o.get("kb_review")
        if not isinstance(kb, dict):
            continue
        if kb.get("recurrence_risk") != "likely-recurring":
            continue
        sa = kb.get("suggested_action")
        if isinstance(sa, dict):
            d = (sa.get("detail") or "").strip()
        else:
            d = ""
        if d:
            out.append(d)
    if len(out) > max_display:
        out = out[-max_display:]
    return out


def kb_insights_data(kb_path: Path, execution_log_path: Path) -> dict[str, Any]:
    """
    Returns counts and aggregates for the KB Insights sidebar.
    total_runs: lines in execution log with event execution.
    flagged: kb lines where fired is True and kb_review present.
    """
    from collections import Counter

    out: dict[str, Any] = {
        "total_runs": 0,
        "total_flagged": 0,
        "total_positive_review": 0,
        "failure_class_counts": Counter(),
        "suggested_action_type_counts": Counter(),
        "last_recurring": [],
    }
    if execution_log_path.exists():
        try:
            for line in execution_log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                if o.get("event") == "execution":
                    out["total_runs"] += 1
        except Exception:
            pass

    if not kb_path.exists():
        return out

    last_recur: list[dict[str, Any]] = []
    try:
        for line in kb_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            if o.get("review_type") == "positive" and o.get("kb_review"):
                out["total_positive_review"] += 1
                continue
            if o.get("fired") is True:
                out["total_flagged"] += 1
            kb = o.get("kb_review")
            if not isinstance(kb, dict) or o.get("fired") is not True:
                continue
            for fc in kb.get("failure_classes") or []:
                if isinstance(fc, str) and fc.strip():
                    out["failure_class_counts"][fc] += 1
            sa = kb.get("suggested_action")
            if isinstance(sa, dict):
                t = (sa.get("type") or "").strip()
                if t:
                    out["suggested_action_type_counts"][t] += 1
            if kb.get("recurrence_risk") == "likely-recurring" and isinstance(sa, dict):
                last_recur.append(
                    {
                        "query": o.get("query", "")[:80],
                        "recurrence_risk": kb.get("recurrence_risk"),
                        "detail": (sa or {}).get("detail", "") if isinstance(sa, dict) else "",
                        "summary": (kb.get("summary") or "")[:200],
                    }
                )
    except Exception:
        return out
    out["last_recurring"] = last_recur[-3:]
    return out


def performance_insights(execution_log_path: Path, feedback_path: Path) -> dict[str, Any]:
    """
    Aggregate metrics for Review Mode: execution traces + human ratings.
    """
    from collections import defaultdict

    out: dict[str, Any] = {
        "total_runs": 0,
        "with_rating": 0,
        "pct_overall_at_least_4": None,
        "executions_with_synth_flag": 0,
        "pct_synth_sufficient_first_pass": None,
        "scout_fired_rated": 0,
        "pct_scout_contrib_at_least_4": None,
        "latency_by_mode": {},
        "overall_last_10": [],
    }
    executions: list[dict[str, Any]] = []
    if execution_log_path.exists():
        for line in execution_log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            if o.get("event") == "execution":
                executions.append(o)
    out["total_runs"] = len(executions)
    if not executions:
        return out

    by_mode: dict[str, list[float]] = defaultdict(list)
    for e in executions:
        m = str(e.get("mode") or "?")
        if e.get("latency_seconds") is not None:
            try:
                by_mode[m].append(float(e["latency_seconds"]))
            except (TypeError, ValueError):
                pass
    for m, arr in by_mode.items():
        out["latency_by_mode"][m] = round(sum(arr) / len(arr), 2) if arr else 0.0

    def _synth_field(e: dict) -> bool | None:
        v = e.get("synth_sufficient_first_pass")
        if v is None and e.get("execution_trace"):
            v = (e.get("execution_trace") or {}).get("synth_sufficient_first_pass")
        return v

    sfp_runs = [e for e in executions if _synth_field(e) is not None]
    out["executions_with_synth_flag"] = len(sfp_runs)
    if sfp_runs:
        good = [e for e in sfp_runs if _synth_field(e) is True]
        out["pct_synth_sufficient_first_pass"] = round(100.0 * len(good) / len(sfp_runs), 1)

    if not feedback_path.exists():
        return out

    feedback_by_run: dict[str, dict] = {}
    for line in feedback_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get("event") != "feedback" or not o.get("run_id"):
            continue
        # last line for run_id wins (append order)
        feedback_by_run[str(o["run_id"])] = o

    rated: list[tuple[dict, dict]] = []  # (fb, exec) — exec may be missing
    for rid, fb in feedback_by_run.items():
        on = feedback_overall_numeric(fb)
        if on is not None:
            ex = next((e for e in reversed(executions) if str(e.get("run_id")) == rid), None)
            rated.append((fb, ex))
    out["with_rating"] = len(rated)
    if rated:
        g4 = [fb for fb, ex in rated if (feedback_overall_numeric(fb) or 0) >= 4]
        out["pct_overall_at_least_4"] = round(100.0 * len(g4) / len(rated), 1)
    # Last 10 rated in file order: collect in order, filter to those with overall
    ordered: list[dict] = []
    for line in feedback_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get("event") != "feedback":
            continue
        on = feedback_overall_numeric(o)
        if on is not None:
            ordered.append({**o, "_on": on})
    if ordered:
        out["overall_last_10"] = [x["_on"] for x in ordered[-10:]]
    # Scout success: among runs where scout_fired and feedback has scout_contribution
    sc_r: list[dict] = [
        f
        for f in feedback_by_run.values()
        if f.get("scout_contribution") is not None
    ]
    exec_by_run = {str(e.get("run_id")): e for e in executions}
    scout_c: list[dict] = [f for f in sc_r if (exec_by_run.get(str(f.get("run_id"))) or {}).get("scout_fired")]
    out["scout_fired_rated"] = len(scout_c)
    if scout_c:
        ok = sum(1 for f in scout_c if int(f.get("scout_contribution") or 0) >= 4)
        out["pct_scout_contrib_at_least_4"] = round(100.0 * ok / len(scout_c), 1)
    return out
