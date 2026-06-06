# AG-90B Final Answer / Author / Citation Runtime Seam Extraction

Status: bounded subtractive implementation; behavior-preserving compatibility-shell extraction; no live validation

Branch: `ag-90b-final-answer-author-citation-runtime-seam-extraction`
Base: `main`

## Purpose

AG-90B reduces `core/pipeline_orchestrator.py` by extracting final-answer runtime
plumbing that was already licensed by AG-89D/AG-89E into a bounded helper module.
The extraction keeps `FinalAnswerPacket` authority intact and prevents the legacy
orchestrator from re-owning packet construction, Author payload derivation,
citation/source compatibility handoff assembly, or packet trace attachment.

This phase is not a prompt rewrite, citation-formatting change, provider/search
change, query-quality change, evidence-selection change, or new authority framework.

## Extraction candidates inspected

| Candidate | Estimated orchestrator reduction | Risk | Disposition |
| --- | ---: | --- | --- |
| Pre-Author source-obligation projection, `build_final_answer_packet(...)`, and `derive_author_input_payload(...)` call preparation | ~35-45 lines | Low: deterministic packet/payload plumbing; no provider/search/model calls | Extracted |
| Post-Author packet citation-observation refresh, packet-derived compatibility refs, citation/source handoff state build, handoff execution, and packet trace fragment | ~25-35 lines | Low: compatibility projection already packet-derived after AG-89D/AG-89E | Extracted |
| Final Analyst/Author compatibility trace rebuild after final-answer classification | ~60-80 lines | Medium-low: trace/handoff compatibility surface includes packet-derived final evidence ref and final source telemetry, but does not alter Author model call already completed | Extracted with exact argument preservation |
| Earlier pre-Author `execute_analyst_author_handoff(...)` and Author model call | Large | High/closed: touches live Author call shape and provider/model call boundary | Kept in orchestrator |
| Author prompt prose assembly | Large | High/closed: prompt text must remain visibly unchanged | Kept in orchestrator |
| Final evidence bundle selection/attachment | Medium | Closed: final evidence selection and Author precision slice behavior are not AG-90B targets | Kept in orchestrator |
| Official/current custody semantics | Medium | Closed: custody satisfaction remains owned by `OfficialCurrentSourceCustodyState` and source-class observability | Only consumed as existing projection |

## Selected extraction

Introduced `core/final_answer_runtime_assembly.py` as a bounded runtime assembly
helper.  The helper owns only mechanical wiring of already-computed runtime facts
into existing AG-89D/AG-89E adapters and compatibility handoffs.

Extracted surfaces:

- pre-Author source-obligation projection preparation;
- `build_final_answer_packet(...)` call preparation;
- `derive_author_input_payload(...)` call preparation;
- packet-derived Author prompt/system-key/effort return values;
- post-Author packet citation-observation refresh;
- packet-derived final evidence / ledger / source telemetry compatibility refs;
- final Analyst/Author compatibility handoff rebuild with packet-derived final evidence ref;
- packet-derived citation/source handoff state build and execution;
- final answer packet trace-fragment preparation.

## Before / after line counts

- Before: `core/pipeline_orchestrator.py` had **7,434** lines.
- After: `core/pipeline_orchestrator.py` has **7,326** lines.
- Net delta: **-108 lines**.

The phase meets the minimum AG-90B containment target of at least `-100` net lines.

## Helper responsibilities

`core/final_answer_runtime_assembly.py` provides:

- `assemble_final_answer_author_runtime(...)` — builds the pre-Author
  `FinalAnswerPacket`, derives the existing packet Author payload, and returns the
  packet-derived Author prompt/system-key/effort values.
- `assemble_final_answer_author_runtime_from_scope(...)` — orchestrator-thinning
  compatibility shell that consumes a whitelisted subset of the current runtime
  scope and delegates to the bounded author assembly helper.  The runtime scope is
  not serialized or traced.
- `assemble_final_answer_citation_runtime(...)` — refreshes the packet with final
  citation observations, rebuilds the final Analyst/Author compatibility handoff,
  builds the packet-derived citation/source handoff state, executes the deterministic
  handoff adapter, and returns trace fragments/projections.
- `assemble_final_answer_citation_runtime_from_scope(...)` — orchestrator-thinning
  compatibility shell that consumes a whitelisted subset of the current runtime
  scope and delegates to the bounded citation assembly helper.  The runtime scope is
  not serialized or traced.

The helper does **not** select evidence, choose citations, format citations, call
models, call providers, run retrieval, mutate query text, decide official/current
satisfaction, alter Author prose, or introduce a new RunAuthority framework.

## Behavior-preservation proof

- The Author model call remains in `core/pipeline_orchestrator.py` and still calls
  `ask_model(author_prompt, _author_system, provider=..., model=..., effort=..., stream=True, use_reasoning=False)`.
- The pre-Author packet path still uses the same runtime values for final evidence,
  Author evidence, ordered sources, unique source URLs, QueryPlan lineage,
  corpus-weak posture, failure-card posture, conflict presence, synthesis
  insufficiency, and Author notes.
- The packet Author payload still comes from `derive_author_input_payload(...)`.
- The legacy citation/source handoff remains packet-derived via
  `build_packet_derived_citation_source_handoff_state(...)`.
- The final Analyst/Author compatibility handoff still receives the same final
  evidence, Author evidence, source telemetry ref, final evidence ref, gate refs,
  retrieval-loop refs, router-query-preparation refs, and answer-contract ref.
- Focused AG-90B tests compare scoped assembly against the direct bounded builder
  and verify packet-derived citation handoff refs, snapshot refs, source telemetry,
  and packet trace projection.

## Protected surfaces kept closed

AG-90B did not change:

- provider routing, provider selection, provider depth, provider swaps, or new providers;
- provider/model/search calls;
- QueryPlan-authorized query text;
- query-generation quality;
- official/current custody satisfaction semantics;
- retrieval ranking/filtering;
- final evidence selection;
- citation formatting style;
- Author prose/style/product design;
- Analyst/Economist/Scrutineer behavior;
- cache reuse;
- ProjectSource retrieval;
- prompt prose outside the existing AG-89D packet-authority payload behavior.

## Remaining high-value extraction candidates

1. **Author prompt text assembly** — high line-count opportunity, but should be a
   dedicated prompt-invariance phase with exact golden-string tests because prompt
   prose is a protected surface.
2. **Earlier pre-Author Analyst/Author handoff execution** — candidate for a later
   Author runtime seam phase, but it is closer to the live Author call shape than
   the post-Author compatibility trace rebuilt here.
3. **Source-obligation bridge telemetry** — should follow a custody-focused consumer
   audit so bridge readers can move to `official_current_source_custody` without
   changing satisfaction semantics.
4. **Supplemental-search and Scrutineer remediation handoff traces** — valuable
   follow-up only after their diagnostic consumers are inventoried.

## Recommended next phase

Run an AG-90C prompt-invariance extraction inventory for the remaining Author prompt
assembly block, or an AG-90C trace compatibility pass focused on source-obligation
bridge and supplemental-search/Scrutineer handoff trace consumers.  Either next
phase should remain subtractive and should not perform live provider/model/search
validation unless separately approved.
