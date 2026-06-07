# AG-90G — Post-Analyst Handoff Packaging Seam Extraction

## Inspected block

The inspected runtime block was the post-Analyst/downstream handoff surface in
`core/pipeline_orchestrator.py` immediately after the AG-90F Analyst runtime seam
and AG-90E legacy review seam, before the Author provider/model call. The block
owned already-computed packaging and telemetry glue:

- posthoc Author quantitative-source telemetry scanning;
- posthoc Economist skip-eligibility shadow telemetry;
- Analyst/Economist shadow-alignment summarization;
- Analyst→Author handoff state construction;
- mechanical execution of the Analyst→Author handoff envelope;
- compatibility assignment of handoff-derived `author_system_prompt_key` and
  `_author_effort`.

## Selected extraction

AG-90G extracts that bounded packaging surface into
`core/post_analyst_handoff_packaging.py`:

- `build_post_analyst_handoff_packaging(...)` is the direct tested entrypoint
  for representative already-computed Analyst/Economist/gate values.
- `build_post_analyst_handoff_packaging_from_scope(...)` is the orchestrator
  adapter; it consumes a strict whitelist from `locals()` and does not accept or
  pass `globals()`.
- The helper owns only deterministic packaging, shadow telemetry, and mechanical
  Analyst→Author handoff invocation.
- Existing private compatibility names remain re-exported through the
  orchestrator for older tests and downstream imports.

## Line counts and deltas

- `core/pipeline_orchestrator.py` before: **6,235** lines.
- `core/pipeline_orchestrator.py` after: **5,903** lines.
- Orchestrator reduction: **-332** lines.
- `core/post_analyst_handoff_packaging.py`: **317** lines.
- Production-code delta: `core/pipeline_orchestrator.py` **+45/-377** plus new
  helper **+317**, for a net **-15** production lines.
- Total repo delta before commit: production **-15** lines plus focused tests
  **+212** lines and this architecture note **+107** lines, for a total repo
  delta of **+304** lines.

## Helper responsibility

The helper packages facts that were already computed by prior runtime stages. It
may:

- scan the already-built Author prompt for diagnostic quantitative-source
  markers;
- compute diagnostic-only Economist skip-eligibility shadow telemetry;
- summarize pre/post Economist skip-shadow alignment;
- build Controller-owned Analyst→Author handoff state from supplied identities;
- execute the existing mechanical Analyst→Author handoff envelope.

The helper does **not** decide Analyst admission, choose providers, dispatch
search, alter query planning, rebuild evidence, select final evidence, format
citations, build Author prose, call the final answer model, alter custody, or
change `FinalAnswerPacket` semantics.

## Exact packaging parity proof

Focused AG-90G tests exercise the helper with deterministic fixtures and assert:

1. Representative healthy Analyst/Economist outputs produce the same
   Analyst→Author admission descriptor, evidence-context descriptor, Author
   prompt input descriptor, Author effort/key passthrough, and eligible
   Economist skip-shadow alignment.
2. The scope adapter preserves failure-card packaging, Analyst skip posture,
   Analyst evidence/context identity, and Author quantitative-source scan output
   for a raw-packet-marker fixture.
3. Static seam guards verify no `{**globals(), **locals()}` pattern, no
   `globals()` use in the helper, no provider/search/prompt/model/citation
   imports in the helper, and no calls to model/search/provider/evidence/citation
   authority functions.

Existing AG-90F, AG-90E, Analyst/Author/Economist handoff, and full offline
suite tests cover runtime parity through the orchestrator.

## Protected surfaces kept closed

AG-90G did not change:

- prompt text;
- provider/model/effort/base-url/api-key/use-reasoning routing;
- search-depth policy;
- QueryPlan query text/order;
- retrieval ranking/filtering;
- final evidence selection;
- citation formatting;
- Author prose/style/posture;
- official/current custody behavior;
- `FinalAnswerPacket` semantics;
- cache reuse;
- ProjectSource retrieval.

No live validation, provider calls, model calls, or search calls were run.

## Remaining candidates

Remaining burn-down candidates are downstream handoff/projection pockets that are
still interleaved with final answer/citation runtime assembly, especially where
already-computed citation-source, final-answer packet, and session-output trace
fragments are copied into legacy trace dictionaries. Those candidates should
remain bounded and must not absorb final evidence selection, citation formatting,
Author prose, or packet authority semantics.
