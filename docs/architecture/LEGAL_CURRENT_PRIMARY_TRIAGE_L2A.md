# L2A Legal/current-primary source failure triage

## Status

Architecture/diagnostic summary only. This note does not implement provider,
query, prompt, ranking, handoff, runtime, controller, or final-answer behavior
changes.

Inputs reviewed were the sanitized AG-41 packets under `outputs/ag41` plus
committed architecture and validation notes. Raw provider payloads, traces,
logs, DB rows, caches, prompts, secrets, private packets, and live calls were
not inspected.

## Executive summary

AG-41 legal/current-primary failures are best classified as a legal source
quality side track, not as a new controller-loop regression.

The controller made most gaps diagnosable:

- CTA/FinCEN: source-class recovery fired, but the result stayed off-domain and
  `recovery_source_quality_status` was `no_relevant_sources`.
- OSHA heat: the answer stopped with caveat on secondary evidence, but no
  missing official/current source class or active source-class recovery was
  visible.
- EU AI Act: source-class recovery generally fired and EUR-Lex was visible and
  cited, but official EU legal sources were tiered as `unknown` and secondary
  sources carried too much legal burden in some answers.
- SSDI: positive control. Official eCFR/Federal Register sources were visible
  and cited.

This should not block controller-loop consolidation unless a phase explicitly
claims to fix legal retrieval, legal source classification, or legal citation
survival.

## Case classification

Failure numbers:

1. source-class need not detected
2. recovery not triggered
3. recovery triggered but no official candidates returned
4. official candidates returned but rejected/misclassified
5. accepted official sources not visible in final evidence
6. visible official sources not cited in final answer
7. source unavailable from current provider stack
8. query/domain strategy insufficient
9. requires source-specific official resolver/API
10. final answer posture too confident despite missing official source

| Case | Outcome | Classification | Category |
|---|---|---|---|
| CTA / FinCEN BOI status | Recovery fired, but no relevant official source was visible and the final answer safely refused to answer. | 3, 8; possible 7/9 only after repeated sanitized diagnostics | B/E |
| OSHA heat illness prevention | Official/current source need was not visible; recovery did not fire before caveated stop on secondary sources. | 1, 2, 8; possible 7/9 only after bounded diagnostics | A/B/D/E |
| EU AI Act dates | EUR-Lex was recovered, visible, and cited, but official tiering and source dominance were weak. | 4 minor | C/D/E |
| EU AI Act milestone concepts | Positive legal/current control; EUR-Lex cited and answer handled non-conflict correctly. | 4 minor only because EUR-Lex tier was `unknown` | C/E |
| EU AI Act high-risk requirements | Official source visible/cited, but answer leaned on secondary sources and admitted the legal test was not fully reproduced. | 4; final citation/source-dominance weakness | C/D/E |
| SSDI eligibility | Positive control with official eCFR/Federal Register citations. | No material failure | E |

## Pattern

The failures cluster around:

- trigger/detection for OSHA heat;
- provider/query/domain acquisition for CTA/FinCEN;
- official-source classification and final-source dominance for EU AI Act;
- not conflict-state production, weak-corpus recovery, targeted retrieval
  ownership, or protected handoff behavior.

AG-41 does not expose the full L1
`source_class_recovery_validation_l1` bottleneck fields. Therefore L2A cannot
reliably distinguish no provider candidates from candidates rejected, accepted
sources not visible, or visible official sources not finally cited except where
the final sanitized sources make that obvious.

## Product standard

For legal/current/regulatory questions, ProPlex should be good-enough rather
than a full legal research platform:

- prefer official/current/primary sources;
- cite official sources when found;
- distinguish legal text from interpretation;
- caveat clearly when official/current support is missing;
- avoid confident legal, eligibility, deadline, or compliance claims when
  official/current support is unavailable.

CTA met the caveat standard but failed source acquisition. OSHA partially met
the caveat standard but should have attempted official-source recovery. EU AI
Act met the substantive standard better, but should classify and foreground
official EU legal text more reliably.

## Recommended next phase

Run L2B - Sanitized legal source recovery diagnostics contract.

Scope: expose or collect enough sanitized L1 fields for a small
legal/current-primary case set to distinguish trigger, eligibility, provider
candidates, accepted official sources, classification, evidence visibility,
final citation survival, and final answer posture.

Stop if the phase needs raw traces, provider payloads, DB rows, caches, logs,
prompts, secrets, unapproved live calls, or implementation changes to answer the
diagnostic question.

## Non-recommendations

Do not patch provider routing, provider selection, search depth, provider APIs,
query/domain tuning, source-specific adapters, prompts, ranking, evidence
visibility, final-answer cleanup, controller-loop authority, targeted retrieval
ownership, weak-corpus recovery, conflict-state production, or protected
Analyst/Economist/Author/Scrutineer handoffs based on L2A.

Do not treat CTA/OSHA/EU AI Act legal source quality as a controller-loop
consolidation blocker unless a later phase explicitly scopes legal retrieval
repair.
