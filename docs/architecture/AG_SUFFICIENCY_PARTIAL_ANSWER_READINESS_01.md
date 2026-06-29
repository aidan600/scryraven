# AG-SUFFICIENCY-PARTIAL-ANSWER-READINESS-01

Status: completed implementation posture for the pre-FAP readiness reducer.

Proof class: `component_harness_proof`.

Product path affected: RunKernel-reduced SufficiencyReadiness state over the
current answer contract, ComponentCoverage, admitted SemanticObservation refs,
ScrutineerReview posture, Specialist calculation posture, and follow-up budget
posture. No live provider, broker, retrieval, fetch/read, model,
FinalAnswerPacket, Author, citation eligibility, source-obligation
satisfaction, `current_answer_contract` mutation, or product correctness path
is opened.

## Result

`AG-SUFFICIENCY-PARTIAL-ANSWER-READINESS-01` introduces
`RunKernel.SufficiencyReadiness` as the deterministic pre-FAP readiness reducer.
SufficiencyReadiness is RunKernel-owned. It produces component-level and
answer-level readiness, records safe refs and caveats for later FAP hardening,
and stays out of FAP and Author authority.

The canonical state/projection/history lives under:

- `sufficiency_readiness_state`
- `sufficiency_readiness_projection`
- `sufficiency_readiness_history`

The RunKernel stage/action/observation are:

- stage: `sufficiency_readiness`
- action: `sufficiency_readiness_decide`
- observation: `sufficiency_readiness_decided`

## Taxonomy

The implemented readiness taxonomy is:

- `full_answer_ready`
- `partial_answer_ready`
- `blocked`
- `followup_required`
- `contested`
- `insufficient_evidence`
- `not_applicable`

`not_applicable` is a gating/non-phase state for absent readiness inputs, not
the lowest normal answerability status.

## Component Behavior

SufficiencyReadiness builds a component readiness map keyed by answer component
id. Each entry preserves the component id/revision/digest, materiality or role,
matching current-contract ComponentCoverage refs, admitted SemanticObservation
refs through coverage/admission lineage, Scrutineer refs, Specialist refs when
present, follow-up budget posture, `component_readiness_status`, blockers,
mandatory caveats, and prohibited upgrades.

Coverage that does not match the current answer component revision and digest is
ignored. Custody, Analyst proposals, or stale coverage refs are not support by
themselves. Required quantitative components that carry Specialist posture must
have non-contested, non-blocked Specialist calculation posture before they can
be treated as ready.

## Answer Behavior

Answer-level readiness aggregates component readiness with this priority:

- `not_applicable` when the current contract/component inputs are absent.
- `contested` when material Scrutineer, Specialist, coverage, currentness, or
  contradiction posture remains contested.
- `followup_required` when material remediation remains and follow-up budget is
  available or expected by mode.
- `blocked` when a material required component is blocked or a supported partial
  would leave a required component missing.
- `insufficient_evidence` when no answer-bearing component has admitted
  support/ComponentCoverage.
- `partial_answer_ready` when at least one answer-bearing component is ready and
  unresolved components are named, non-critical, exhausted, or safely caveatable.
- `full_answer_ready` when all answer-bearing components are ready and no
  material blocker remains.

Modes change budget and review expectations, not semantic authority. Fast has
zero follow-up budget by default. Balanced can require follow-up on material
red flags when budget is available. Deep preserves stronger blocker posture
when final verification expectations are unmet; full Deep orchestration is not
implemented here.

## FAP Handoff Preview

The reducer emits a safe `fap_handoff_preview` only. It contains readiness
status, component readiness refs, supported/blocked/missing/contested/follow-up
component refs, follow-up budget posture, mandatory caveats, and prohibited
upgrades. It does not create FinalAnswerPacket, Author input, answer prose,
citations, citation eligibility, source-obligation satisfaction, or product
correctness.

## Boundaries

SufficiencyReadiness does not create FinalAnswerPacket state, create Author
input, call Author, produce answer prose, mark citation eligibility, satisfy
source obligations, mutate `current_answer_contract`, run live calls, call
providers or brokers, run retrieval or fetch/read, call models, change provider
depth/routing, or claim product correctness.

Old AG-92C Sufficiency/FAP and AG-96/FAP/Author surfaces remain
legacy/passive/closed unless a later phase explicitly reopens them. FAP
hardening comes next, followed by Author prose-only finalization.
