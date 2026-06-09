# AG-91J EvidenceLedger / Source Custody Under RunKernel

Status: implementation complete; high-custody authority migration; no live validation

Branch: `codex/ag91j-evidence-ledger-runkernel`
Base: updated `main` after merged PR #115 / AG-91I

## Purpose

AG-91J moves source/evidence custody into canonical RunKernel-owned state. The
phase does not finish FinalAnswerPacket or Author migration, but it gives future
RunAuthority judgment a deterministic EvidenceLedger instead of scattered
aggregate summaries, helper assessments, final-bundle-only evidence, and trace
mirrors.

Target shape:

1. Retrieval/source-obligation observations enter the RunKernel.
2. RunKernel reduces sanitized observations into `RunState.evidence_ledger`.
3. The ledger records candidate identity, dispositions, source requirements,
   candidate links, and explicit custody gaps.
4. Runtime consumers read ledger-linked state.
5. Trace/export projects ledger state and does not decide custody separately.

## Old Custody Owners

Before AG-91J, source/evidence custody was spread across several surfaces:

- `ControllerEvidenceLedger` recorded Controller-era custody events and legacy
  gaps. It had useful vocabulary but remained Controller/projection shaped.
- `allocation_result_candidate_custody` admitted AG-75 allocation results as
  Controller evidence inputs.
- `OfficialCurrentSourceCustodyState` represented official/current source
  requirements, but it was a narrower projection rather than the full candidate
  custody owner.
- source-class recovery and AnswerContract handoff could treat source-class or
  tier counts as source-obligation evidence.
- final evidence assembly selected sources before there was a RunKernel
  candidate-custody owner for those selections.

Aggregate counts and helper/controller assessments are now explicitly
insufficient for custody unless a deterministic ledger reducer links candidate
identity and disposition to a source requirement.

## New Owner

The canonical owner is `core.evidence_ledger.EvidenceLedger`, stored as
`RunState.evidence_ledger` in `core.run_kernel`.

The ledger records compact, sanitized, JSON-safe state:

- candidate identity: stable candidate id, URL or normalized identity, title,
  domain/label, provider/source origin, retrieval/query/action provenance,
  source tier/class/currentness, readability/fetchability, final-evidence
  eligibility, contextual/lower-tier status, and stronger-obligation
  eligibility;
- candidate custody records: fact, helper assessment, or proposal, with
  accepted/partial/rejected/contextual/lower-tier/unreadable/unfetchable/dropped
  dispositions and reasons;
- source requirements: requirement id, requirement kind, originating
  AnswerContract/source obligation reference, required class/tier/currentness,
  linked candidate ids, status, reason, and aggregate-count-insufficient flag;
- source-obligation links from requirements to candidate ids;
- custody gaps for missing identity, missing readable source, missing
  source-class fit, missing official/current candidate, legacy aggregate-only
  path, non-promotable helper/controller assessment, dropped candidate without
  disposition, final evidence without ledger custody, missing source-bound
  value, and unsupported numeric value.

The projection shape is `evidence_ledger_ag91j_v1` with owner
`RunKernel.EvidenceLedger`, `canonical_state: true`, and explicit
`trace_only: false` / `storage_only: false` flags.

## RunKernel Integration

`core.run_kernel` adds:

- `EVIDENCE_LEDGER_STAGE = "evidence_ledger"`;
- `ActionType.EVIDENCE_LEDGER_REDUCE`;
- `ObservationType.EVIDENCE_CUSTODY_OBSERVED`;
- `RunState.evidence_ledger`;
- `RunKernel.authorize_evidence_ledger_reduction(...)`;
- reduction semantics that apply observations to `RunState.evidence_ledger`
  and store the resulting ledger projection under `state.projections`.

`core.evidence_ledger_runtime` is a tiny executor adapter. It validates the
authorized RunKernel action and wraps sanitized payloads as observations. It
does not classify sources, choose evidence, call providers, call models, or
decide obligations.

`KernelTraceProjection` includes `evidence_ledger`, derived from
`RunState.evidence_ledger.to_projection()`.

## Runtime Consumers

AG-91J adds real consumers beyond trace/export:

- `answer_contract_runtime_handoff` consumes
  `source_class_facts_from_evidence_ledger_projection(...)`. When a ledger
  projection has requirement facts, AnswerContract source-class present/missing
  state comes from ledger-linked requirements rather than source-tier counts.
  Aggregate official counts no longer satisfy official/current obligations.
