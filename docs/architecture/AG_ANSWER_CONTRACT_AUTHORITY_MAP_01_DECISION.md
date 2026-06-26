# AG-ANSWER-CONTRACT-AUTHORITY-MAP-01 Decision

Status: implemented as a passive RunKernel-owned schema/projection surface after
PR #317 on main `4416cbc`. No runtime SearchExecutor wiring,
provider/search/fetch/retrieval behavior, Author behavior, prompt behavior,
citation behavior, partial-answer readiness, or live validation is licensed by
this note.

## Decision

`AG-ANSWER-CONTRACT-AUTHORITY-MAP-01` established a RunKernel-owned passive
AnswerContractAuthorityMap before runtime SearchExecutor wiring.

AnswerContractAuthorityMap ties:

- required answer components;
- delegated component-scoped search work;
- evidence, citation, and source obligations;
- SemanticObservation / ComponentCoverage support;
- SufficiencyJudgment answerability;
- FinalAnswerPacket Author-safe payload readiness;
- prose-only Author handoff.

## Recent Main Context

- PR #312 `AG-LIVE-BLOCKED-FAP-GUARD-01`: blocked FinalAnswerPacket is guarded
  before Author input derivation.
- PR #313 `AG-LIVE-BLOCKED-FAP-SAFE-SUMMARY-01`: safe blocked-FAP summaries are
  attached to failure observability.
- PR #314 `AG-PARTIAL-ANSWER-BLOCKED-SUMMARY-01`: component-level blocked-FAP
  summary telemetry exists for blocked semantic multipart/source-bound numeric
  cases.
- PR #315 `AG-COMPONENT-EXECUTOR-CONTRACT-01`: offline ComponentPlan /
  component executor contract preserves planned components into passive
  SearchWork/query-work/scorekeeping, without wiring runtime model, search,
  fetch, retrieval, or Author behavior.
- PR #317 `AG-ANSWER-CONTRACT-AUTHORITY-MAP-01`: RunKernel owns a passive
  AnswerContractAuthorityMap that observes component work, evidence custody,
  semantic coverage, Sufficiency, FinalAnswerPacket readiness, and Author-safe
  handoff posture without activating runtime SearchExecutor behavior.

## Authority Hierarchy

- RunKernel / RunAuthority remains root authority.
- AnswerContractAuthorityMap is owned by RunKernel and maps answer-component
  obligations to subordinate work and readiness owners.
- ComponentPlan is legacy/compat input terminology for subordinate
  component-search planning.
- ComponentSearchPlan is the preferred subordinate component-search planning
  name.
- SearchExecutor should eventually execute delegated component-scoped search
  work, but must not decide answerability.
- EvidenceLedger owns evidence custody, source obligations, and citation
  eligibility inputs.
- SemanticObservation / ComponentCoverage owns component support.
- SufficiencyJudgment owns answerability.
- FinalAnswerPacket owns Author-safe payload readiness.
- Author remains prose-only and consumes safe handoff material; it does not
  decide evidence custody, component support, answerability, or readiness.

## Non-Goals

- Do not wire ComponentPlan into runtime.
- Do not implement SearchExecutor.
- Do not implement partial-answer readiness.
- Do not change provider routing, retrieval, citation behavior, Author
  behavior, caps, prompts, query generation, or persistence shape.
- Do not run live validation.
- Do not access secrets, `.env`, raw provider payloads, raw prompts, raw model
  responses, DB/cache rows, private logs, full traces, output packets, `output/`,
  or unrelated artifacts.
- Do not make ComponentPlan, ComponentSearchPlan, SearchWork, QueryPlan, or
  SearchExecutor top-level authority.

## Near-Term Roadmap

1. Add the AnswerContract authority map.
2. Clean up ComponentSearchPlan naming and subordination.
3. Add the offline SearchExecutor bridge.
4. Add component-scoped source custody.
5. Bind component evidence and citations.
6. Bind Sufficiency / FinalAnswerPacket component readiness.
7. Add partial-answer readiness only after the full offline authority chain is
   testable.
8. Run live multi-component validation only after offline authority mapping,
   component binding, custody, Sufficiency, FinalAnswerPacket readiness, and
   Author-safe handoff are testable without live behavior changes.
