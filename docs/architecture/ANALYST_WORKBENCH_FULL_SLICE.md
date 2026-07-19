# Analyst Workbench Full Slice

Status: canonical current Analyst Workbench runtime contract, promoted from the
BUILD phase note for
`CURRENT-SOURCE-RECORD-ANALYST-WORKBENCH-FULL-SLICE-SCAFFOLD-01`.

Mode: BUILD

This document records current merged Workbench behavior for future Codex phases.
It does not license runtime changes, live validation, provider/model/search/
fetch/read calls, new answer paths, Scrutineer implementation, source-challenge
recovery, FAP/Author wording changes, or product correctness claims.

Current acquisition boundary: production untrusted exact-URL READ remains
blocked because no Linkup/Tavily operation has sufficient committed public-
target guarantees or observable final-target lineage to be truthfully eligible.
The Workbench contract does not override that block or reactivate READ, Focused
Extract, final custody, or semantic admission.

Future cross-component doctrine lives in
[CROSS_COMPONENT_ANALYST_WORKBENCH.md](CROSS_COMPONENT_ANALYST_WORKBENCH.md).
That doctrine adapts the same proposal-only Workbench posture for synthesis over
compact component refs; it does not create a second Analyst authority path or
open graph execution.

The canonical durable direction is
[MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md](MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md).
The current default ordinary semantic producer does not establish a typed
general component Analyst -> component D-prime lane. The approved Phase 1
product path must add a configured-SmartModel regular component Analyst before
component D-prime, then use a separate configured-SmartModel Cross-Component
Analyst for synthesis proposals. Existing Workbench packets and specialized
status lanes are reuse candidates; their presence is not proof that either
ordinary producer role is installed.

## Canonical Runtime Contract

### Workbench Role

The Analyst Workbench is proposal-only. It is product-consumed between current
candidate intake/fetch-read and D-prime/model review for current-source
single-fact runs.

The Workbench packages bounded candidate diagnostics into:

- candidate role proposals;
- analyst finding proposals;
- gap proposals;
- D-prime dossier refs;
- Workbench reduction projections.

The Workbench may prepare proposal inputs for RunKernel and context/dossier
inputs for D-prime. Its local reduction projection is not RunKernel authority
unless RunKernel actually reduces the state.

The Workbench does not:

- admit evidence;
- satisfy source obligations;
- create citation eligibility;
- finalize source authority;
- create FinalAnswerPacket or Author output;
- dispatch search directly;
- create a new search subsystem;
- decide Sufficiency;
- open source display;
- claim product correctness.

### Future Cross-Component Adaptation Boundary

The future Cross-Component Analyst Workbench must inherit this proposal-only
boundary. It may propose consistency, dependency, missing-component,
contradiction, caveat, recovery, and synthesis refs over compact
`ComponentWorkNode` and admitted synthesis-node outputs, including proposed
semantic edges and first-class synthesis nodes. A real ordinary producer must
be a dedicated configured-SmartModel role, not merely this Workbench contract.
It must hand proposal refs to synthesis D-prime and RunKernel rather than
validating, admitting, dispatching recovery, searching, packaging, or rendering
by itself.

It must not become:

- a parallel Analyst system beside this Workbench;
- a ComponentWorkGraph executor or scheduler;
- a retrieval dispatch path;
- a D-prime substitute;
- a Sufficiency/FAP/Author shortcut;
- an Author glue layer over component finals.

### Candidate Role Semantics

Workbench candidate roles are non-authority proposal classifications. They help
downstream reviewers and reducers see why a candidate is useful, risky, or
incomplete; they do not make the candidate answer authority.

Current role vocabulary includes:

- `strict_answer_support_candidate`;
- `answer_adjacent_context`;
- `qualifier_exception_context`;
- `overclaim_risk`;
- `conflict_candidate`;
- `remediation_needed_candidate`;
- official-looking/read-support gap roles such as
  `official_source_of_record_looking_candidate`,
  `unreadable_high_value_official_artifact`, and the corresponding
  `unreadable_high_value_candidate` gap posture.

