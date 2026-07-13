Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96_CURRENT_STATE_AND_NEXT_CHOICES).

# AG-96 Current State And Next Choices

## Status

This note records the repo-visible AG-96 state after the AG-96C
`SearchWorkPlan` shadow lane and AG-96I3 scout/read verification lane. It is a
guidance snapshot only. It is not a ChatGPT Project Source file and does not
authorize runtime behavior changes.

Post-#342 checkpoint note: AG-96 followup surfaces, the SearchWorkPlan shadow,
offline SearchExecutor bridge, source-class recovery bridges, and broad pipeline
orchestrator paths are legacy/passive/closed unless explicitly reopened. The
current productization next gate is
`AG-SEMANTIC-OBSERVATION-ADMISSION-BRIDGE-01`, not an AG-96 follow-up,
SearchWorkPlan, Specialist, Scrutineer, or partial-answer readiness phase.

## AG-96C SearchWorkPlan Lane

AG-96C currently models `SearchWorkPlan` as a passive RunKernel shadow
projection. The runtime callsite constructs and reduces shadow state after
RunAuthority contract synthesis, but the projection is explicitly unconsumed by
QueryPlan.

Current boundary:

- QueryPlan still owns executable query identity, ordering, and admission.
- Provider selection, search depth, retrieval, prompts, citations, final
  answers, and mode policy are unchanged.
- The runtime shadow projection is useful for future authority-collapse work but
  is not an active product behavior surface.

## AG-96I3 Scout/Read Lane

AG-96I3 has built the diagnostic lane around official/current source recovery:
provider-neutral query shaping, freshness policy, brokered scout diagnostics,
Serper scout observation, scout-to-acquisition handoff, and offline
fetch/read-currentness verification against supplied sanitized read
observations.

Current boundary:

- Scout observations can identify verification candidates, not final evidence.
- Search-result metadata cannot prove current support for an exact claim.
- Offline read verification can mark a supplied observation as suitable for
  later admission review, but it does not admit EvidenceLedger records or create
  citation eligibility.

## Likely Next Direction

AG-96I3K should likely implement a sanitized read-observation adapter for
handoff candidates before EvidenceLedger admission-review diagnostics. The
adapter would make the transition from scout handoff candidate to verification
input explicit, reusable, and inspectable without deciding final evidence
custody.

EvidenceLedger admission-review diagnostics remain the next candidate after the
adapter because they need a stable verified-observation shape to review. Starting
with admission review would risk mixing acquisition/verification plumbing with
evidence custody decisions.

## User-Owned Roadmap Choices

SourceDoc05 and broader roadmap priority remain user-owned. Repo docs can record
decision points, options, and current boundaries, but they should not choose the
next product priority, activate EvidenceLedger admission, change citation
policy, or convert project-roadmap preferences into standing repo doctrine
without an explicit phase brief.
