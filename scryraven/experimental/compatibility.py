"""Terminal-only projection into the existing Author, Result and session consumer."""

from scryraven.experimental.contracts import InvestigatorTerminal
from scryraven.research import Analysis, ComponentAssessment, Finding
from scryraven.sources import Evidence


def terminal_analysis(terminal: InvestigatorTerminal, selected: list[Evidence]) -> Analysis:
    """Preserve the integrated analysis, qualifications, gaps, operation and stop reason.

    The terminal declares ONE support set for its integrated analysis. The legacy
    finding carries its canonical sources; Result.selected_evidence carries the
    identical exact material set. Neither representation claims per-sentence proof.
    No internal notes, obligation priorities, attention state or loop budgets cross.
    """
    coverage = []
    target = terminal.interpreted_target + "\nRequested intellectual operation: " + terminal.intellectual_operation
    if terminal.synthesis:
        text = "\n".join([
            terminal.synthesis,
            *("Qualification: " + value for value in terminal.qualifications),
            *("Conflict: " + value for value in terminal.conflicts),
        ])
        coverage.append(ComponentAssessment(
            need=target, status="qualified" if terminal.qualifications or terminal.conflicts else "supported",
            findings=[Finding(text=text, support_refs=list(dict.fromkeys(item.source_id for item in selected)))],
            limitation="",
        ))
    else:
        # Retain interpreted scope/operation even for an unable result.
        coverage.append(ComponentAssessment(need=target, status="unresolved", findings=[],
                                            limitation=terminal.stop_reason))
    coverage.extend(ComponentAssessment(need=item.portion, status="unresolved", findings=[],
                                         limitation=item.limitation) for item in terminal.unresolved)
    return Analysis(decision="supported" if terminal.posture == "supported" else "unable",
                    coverage=coverage, active_evidence_refs=list(dict.fromkeys(item.source_id for item in selected)),
                    explanation=terminal.stop_reason, next_need=None, next_need_ref=None, new_need_reason=None)