Roles are not necessarily exclusive. A candidate can be official-looking and
still be only contextual, risky, unreadable, or insufficient for the answer
claim. A candidate does not become answer authority merely because it is
official-looking, source-of-record-looking, or contains answer-like tokens.

### Generic Context Vocabulary

Generic qualifier-risk vocabulary is allowed in Analyst detection. This
includes terms such as:

- `waiver`;
- `discount`;
- `reduced`;
- `online`;
- `exception`;
- `exemption`;
- `eligibility`;
- `special`;
- `temporary`.

That vocabulary is generic semantic context, not a domain-specific production
branch. It must not be removed merely to satisfy static guards that are meant to
prevent hard-coded live-case literals. Static guards should prevent production
branches for specific literals such as USCIS, N-400, I-942, or specific fee
amounts, not generic Analyst qualifier vocabulary.

### Gap States

Workbench gap states are proposal-only. They can block answer output only by
feeding the existing product blocker and follow-up policy surfaces; they do not
admit evidence or prove answer correctness.

| Gap state | Meaning | Can block answer output? | Can trigger follow-up when licensed? | Must not infer |
| --- | --- | --- | --- | --- |
| `not_required` | A strict-support candidate was proposed and contextual risks are preserved for downstream review. | No, not by itself. | No. | Does not mean D-prime support, source-obligation satisfaction, citation eligibility, Sufficiency, FAP, Author, source display, or PASS already happened. |
| `strict_support_missing` | No strict answer-support candidate was identified, or contextual material is insufficient for the answer claim. | Yes, through the current-source answer blocker when unresolved. | It may propose and plan a licensed follow-up, but current untrusted exact-URL routing blocks without a safety-eligible provider operation. | Does not mean provider/search/fetch/read occurred, and does not prove that contextual material is true, false, current, or citable. |
| `unreadable_high_value_candidate` | An official-looking or high-value candidate needs readable strict support before it can feed D-prime answer authority. | Yes, through the current-source read-support blocker when unresolved. | It may propose and plan a licensed follow-up, but current untrusted exact-URL routing blocks without a safety-eligible provider operation. | Does not infer the unreadable source content, citation eligibility, source-obligation satisfaction, or PDF/table read support. |
| `overclaim_risk` | Contextual or qualifier material could support a narrower claim but risks overstating the answer without stricter support. | It can contribute to a blocker when strict support is missing or downstream review refuses the claim. | Only through an explicitly licensed recovery/follow-up path. | Does not by itself prove contradiction, support, challenge resolution, or answer readiness. |

### Follow-Up License Behavior

Without an explicit current-source follow-up license or flag:

- `strict_support_missing` and `unreadable_high_value_candidate` remain
  proposal-only blockers.
- No follow-up provider call occurs.
- No follow-up search dispatch occurs.
- No follow-up fetch/read occurs.
- No FAP, Author, citation/source display, or source-display answer path opens
  from the gap.
- Review material may retain proposal/blocker refs only.

With an explicit current-source follow-up license or flag:

- the Workbench gap enters the existing planned and RunKernel-authorized
  ordinary follow-up path;
- follow-up planning refs are retained;
- RunKernel follow-up authorization refs gate execution;
- current target-safety admission and provider-operation eligibility gates
  remain mandatory;
- existing provider DISCOVER acquisition remains distinct from an exact-URL
  operation and may return provider-extracted source material under its current
  gates;
- current repository evidence establishes no safety-eligible Linkup/Tavily
  production READ/Focused Extract route for an untrusted exact URL, so any such
  exact-URL operation blocks before adapter invocation;
- the two former CLI-reachable local webpage openers are retired and no local
  webpage downloader replaces them;
- Workbench and D-prime remain non-dispatch owners;
- an explicit license does not create exact-URL READ/Focused Extract
  eligibility, exact-URL final custody, or product PASS; the retained
  DISCOVER-content path remains pre-existing behavior;
