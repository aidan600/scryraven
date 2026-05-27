# AG-60A Quantitative/Economist Source-Bound Handoff Hardening

## Phase Purpose

AG-60A hardens the quantitative/Economist handoff so source-bound numeric
discipline survives through Economist -> Analyst -> Author without allowing
unsupported or model-derived numbers to become final sourced claims.

## Licensed Surface

Opened:

- Economist quantitative packet interpretation;
- compact quantitative handoff fields to Analyst;
- narrow Analyst and Author quantitative-obedience wording;
- offline tests for source-bound, unsupported, model-derived, thin-quant, and
  leakage boundaries.

Closed:

- provider routing, provider selection, provider depth, and provider
  integration;
- retrieval strategy, source ranking, and source filtering;
- Scrutineer and follow-up behavior;
- weak-corpus recovery policy;
- broad citation-system or final-answer style behavior;
- mixed canonical plus academic source-obligation modeling;
- live validation and private/generated artifacts.

## Ownership Rule

The Controller and AnswerContract own source insufficiency, evidence
sufficiency, stop posture, and final answer posture. Economist, Analyst, and
Author must obey that posture.

## Economist Source-Bound Discipline

Economist remains evidence-bound:

- no numeric anchors means abort or protected unavailable behavior;
- source-bound values require direct snippet support and source IDs;
- unsupported/model-derived values must remain distinguishable;
- unsupported calculations do not produce sourced facts.

AG-60A does not loosen Economist safety or permit Economist output to become
Author-ready.

## Handoff And Prompt Changes

`quantitative_packet_v1` now carries a bounded `unsupported_values` list in
addition to `unsupported_values_count`. The Analyst packet adapter preserves
that list next to `source_bound_values` and tells Analyst to keep the two lanes
distinct.

Analyst prompt wording now explicitly treats `unsupported_values` as unavailable
or model-derived rather than sourced. Author prompt wording now explicitly says
unsupported numeric material must remain caveated and must not be cited or
worded as source-bound fact.

`core/pipeline_orchestrator.py` changed only as a tiny handoff adapter: it adds
the bounded field to the Analyst packet and clarifies packet instructions. It
does not add domain decision logic.

## Tests Added

Added:

- `tests/test_ag60a_quantitative_economist_source_bound_handoff.py`

Coverage:

- no numeric anchors abort without packet;
- source-bound values and unsupported/model-derived labels survive Analyst
  handoff;
- missing entity metric does not get filled as sourced;
- mixed-year and mismatched-metric values remain invalid;
- unsupported calculation requests produce no sourced result;
- model-derived values cannot masquerade as source-bound;
- Analyst and Author prompts preserve quantitative distinctions;
- estimate-from-priors remains explicitly model-derived;
- thin-quant `DATA_UNAVAILABLE` remains protected;
- raw quantitative packets, raw Economist JSON, prompts, traces, provider
  payloads, and local packet markers remain redacted from public handoff;
- AG-57A mixed canonical plus academic xfail remains preserved.

## Protected Boundaries

Economist code execution remains closed. Economist output still cannot bypass
Analyst. Raw `quantitative_packet`, raw `economist_v1`, raw Economist framework
text, raw prompts, provider payloads, DB rows, caches, traces, `.env`, secrets,
and local packets remain blocked from public/Author-visible surfaces.

## Validation Decision

No live validation was used.

Offline tests are sufficient because AG-60A changes deterministic compact
handoff projection and repo-tracked prompt wording only. Live ProPlex,
provider/model calls, web/search calls, and independent source checks remain
closed.

## Mixed Canonical Plus Academic Status

The AG-57A mixed canonical plus academic xfail remains preserved. AG-60A does
not model simultaneous independent canonical and academic obligations.

## Next Recommended Surface

If further quantitative failures appear, keep the next phase in compact
quantitative handoff consumption or deterministic AnswerContract quantitative
posture projection. Do not open provider routing/depth, retrieval
ranking/filtering, Scrutineer, follow-up, weak-corpus policy, broad citation
behavior, or broad final-answer behavior from AG-60A alone.
