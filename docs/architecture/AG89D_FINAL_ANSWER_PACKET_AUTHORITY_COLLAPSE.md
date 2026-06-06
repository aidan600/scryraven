# AG-89D FinalAnswerPacket Authority Collapse

Status: bounded implementation; behavior-preserving final-answer authority seam; no live validation

## Scope

AG-89D introduces `FinalAnswerPacket` as the run-local authority for final answer
evidence identity, citation eligibility, source-obligation visibility, official/current
custody summary references, answer posture, mandatory caveats, prohibited upgrades,
and Author input references.

This phase does **not** change provider routing, provider choice, search behavior,
query generation, `QueryPlan` behavior, retrieval ranking/filtering, Author prompt
prose, Author style, citation formatting, or final answer product design.

## Implemented seam

`core.final_answer_packet.FinalAnswerPacket` records:

- `evidence_allowed` and `evidence_excluded` records;
- `citation_eligible` and `citation_ineligible` records with rejection reasons;
- official/current source-obligation records derived from
  `OfficialCurrentSourceCustodyState` when custody is present;
- claim/answer postures such as `directly_sourced`, `insufficient_evidence`,
  `weak_corpus_authorized`, `failure_card_authorized`, and `conflict_preserved`;
- packet-level `mandatory_caveats` and `prohibited_upgrades`;
- QueryPlan lineage references as provenance only;
- JSON-safe trace projection without raw prompt text, provider payloads, secrets,
  DB rows, caches, or private logs.

`core.final_answer_runtime_adapter` owns runtime construction, Author input payload
derivation, packet trace projection, and the compatibility projection used by the
legacy citation/source handoff.

## Consumed authority

Before Author execution, the orchestrator builds a `FinalAnswerPacket`, derives a
`FinalAnswerAuthorInputPayload` from it, and then passes the payload prompt/system
key/effort through the existing Author execution path. The payload preserves the
existing prompt text and model/provider call shape; it only makes the packet the
explicit authority for what the Author is allowed to use, cite, caveat, and claim.

## Deleted/demoted surface

The legacy citation-source handoff is demoted behind `FinalAnswerPacket`:

- `pipeline_orchestrator.py` no longer calls
  `build_citation_source_handoff_state(...)` directly from scattered final evidence,
  source URL, ordered-source, and telemetry variables.
- Instead, it calls
  `build_packet_derived_citation_source_handoff_state(final_answer_packet, ...)`.
- The compatibility handoff trace remains for downstream consumers, but its final
  evidence and citation eligibility inputs are packet projections.

This satisfies the AG-89 deletion/demotion requirement without changing citation
formatting or final answer prose.

## AG-89B boundary

Official/current source satisfaction remains owned by
`OfficialCurrentSourceCustodyState`. The packet may consume custody projections and
serialize satisfied/unsatisfied posture, but it does not infer official/current
satisfaction from aggregate counts, query text, source counts, or citation presence.
When custody is absent, the packet marks custody visibility unavailable rather than
pretending satisfaction.

## AG-89C boundary

`QueryPlan` remains authoritative for query identity and query mutations. The packet
may include QueryPlan trace references as lineage/provenance; it does not mutate
queries, order retrieval, or decide retrieval continuation.

## Current limitations

- The pre-Author packet consumes the sanitized `official_current_source_custody`
  projection emitted by existing source-class observability over final evidence. It
  does not consume the later official-source obligation bridge trace because that
  bridge is assembled in the runtime trace path after Author execution.
- Existing Author product style remains unchanged. The only Author-facing prompt
  change is a bounded packet-authority block appended by the packet payload so the
  Author can obey citation eligibility, missing-obligation posture, mandatory
  caveats, and prohibited upgrades.

## Next action

AG-89E should fold additional observer-only final answer mirrors and trace wrappers
behind `FinalAnswerPacket` now that final evidence/citation/Author input authority has
a canonical packet seam.
