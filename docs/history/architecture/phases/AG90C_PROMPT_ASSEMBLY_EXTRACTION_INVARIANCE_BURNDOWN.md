Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG90C_PROMPT_ASSEMBLY_EXTRACTION_INVARIANCE_BURNDOWN).

# AG-90C Prompt Assembly Extraction / Prompt-Invariance Burn-Down

Status: behavior-preserving extraction; no live validation; no provider/model/search calls

Branch: `ag-90c-prompt-assembly-extraction-invariance-burndown`

## Purpose

AG-90C continues the orchestrator burn-down by moving bounded prompt assembly out
of `core/pipeline_orchestrator.py` while keeping prompt text, model-call shape,
provider/search behavior, evidence selection, citation formatting, and final
answer prose closed.

The phase is subtractive: helpers build the same strings the orchestrator built
inline.  Runtime calls remain in the orchestrator.

## Prompt blocks inspected

| Prompt block | Approx. orchestrator-hosted lines inspected | Risk | Decision |
| --- | ---: | --- | --- |
| Author prompt body, tier text, image context, Scrutineer Author block, Author system-key selection | ~150 | High: directly shapes final answer prose and citation instructions | Extracted with exact-string tests and system-key parity |
| Analyst cached prefix and Analyst prompt suffixes | ~70 | Medium/high: stable prefix affects cached context and Analyst behavior | Extracted with exact prefix/suffix tests; model call remains in orchestrator |
| Economist numerical-anchor preflight prompt | ~55 | Medium: JSON preflight prompt and call shape are protected | Extracted prompt strings only; JSON call shape remains in orchestrator |
| Synthesis evaluator prompt | ~8 | Medium: JSON evaluator prompt controls supplemental search trigger | Extracted exact string only; evaluator call shape unchanged |
| Scrutineer audit prompt and remediation-query prompt | ~50 | Medium/high: flags and remediation queries are protected | Extracted exact strings only; Scrutineer/remediation calls unchanged |
| Query expander prompt | ~12 | Medium: component-query generation prompt | Extracted exact string only; expander call shape unchanged |
| Router/retry/title/researcher prompts | ~35 | Medium: earlier routing/query behavior is sensitive | Left in place; not needed to reach target and query text generation remains closed |
| Scout registry prompt snippets | N/A registry-driven | High: registry-owned prompts and evidence-requirement behavior | Left in place; no registry rewrite |

## Selected extraction

Introduced `core/runtime_prompt_assembly.py` as a bounded prompt construction
module.  It owns only mechanical prompt and prompt-fragment builders for:

- Analyst cached prefix and Analyst prompt suffixes;
- query expander prompt;
- Economist preflight prompts;
- synthesis evaluator prompt;
- unsupported-retrieval Analyst/Author directive fragments;
- Scrutineer audit prompt and remediation-query prompt;
- Author image context, tier instruction selection, Author prompt assembly, and
  Author system prompt key selection.

The orchestrator now imports these helpers and keeps the model/search callsites
where they were.

## Before / after line counts

- Before: `core/pipeline_orchestrator.py` had **7,326** lines.
- After: `core/pipeline_orchestrator.py` has **7,122** lines.
- Net delta: **-204 lines**.

This meets the AG-90C minimum target of at least `-200` net orchestrator lines.

## Surfaces moved out of the orchestrator

Moved out:

- prompt text concatenation for selected Author, Analyst, Economist preflight,
  synthesis evaluator, Scrutineer, remediation, and expander prompts;
- prompt-fragment assembly for unsupported retrieval and Author image/tier
  instructions;
- mechanical Author system-key selection logic.

Not moved:

- `ask_model(...)` callsites;
- provider/model/effort/use_reasoning/stream/require_json arguments;
- `process_search_queries(...)` callsites;
- provider routing or provider selection;
- final evidence selection;
- citation formatting;
- official/current custody semantics;
- QueryPlan authorization;
- FinalAnswerPacket authority semantics.

