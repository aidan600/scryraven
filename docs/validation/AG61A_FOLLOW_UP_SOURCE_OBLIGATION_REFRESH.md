# AG-61A Follow-Up Source-Obligation Refresh

## Phase Purpose

AG-61A prevents chat follow-ups from using stale saved report context when the
new follow-up introduces a current, official, canonical, legal/current-primary,
academic, or source-bound quantitative obligation.

## Licensed Surface

Opened:

- follow-up source-obligation detection;
- follow-up saved-context source-sufficiency checks;
- existing follow-up retrieval request generation;
- follow-up synthesis prompt grounding;
- follow-up public leakage guards;
- offline tests and this validation note.

Closed:

- provider routing, provider selection, provider depth, provider integration,
  and new providers;
- broad retrieval behavior outside the existing follow-up retrieval path;
- source ranking/filtering redesign;
- Analyst, Author, Economist, and Scrutineer behavior outside follow-up-specific
  prompt text;
- Economist source-bound behavior;
- weak-corpus recovery policy;
- broad citation-system or final-answer style behavior;
- mixed canonical plus academic source-obligation modeling;
- `core/pipeline_orchestrator.py`;
- live validation and private/generated artifacts.

## Ownership Rule

The Controller and AnswerContract own source insufficiency, evidence
sufficiency, stop posture, and final answer posture. Follow-up must preserve the
same posture instead of becoming an escape hatch around required source classes,
source-fit, citation-laundering, or quantitative source-bound rules.

## Follow-Up Refresh Behavior

`core/followup.py` now applies a deterministic follow-up source-obligation
refresh after evaluator JSON parsing and before the existing follow-up retrieval
call.

When the new follow-up asks for current official/rule material, canonical docs,
legal/current-primary evidence, explicit academic evidence, or source-bound
numeric comparisons, follow-up checks whether saved passages actually satisfy
the required source class. Secondary, community, social, weak, off-topic, or
partial saved context does not satisfy a new required class.

Declared `source_class` values on saved passages are not enough to satisfy
official/current, canonical, legal/current-primary, or source-bound numeric
follow-up obligations. The saved passage tier, domain, and context must support
that authority before the declared class can count as source-sufficient.

If saved context is insufficient, follow-up sets the existing `needs_search`
path and creates terse targeted follow-up queries only through the existing
follow-up retrieval mechanism. If retrieval returns no usable new evidence, the
synthesis prompt carries a compact insufficiency note so the answer can preserve
that posture rather than answering confidently.

Saved context remains usable when no new source obligation is introduced, or
when the saved context actually contains the required source class.

## Prompt And Handoff Changes

`MemorySearchResult` now carries compact follow-up fields:

- `required_source_classes`;
- `source_obligation_status`;
- `source_obligation_reason`;
- `source_obligation_note`;
- `saved_context_source_sufficient`.

The follow-up synthesis prompt includes only the compact note, not raw prompts,
raw traces, provider payloads, DB rows, caches, logs, local packets, or raw
quantitative packets.

`core/prompts.py` clarifies the follow-up evaluator and chat assistant contract:
saved report context is sufficient for new source-bound obligations only when it
contains the required source class, and follow-up synthesis must obey the
compact source-obligation note.

## Tests Added Or Changed

Added:

- `tests/test_ag61a_followup_source_obligation_refresh.py`

Coverage:

- current official/rule follow-up refreshes secondary saved context;
- canonical docs follow-up refreshes community saved context;
- secondary/community declared-class laundering guards for official-current and
  canonical-doc claims;
- source-bound quantitative follow-up does not fill a missing metric;
- non-authoritative declared numeric-source laundering remains insufficient;
- simple clarification negative control uses saved context;
- explicit academic follow-up remains academic and is not forced into canonical
  docs;
- ordinary conceptual follow-up is not over-forced into official/canonical
  recovery;
- AG-59AB insufficiency posture is preserved when required evidence remains
  missing;
- AG-60A source-bound versus unsupported/model-derived quantitative distinction
  is preserved;
- citation-laundering guard reaches follow-up synthesis;
- follow-up prompt surfaces redact protected raw/private material;
- AG-57A mixed canonical plus academic strict xfail remains preserved;
- protected provider/routing/depth, prompt role, weak-corpus, and orchestrator
  surfaces remain closed.

## Protected Surfaces

`core/pipeline_orchestrator.py` remains unchanged. Provider routing, provider
selection, provider depth, source ranking/filtering, weak-corpus policy,
Economist behavior, and broad final-answer/citation behavior remain closed.

## AG-59AB Preservation

When a required source class remains missing after follow-up retrieval, the
follow-up synthesis prompt preserves an insufficiency posture and blocks
citation-laundering from stale saved sources.

## AG-60A Preservation

Source-bound numeric follow-ups require sourced numeric evidence. Missing
metrics remain unavailable, and unsupported/model-derived values must stay
distinct from sourced facts.

## Mixed Canonical Plus Academic Status

The AG-57A mixed canonical plus academic strict xfail remains preserved. AG-61A
does not model simultaneous independent canonical and academic source classes.

## Validation Decision

No live validation was used.

Offline tests are sufficient because AG-61A changes deterministic follow-up
classification, compact follow-up handoff fields, and repo-tracked follow-up
prompt wording only. Live ProPlex, provider/model calls, web/search calls, and
independent source checks remain closed.

## Next Recommended Surface

If further gaps appear, keep the next phase in follow-up source-obligation
handoff consumption or deterministic saved-context source-fit diagnostics. If
the mixed canonical plus academic xfail must be repaired, stop for a separate
product/modeling phase first.