- final answer runtime assembly carries `evidence_ledger_projection` into the
  final-answer packet path where available.
- `final_answer_runtime_adapter` recognizes a RunKernel EvidenceLedger
  projection, derives official/current source obligations from its subordinate
  official/current projection, records ledger candidate/requirement/gap counts,
  and adds a prohibited upgrade when final evidence was selected without ledger
  custody.

Trace/export also reads the ledger projection, but it is not the only consumer.

## Compatibility-Only Surfaces

`ControllerEvidenceLedger` remains available for AG-74 compatibility, but now
exports `run_kernel_compatibility_status:
compatibility_only_subordinate_to_run_kernel_evidence_ledger_ag91j`.

`allocation_result_candidate_custody` remains a sanitized AG-75 input/projection
helper and exports `run_kernel_compatibility_status:
sanitized_observation_input_for_run_kernel_evidence_ledger_ag91j`.

`OfficialCurrentSourceCustodyState` remains as a subordinate projection emitted
from the EvidenceLedger. It no longer needs to be treated as the full custody
owner for AG-91J surfaces.

Aggregate-only source paths are demoted. The ledger preserves counts as
compatibility/gap facts, but `aggregate_counts_are_authoritative_for_custody`
is false and aggregate counts cannot satisfy source requirements.

Final evidence selected before ledger custody is represented as a compatibility
gap, not as proof of custody.

## Protected Surfaces Opened

AG-91J opened and changed:

- evidence custody model and projection;
- candidate disposition vocabulary and deterministic promotion rules;
- source requirement/source-obligation linkage;
- official/current source satisfaction guardrails;
- source-class/currentness/source-fit checks needed to prevent weak/stale/social
  sources from satisfying stronger obligations;
- AnswerContract source-obligation consumption of ledger-linked state;
- final-answer packet custody awareness for ledger compatibility gaps;
- static guards around aggregate-only and projection-only custody authority.

## Protected Surfaces Kept Closed

AG-91J did not change:

- live provider/model/search calls;
- provider integrations or provider swap behavior;
- broad query strategy/finalization/order behavior;
- retrieval ranking/filtering beyond custody observation admission;
- Author prose, prompt text, or citation formatting style;
- hosted/deployment/cache behavior;
- secrets, `.env`, raw provider payloads, raw prompts, DB rows, private logs,
  caches, full raw traces, local output packets, or private artifacts.

No live validation was run.

## Behavior Changes

Intentional behavior changes:

- RunKernel now owns canonical evidence/source custody state.
- stronger official/current/legal/canonical/source-bound requirements require
  candidate identity and deterministic fit;
- helper/controller assessments and proposals are recorded but cannot promote a
  fact disposition;
- weak, secondary, community/social, stale, off-topic, unreadable, or unfetchable
  candidates cannot satisfy stronger requirements merely because they are
  citeable;
- AnswerContract source-class handoff prefers ledger-linked requirements over
  source-tier aggregate counts;
- final-answer packet custody summary can report RunKernel EvidenceLedger gaps.

Compatibility preserved:

- legacy Controller/AG-75 custody projections still exist for old consumers;
- subordinate official/current custody projection still has the AG-89B shape;
- final evidence selection and citation formatting remain otherwise unchanged.

## Static Guards And Tests

AG-91J adds `tests/test_evidence_ledger_ag91j.py`. It guards that:

- candidate-level custody exists and is sanitized;
- facts, helper assessments, and proposals remain distinguishable;
- source requirements link to candidate ids;
- aggregate counts cannot satisfy custody;
- weak/stale/social/off-topic evidence cannot satisfy stronger obligations;
- official/current gaps remain explicit;
- final evidence without ledger custody is a compatibility gap;
- RunKernel projection derives from canonical RunState;
- AnswerContract consumes ledger-linked state;
- final-answer packet consumes ledger custody awareness;
- trace/projection is not a second decision layer;
- stale Controller/AG-75 helpers are compatibility-only/subordinate.

## Remaining Work

AG-91K should move FinalAnswerPacket / Author executor further under RunKernel
so final evidence selection, citation eligibility, final posture, and Author
inputs consume canonical ledger custody as first-class authority.

If evidence custody exposes broader contract or judgment blockers, AG-92A should
continue with RunAuthority prompt and contract synthesis. AG-92B can then retire
more compatibility projections after final answer state is canonical enough to
replace them.