## Helper responsibilities

`core/runtime_prompt_assembly.py` is intentionally a string-builder module. It:

- accepts already-computed runtime facts;
- returns dataclass prompt assemblies or strings;
- performs no provider/model/search calls;
- does not import `DEFAULT_SYSTEM` or own provider routing;
- does not serialize raw prompts to trace, caches, DB rows, or output artifacts;
- does not choose evidence, citations, providers, search depth, or next actions.

Compatibility scope wrappers are used only to thin the orchestrator callsite;
their scope dictionaries are not serialized or traced.

## Exact prompt-invariance proof

Added `tests/test_ag90c_runtime_prompt_assembly.py`, which proves exact prompt
string parity for representative fixtures covering:

- Analyst cached prefix, quant-packet section placement, evidence slicing, and
  normal/estimate-from-priors Analyst suffixes;
- expander prompt;
- synthesis evaluator prompt;
- Scrutineer audit prompt and flag-limit system prompt replacement;
- Scrutineer remediation researcher prompt;
- Author prompt including recency note, analysis block, precision evidence,
  sources, nutrition note, Scrutineer Author block, image context, and final
  markdown directive;
- Economist preflight prompt;
- unsupported-retrieval Analyst directive and Author note;
- Author system prompt key selection;
- helper static guard forbidding model/provider/search calls and enforcing the
  orchestrator line-count burn-down.

Updated static guards that previously required prompt text to remain literally
inside `pipeline_orchestrator.py`; they now encode the AG-90C rule that bounded
helper extraction is allowed only when prompt parity is tested and helpers do not
call models/providers/search.

## Model-call shape preservation

Every touched live call remains in `core/pipeline_orchestrator.py` with the same
call-shape inputs:

- Analyst calls keep the same system prompts, provider/model, effort,
  `use_reasoning`, and stable-prefix measurement inputs.
- Economist preflight keeps the same fast provider/model, `effort="low"`,
  `use_reasoning=False`, `require_json=True`, `max_tokens=100`, and
  `temperature=0`.
- Synthesis evaluator keeps the same fast provider/model, `effort="low"`,
  `require_json=True`, and existing `use_reasoning` value.
- Scrutineer keeps the same smart provider/model, `effort="medium"`,
  `require_json=True`, and `use_reasoning=False`.
- Scrutineer remediation keeps the same researcher system prompt, fast
  provider/model, `effort="low"`, `require_json=True`, and existing
  `use_reasoning` value.
- Author keeps the same streaming call and Author handoff/runtime packet path.

## Protected surfaces kept closed

AG-90C did not change:

- prompt prose intentionally;
- final answer prose/style/product design;
- citation formatting style;
- provider routing, provider selection, provider depth, provider swap, or new
  providers;
- provider/model/search calls;
- QueryPlan-authorized query text;
- retrieval ranking/filtering;
- final evidence selection;
- official/current custody satisfaction;
- FinalAnswerPacket authority semantics;
- Analyst/Economist/Scrutineer behavior beyond mechanical prompt assembly
  relocation;
- cache reuse;
- ProjectSource retrieval.

## Remaining high-value extraction candidates

1. Router/retry/title/researcher prompt snippets can be extracted in a later
   phase with query-text golden tests.
2. Scout registry prompt usage should remain registry-owned unless a dedicated
   Scout prompt-invariance phase is opened.
3. Additional context-measurement call assembly may be thinned after prompt
   extraction stabilizes, but it should not become a trace/policy brain.
4. More explicit old-vs-helper golden fixtures could be added from captured
   sanitized orchestrator scenarios if future phases touch prompt text again.

## Recommended next phase

Run a narrow AG-90D prompt-invariance cleanup for the remaining router/researcher
prompt snippets, or a non-prompt orchestrator containment pass that extracts
runtime bookkeeping without moving provider/search/model calls.  Keep live
validation disabled unless a future brief explicitly approves it.
