Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG89E_TRACE_WRAPPER_COLLAPSE_ORCHESTRATOR_SIMPLIFICATION).

# AG-89E Trace-only Wrapper Collapse / Orchestrator Simplification

Status: bounded subtractive implementation; behavior-preserving trace/projection cleanup; no live validation

Branch: `ag-89e-trace-wrapper-collapse-orchestrator-simplification`

## Scope

AG-89E inventories observer-only or duplicate trace/projection surfaces that overlap
with the authority packets introduced by AG-89B, AG-89C, and AG-89D, then folds one
safe final-answer compatibility surface behind `FinalAnswerPacket`.

This phase does **not** change provider routing, provider selection, provider depth,
search behavior, query-generation quality, prompt text, retrieval ranking/filtering,
final evidence selection quality, citation formatting, Author prose/style, cache
reuse, or ProjectSource retrieval.  No live ScryRaven/proplex/provider/model/search
validation was run for this implementation.

## Surfaces inventoried

| Surface | Old wrapper / mirror | Authority owner now | Current consumer | Classification | Immediate AG-89E action |
| --- | --- | --- | --- | --- | --- |
| Legacy final evidence reference passed into the Analyst/Author handoff | Orchestrator-local count dict built from `final_top_evidence`, `author_evidence`, `ordered_sources`, and `unique_source_urls` | `FinalAnswerPacket` | `analyst_author_handoff_contract` trace/export compatibility | Fold | Replaced with `final_answer_packet_compatibility_refs(packet)["final_evidence_ref"]` |
| Citation/source handoff ledger/source telemetry refs | Orchestrator-local dicts narrating packet id, source ids, ordered sources, URL counts, and final answer source telemetry | `FinalAnswerPacket` | `citation_source_handoff_contract` compatibility handoff | Fold | Moved to `final_answer_packet_compatibility_refs(...)` and passed to the existing packet-derived handoff builder |
| Citation/source handoff final evidence bundle ref | Adapter-local ref was already packet-derived after AG-89D | `FinalAnswerPacket` | `citation_source_handoff_contract` compatibility handoff | Keep as demoted compatibility | Centralized with the other packet compatibility refs so the old handoff does not regain independent evidence authority |
| `queries_per_iteration` trace | Legacy top-level query trace mirror | `QueryPlan` | Existing trace/report tests and offline diagnostics | Keep for compatibility | No runtime change; AG-89C already derives it from `QueryPlan.queries_by_iteration()` |
| `query_plan` trace | Canonical query authority trace | `QueryPlan` | Runtime trace, AG-89C tests, weak-corpus diagnostics | Keep | No change |
| Official/current source-custody summary inside final packet | Packet projection of custody state | `OfficialCurrentSourceCustodyState` | Final answer packet source-obligation posture | Keep as projection | No change; packet still does not infer satisfaction from source/citation counts |
| Source-obligation bridge telemetry | Historical bridge and observability traces | `OfficialCurrentSourceCustodyState` | Existing source-obligation diagnostics | Later | Needs a separate consumer audit before deletion because several diagnostics still read bridge-shaped trace |
| Synthesis evaluator supplemental-search handoff refs | Passive compatibility refs to answer/citation/Analyst handoffs | Existing SES handoff contract; final evidence pieces are candidates for `FinalAnswerPacket` derivation | Supplemental-search diagnostics | Later | Not changed; deleting it safely requires a focused SES consumer audit |

## Surfaces deleted, demoted, or folded

AG-89E folded the orchestrator-local final evidence and citation/source reference
mirrors into `core.final_answer_runtime_adapter.final_answer_packet_compatibility_refs`.
The retained legacy shapes are now compatibility projections with an explicit
`authority: "final_answer_packet"` marker and, for the Analyst/Author final evidence
reference, `trace_mode: "final_answer_packet_compatibility_projection"`.

No new authority packet or trace-only wrapper was added.  The new helper is an adapter
projection for existing consumers and replaces older dict assembly that lived in
`core/pipeline_orchestrator.py`.

## Kept surfaces and deletion triggers

- `citation_source_handoff_contract` remains because downstream handoff/export tests
  still consume that trace shape.  Deletion trigger: a later phase proves all runtime,
  report, and telemetry consumers can read `final_answer_packet` directly.
- `analyst_author_handoff_contract.final_evidence_ref` remains because the
  Analyst/Author handoff trace shape is repo-visible.  Deletion trigger: the
  handoff accepts a packet ref directly or downstream consumers switch to
  `final_answer_packet`.
- `queries_per_iteration` remains as a top-level compatibility key.  It is kept only
  because existing diagnostics read it directly; the authority owner remains
  `QueryPlan`.  Deletion trigger: diagnostics and tests consume
  `query_plan.authorized_queries_by_iteration` directly.
- Official/current source-obligation bridge telemetry remains until a custody-focused
  consumer audit can demote bridge readers to `official_current_source_custody`.

## How retained projections derive from canonical authority state

`final_answer_packet_compatibility_refs(packet, ...)` reads from the packet and its
packet-owned legacy citation projection:

- final evidence counts from `packet.evidence_allowed`;
- author evidence count from `packet.author_input_refs["author_evidence_count"]`,
  which is recorded when the packet is built;
- ordered source and URL counts from `packet.to_legacy_citation_handoff_inputs()`;
- source IDs from `packet.evidence_allowed`;
- final answer source telemetry from `packet.author_input_refs` after the packet is
  updated with citation observations;
- citation-eligible counts from `packet.citation_eligible`.

The orchestrator no longer reconstructs these citation/source compatibility refs from
parallel local variables.

## `pipeline_orchestrator.py` containment result

- Starting line count observed before AG-89E edits: 7,750 lines.
- Ending line count after AG-89E edits: 7,727 lines.
- Net delta: **-23 lines**.
- New orchestrator callsites added: one import and two calls to the existing final
  answer runtime adapter helper, `final_answer_packet_compatibility_refs(...)`.
- Old orchestrator trace/reference assembly removed: the inline Analyst/Author
  `final_evidence_ref` count dict and the inline citation-source `ledger_ref` /
  `source_telemetry_ref` packet mirror dicts.
- Helper/adapter modules introduced: none.  The existing
  `core.final_answer_runtime_adapter` gained the compatibility projection helper.
- Remaining orchestrator callsites are compatibility seams: the orchestrator still
  creates `FinalAnswerPacket`, derives Author input, attaches compatibility handoff
  traces, and invokes the legacy citation-source handoff executor because downstream
  consumers still expect those shapes.

The net result moves duplicate final-evidence/citation trace authority out of the
orchestrator and behind `FinalAnswerPacket`; it does not deepen orchestrator authority.

## Remaining candidates for later cleanup

1. Replace downstream `queries_per_iteration` readers with `query_plan` readers, then
   delete the top-level compatibility key.
2. Audit `official_source_obligation_bridge` and source-class observability readers,
   then demote bridge satisfaction summaries to custody projections.
3. Audit the synthesis evaluator supplemental-search handoff for final evidence,
   citation-source, and Analyst/Author refs that can be packet refs instead of
   passive handoff mirrors.
4. Continue shrinking `pipeline_orchestrator.py` only where wrapper deletion or
   adapter extraction removes at least as much authority surface as it adds.
