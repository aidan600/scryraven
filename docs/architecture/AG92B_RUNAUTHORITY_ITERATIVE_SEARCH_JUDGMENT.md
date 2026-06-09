# AG-92B RunAuthority Iterative Search Judgment

Status: implemented as a bounded RunAuthority behavior activation.

## Purpose

AG-92B makes retrieval continuation and source-class recovery judgment a
RunKernel-owned RunAuthority decision instead of a helper/controller-local
conclusion. Executors still search. Helpers still propose. Reducers commit
canonical state. Trace reports state.

The active runtime seam is post-main-retrieval and pre-source-class recovery:
the pipeline reduces the active RunAuthority contract into EvidenceLedger,
reduces runtime evidence facts, authorizes a RunAuthority search-judgment
action, executes the bounded judgment executor, reduces the observation into
RunState, and passes the reduced projection into the authoritative-source
action builder.

## Previous Owners

Before AG-92B, retrieval continuation and recovery were mainly governed by:

- source-class recovery recommendation helpers;
- answer-contract source-class gap triggers;
- retrieval-stop checkpoint/controller snapshots;
- local orchestrator branch state;
- compatibility bridges for official/canonical recovery.

Those surfaces remain as proposal and compatibility inputs. They are not the
new authority when the RunKernel search judgment is present.

## New Owner

The new owner is `RunKernel.RunAuthoritySearchJudgment`.

Core modules:

- `core/run_authority_search_judgment.py`
- `core/run_authority_search_judgment_prompt.py`
- `core/run_authority_search_judgment_validation.py`
- `core/run_authority_search_judgment_runtime.py`
- `core/run_authority_search_judgment_consumers.py`

RunKernel vocabulary:

- stage: `SEARCH_JUDGMENT_STAGE`
- action: `ActionType.SEARCH_JUDGMENT_DECIDE`
- observation: `ObservationType.SEARCH_JUDGMENT_DECIDED`
- state: `RunState.search_judgment`
- projection: `RunState.search_judgment_projection`
- history: `RunState.search_judgment_history`

Trace derives from `RunState.to_trace_projection()`.

## Decisions

Decision vocabulary:

- `STOP_SATISFIED`
- `CONTINUE_TARGETED_SEARCH`
- `RECOVER_MISSING_OFFICIAL_CURRENT`
- `RECOVER_MISSING_LEGAL_PRIMARY`
- `RECOVER_MISSING_CANONICAL`
- `RECOVER_MISSING_SOURCE_BOUND_NUMERIC`
- `ESCALATE_EXISTING_PROVIDER_OR_DEPTH`
- `BLOCK_REDUNDANT_QUERY`
- `STOP_INSUFFICIENT`
- `DEFER_TO_EXISTING_LEGACY_COMPATIBILITY`

Classification vocabulary:

- `contract_satisfied`
- `active_required_gap`
- `lower_tier_lead_only`
- `stale_or_off_topic_only`
- `useful_lead_needs_targeted_recovery`
- `redundant_query_blocked`
- `new_source_class_target_allowed`
- `budget_exhausted`
- `insufficient_but_answerable_with_caveats`
- `helper_assessment_rejected`
- `helper_assessment_promoted`

## Input And Projection

The judgment input is compact and sanitized:

- contract reference: contract id, selected templates, requirements, posture and
  recovery policy;
- EvidenceLedger reference: candidate count, requirements, custody gaps,
  candidate records, compatibility gaps;
- query facts: QueryPlan trace fragment, roles, current query lineage where safe;
- retrieval facts: counts, source-class/tier/domain summaries, provider
  diagnostic count;
- helper proposals: retrieval stop, source-class recovery, answer-contract
  handoff;
- budget: iteration, max iterations, remaining budget, recovery attempts.

The projection stores only compact state: decision, classifications,
satisfaction, gaps, redundancy, continuation, targets, recommended query
previews, helper promotion/rejection, insufficient posture, prompt hash/length,
and model identity. Raw prompt text, raw model output, raw provider payloads,
DB rows, caches, logs, full traces, output packets, and secrets are not stored.

## Deterministic And Smart Paths

Deterministic judgment always runs at the wired seam.

The optional smart-model path is controlled by
`RunConfig.run_authority_search_judgment_smart_model`, default `False`. When
enabled, it uses the injected `ask_model` callable with strict JSON output and
prompt metadata only. AG-92B tests use fakes only; no live model, provider, or
search calls are required.

The prompt frames the model as a careful research director judging the next
retrieval action against a committed contract and EvidenceLedger. It explicitly
states that the model is not an Author, search executor, citation formatter, or
unbounded provider router.

## Validation And Repair

Validation enforces:

- lower-tier evidence cannot satisfy official/current, legal/current-primary,
  canonical-doc, source-bound numeric, or user-document obligations;
- aggregate counts do not satisfy custody;
- stale/off-topic evidence cannot satisfy current/source-fit requirements;
- helper "satisfied" proposals are rejected while required EvidenceLedger gaps
  remain;
- duplicate continuation queries are blocked unless they target a new active
  gap/source class;
- `STOP_SATISFIED` is repaired when required EvidenceLedger gaps remain;
- source-bound numeric unknowns cannot be presented as supported;
- invalid model JSON falls back to deterministic judgment.

Repair falls back to deterministic authority and records validation status in
the reduced projection without storing raw model output.

## Runtime Consumer

The active consumer is the authoritative-source action path:

`pipeline_orchestrator.py`
-> `RunKernel.search_judgment_projection`
-> `build_authoritative_source_action_orchestrator_handoff()`
-> `AuthoritativeSourceActionFacts.run_search_judgment_projection`
-> `apply_search_judgment_to_source_class_recovery_recommendation()`
-> `record_source_class_recovery_lifecycle()`
-> existing source-class recovery action envelope/dispatch.

This demotes the older source-class recovery helper to advisory status when a
reduced RunAuthority search judgment is present. A recovery judgment can promote
missing source-class recovery through the existing controller contract. A
redundant-query or stop-insufficient judgment can block recovery and carry an
insufficient/partial posture.

`pipeline_orchestrator.py` remains a thin caller: it builds input, authorizes,
executes, reduces, and passes the projection. Source hierarchy policy, prompt
construction, validation, and consumer promotion/blocking live outside the
orchestrator.

## Opened Surfaces

AG-92B opens only:

- RunAuthority search-judgment prompt behavior;
- retrieval continuation/recovery decision;
- redundancy judgment;
- source-class recovery interaction;
- limited query/source-class target metadata for recovery admission;
- static guards that keep prompt/validator logic out of the orchestrator.

## Closed Surfaces

Still closed:

- live validation;
- new provider integration;
- broad provider/search/ranking/filtering rewrites;
- broad query generation/order rewrites;
- Author prose and citation formatting;
- hosted/deployment/cache behavior;
- secrets, `.env`, raw provider payloads, raw prompts, DB rows, private logs,
  caches, full raw traces, output packets, and private artifacts.

## No-Live-Validation Posture

Implementation and tests are offline. The production code supports injected
model judgment, but default configuration keeps it disabled and the tests use
fake `ask_model` only.

## Remaining Work

AG-92C should add the RunAuthority sufficiency judge that decides final answer
sufficiency/posture after recovery and before Author execution. AG-92B supplies
the iterative search judgment and an active source-class recovery consumer, but
does not rewrite Author prose, citation formatting, or broad final-answer style.
