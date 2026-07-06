# Analyst Workbench Full Slice

Status: current BUILD phase note for
`CURRENT-SOURCE-RECORD-ANALYST-WORKBENCH-FULL-SLICE-SCAFFOLD-01`.

Mode: BUILD

## Phase Boundary

Target surface:

- Product-consumed Analyst Workbench scaffold between candidate intake and
  D-prime/model-review admission for current-source single-fact runs.
- Candidate evidence triage, evidence-role proposals, analyst finding proposals,
  lane placeholders, gap-search proposal, D-prime dossier handoff, and
  Workbench reduction projection.
- Product CLI review output that shows a reviewer-visible Workbench section
  without dumping raw/private material or treating proposals as authority.

High-custody surface:

- Current-source record product CLI answer-first output.
- D-prime model-review input packet and status refs.
- Existing source-obligation authority, citation-source handoff authority,
  FinalAnswerPacket, Author, and citation display boundaries.

Closed-this-phase surface:

- Live validation correctness claims.
- Follow-up live searches proposed by the Workbench.
- Specialist/Economist/Scrutineer lane execution beyond placeholders.
- Evidence admission, source-obligation satisfaction, citation eligibility,
  source-authority finality, product correctness, and answer prose creation by
  Workbench packets.

## Product-Facing Progress

Product-facing progress type: product-path scaffold consumed by the current
answer flow.

Actual user-facing or reviewable output delta:

- Product CLI output remains answer-first and prints the clean review-report
  path instead of a full Workbench dump.
- When strict support is missing or contextual material creates overclaim risk,
  the answer-first blocker names the need for official strict support.
- The current-source record review report now includes an `Analyst Workbench`
  section with triage refs, dossier handoff status, lane placeholder statuses,
  gap proposal status, Workbench reduction projection status, and explicit
  RunKernel reduction-pending status.

Actual consumer seam:

- `proplex.mvp_single_relation_live_dogfood_run` builds the Workbench bundle
  after fetch/read succeeds and before semantic/D-prime coverage.
- `proplex.live_semantic_coverage_status` passes the Workbench D-prime dossier
  ref into `core.dprime_model_review_assessment`.
- D-prime input refs carry the dossier ref as proposal-only context.

Existing machinery reused:

- Generic relation planning and acquisition planning.
- Provider-extracted and fetch/read candidate diagnostics.
- D-prime model-review assessment input/ref/status machinery.
- Existing source-obligation and citation-source authority reducers.
- Existing product CLI answer path and review-report writer.

New machinery introduced:

- `core.analyst_workbench_runtime` creates sanitized proposal-only packets:
  `CandidateEvidenceTriagePacket`, `EvidenceRoleProposal`,
  `AnalystWorkbenchPacket`, `AnalystFindingProposal`,
  `AnalysisGapSearchProposal`, `WorkbenchDprimeDossier`, and
  `WorkbenchReductionProjection`.
- Product packet/report validation ensures the Workbench cannot claim evidence
  admission, source-obligation satisfaction, citation eligibility,
  source-authority finality, product correctness, raw/private retention, answer
  prose creation, or RunKernel reduction.

Old path treatment:

- The prior optional evidence-triage deferral is replaced by a product-consumed
  Workbench bundle after fetch/read.
- Existing D-prime authority remains the only downstream authority path; the
  Workbench dossier is context, not admission.
- The local Workbench projection is marked `run_kernel_reduced: false`,
  `run_kernel_reduction_pending: true`, and
  `proposed_for_runkernel_reduction: true`.

Why this is not reinventing an existing surface:

- The Workbench does not create a separate answer path, citation renderer,
  source-obligation authority, or D-prime substitute.
- It packages bounded candidate diagnostics already produced by the ordinary
  runtime into proposal-only records, then hands compact refs to the existing
  D-prime path and review report.

## Authority Boundary

Workbench packets are proposal-only. They may classify candidate roles, propose
analyst findings, propose a gap search, prepare a local Workbench reduction
projection, and hand a D-prime dossier ref to the existing D-prime path.

They must not:

- Admit evidence.
- Satisfy source obligations.
- Create citation eligibility.
- Finalize source authority.
- Claim product correctness.
- Create answer prose.
- Retain raw source text, raw provider payloads, raw prompts, raw model
  responses, private logs, DB/cache rows, or full traces.
- Imply RunKernel authority unless RunKernel actually reduced the state.

## Validation Status

Live product run executed: not by this phase.

Live validation correctness claimed: false.

Product correctness claimed: false.

The phase uses offline injected provider/fetch/model-review callables to guard
the ordinary product path without live provider, model, search, retrieval, or
private-data access.
