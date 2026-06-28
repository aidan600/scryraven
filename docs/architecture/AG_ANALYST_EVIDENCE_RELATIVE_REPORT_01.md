# AG-ANALYST-EVIDENCE-RELATIVE-REPORT-01

Status: implementation posture note for the first current
EvidenceRelativeAnalysisPacket / analyst_report seam.

## Packet Posture

`EvidenceRelativeAnalysisPacket` with embedded `analyst_report` now exists as a
standalone proposal-only evidence-relative meaning packet after EvidenceLedger
custody. It consumes the EvidenceLedger `fetch_read_candidate_custody`
projection by IDs, digests, URL/domain/title metadata, fetch/read status,
bounded character counts, and excerpt digests, plus injected offline Analyst
proposal records.

The packet may say proposal-only that a readable custody record appears relevant
to a component, may support a component, may contradict another record, raises a
caveat/currentness/scope concern, or leaves an analysis gap. It also represents
readable-but-unanalyzed custody as `analysis_missing` and failed/unreadable
custody as `unreadable_source` or `missing_readable_source` gaps.

This is not SemanticObservation admission. It does not create ComponentCoverage,
citation eligibility, source-obligation satisfaction, Sufficiency,
FinalAnswerPacket, Author input, readiness, search dispatch, query plans, or
product correctness. It does not copy bounded text, raw content, prompts,
provider payloads, private logs, DB/cache rows, or generated private artifacts.

## Legacy surface audit

Inspected surfaces:

- `core/analyst_runtime_stage.py`
- `core/analyst_quant_packet_runtime.py`
- `core/post_analyst_handoff_packaging.py`
- `core/semantic_observation_foundation.py`
- `core/semantic_observation_admission_runtime.py`
- `core/economist_handoff_contract.py`
- `core/scrutineer_remediation_handoff_contract.py`
- `core/scrutineer_remediation_runtime_handoff.py`
- ComponentCoverage, Sufficiency, FinalAnswerPacket, and Author modules/tests
  around the downstream closed surfaces.

Reused surfaces:

- EvidenceLedger fetch/read candidate custody projection shape and custody
  lineage fields.
- SearchResultCandidatePacket and FetchReadContentPacket test helpers only for
  offline upstream fixture construction.

Intentionally avoided surfaces (intentionally avoided):

- Old Analyst runtime and post-Analyst handoff modules, because they are
  model/prompt-era and orchestrator-adjacent.
- old SemanticObservation surfaces, except as vocabulary/pattern inspiration.
- Economist and Scrutineer handoff surfaces, because they remain passive,
  specialized, or legacy and are not the current report authority.
- ComponentCoverage, Sufficiency, FinalAnswerPacket, and Author paths, because
  this phase must not create or trigger downstream authority.

legacy/passive/downstream posture:

- Existing Analyst/Economist/Scrutineer modules remain legacy/passive or
  specialized compatibility surfaces unless a later phase explicitly integrates
  them into the current second-half chain.
- Existing SemanticObservation admission remains the later semantic-observation
  authority path; this packet is not an admission shortcut.
- ComponentCoverage, Sufficiency, FinalAnswerPacket, and Author remain
  downstream closed surfaces for this phase.

Retired or demoted in this phase:

- No runtime surface was deleted. The safe cleanup was documentation demotion:
  current docs now distinguish the new proposal-only packet from old
  Analyst/SemanticObservation/Economist/Scrutineer surfaces and from downstream
  coverage/readiness/Author surfaces.

Later retirement targets:

- Legacy Analyst runtime and post-Analyst handoff modules should be revisited in
  a dedicated migration/retirement phase after the current Analyst/Specialist/
  Scrutineer packet chain exists.
- Old passive SemanticObservation vocabulary can be reconciled only when a later
  phase explicitly bridges or replaces proposal packets with admitted semantic
  observations.