- if follow-up is exhausted, the product reports the licensed/exhausted
  blocker, not a not-licensed blocker;
- if material is obtained but the answer path is not reached, the product
  reports the existing answer-path-not-reached blocker;
- if candidate identity diverges, the #452 candidate handoff blocker remains
  authoritative.

The provider-eligibility block reflects insufficient committed public-target
guarantees or observable final-target lineage. It does not classify Linkup or
Tavily as inherently unsafe, and an offline fixture cannot change production
policy.

### Product PASS Conditions

Workbench proposal, follow-up execution, provider result, readable material, or
an official-looking source alone is not product PASS.

Product PASS requires the existing downstream answer path to consume:

- D-prime support/admission;
- admitted `SemanticObservation`;
- `ComponentCoverage`;
- `SufficiencyReadiness`;
- FAP safe claim / hardened FinalAnswerPacket;
- Author answer output;
- citation/source display handoff;
- raw/private retention false posture.

### Candidate Handoff Identity Invariant

The #452 invariant is that all answer-authority candidates must be the same
candidate before answer authority opens:

- Workbench expected D-prime candidate;
- D-prime relation intake candidate;
- selected source candidate;
- source-display candidate.

If those identities diverge, the product must block before FAP, Author, or
source display. The blocker is authoritative even when a provider result is
official-looking, readable, or answer-like.

### Relationship To D-prime, Scrutineer, Sufficiency, FAP, And Author

D-prime is the evidence-relative support judge. It is not the whole Analyst, and
Workbench context does not substitute for D-prime model review, proposal
validation, RunKernel admission, or downstream answer-path consumption.

Scrutineer challenge posture is separate. It must not be silently treated as an
implemented answer blocker or remediation layer unless a phase explicitly
licenses that surface.

Sufficiency decides answer readiness after the required evidence, support,
coverage, and challenge/follow-up posture exists.

FAP is the authority manifest / safe-claim packet. Author is constrained
rendering from that packet. The Workbench does not substitute for D-prime,
Scrutineer, Sufficiency, FAP, Author, citation eligibility, citation rendering,
or source display.

### Review Report Expectations

Current-source review reports should expose:

- Workbench gap kind/status;
- strict, contextual, and overclaim candidate counts;
- follow-up licensed/executed/exhausted status;
- RunKernel authorization/ref status;
- Workbench expected candidate;
- D-prime intake candidate;
- selected source candidate;
- source-display candidate;
- answer path reached/not reached;
- raw/private retained false posture.

The report is review material. It must not turn Workbench proposals, candidate
roles, follow-up refs, provider results, readable material, D-prime dossier
context, or source-display metadata into product-correctness claims.

## Implementation Provenance

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

Product-facing progress type: predecessor product-path scaffold retained for
provider-extracted DISCOVER material and offline injected-fixture regression.
Current production untrusted exact-URL acquisition is blocked before the
exact-URL fetch/read-to-Workbench seam.

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
  after a bounded material handoff and before semantic/D-prime coverage. The
  handoff may come from retained provider-extracted DISCOVER material; offline
  tests may also inject a bounded fetch/read result. Neither source is a new
  production exact-URL READ activation or proof of current live correctness.
- `proplex.live_semantic_coverage_status` passes the Workbench D-prime dossier
  ref into `core.dprime_model_review_assessment`.
- D-prime input refs carry the dossier ref as proposal-only context.

Existing machinery reused:

- Generic relation planning and acquisition planning.
- Retained provider-extracted DISCOVER and fetch/read candidate diagnostics;
  the direct exact-URL fallback is retired, while bounded fixtures continue to
  exercise the seam offline.
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

- The prior optional evidence-triage deferral was replaced at the predecessor
  checkpoint by a Workbench bundle after a bounded material handoff. The
  current production exact-URL route is blocked, while retained
  provider-extracted DISCOVER material and offline injected fixtures may still
  exercise that downstream bundle.
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
