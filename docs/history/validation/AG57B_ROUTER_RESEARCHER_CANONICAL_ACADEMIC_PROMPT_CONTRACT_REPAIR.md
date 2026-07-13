Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG57B_ROUTER_RESEARCHER_CANONICAL_ACADEMIC_PROMPT_CONTRACT_REPAIR).

# AG-57B Router/Researcher Canonical-vs-Academic Prompt Contract Repair

## Phase Purpose

AG-57B narrows the repo-tracked Router and Researcher prompt contract for the
boundary between canonical technical documentation and explicit
academic/literature requests.

The phase is a prompt-contract repair only. It does not change provider
routing, recovery execution, evidence ranking, citation behavior, Author
behavior, or final-answer posture.

## Licensed Surface

Opened:

- Router prompt wording in `core/prompts.py`;
- Researcher prompt wording in `core/prompts.py`;
- offline prompt-contract tests;
- this validation note.

Closed:

- provider routing, provider selection, provider depth, provider integration,
  and new providers;
- deterministic recovery behavior beyond existing prompt-contract tests;
- source ranking, filtering, evidence acceptance, citation survival, and
  citation selection;
- Analyst, Economist, Author, Scrutineer, follow-up, weak-corpus, and
  final-answer behavior;
- `core/pipeline_orchestrator.py`;
- live validation;
- raw runtime prompts, raw provider payloads, DB rows, logs, caches, secrets,
  `.env`, and full traces.

## AG-57A Invariant Baseline

AG-57A was present on `main` at merge commit `7f4caa5`.

Relevant invariants preserved:

- canonical technical documentation remains the default source class for named
  software/database/API/package/project behavior unless the user explicitly
  asks for academic literature;
- explicit peer-reviewed, literature review, empirical study, benchmark
  literature, and arXiv requests remain academic;
- ordinary conceptual explainers do not force canonical documentation recovery;
- the mixed canonical plus academic obligation remains a strict xfail.

## Prompt Wording Changed

Router wording now clarifies that `is_academic=true` applies to explicit
peer-reviewed, literature, arXiv/preprint, empirical-study, independent
research, or academic benchmark-literature requests, or when peer-reviewed
evidence is authoritative for the user's requested claim.

Router wording also clarifies that named software/database/language/browser
API/package/SDK/protocol/project behavior, configuration/options, reference
semantics, release behavior, documented performance behavior, and tradeoffs
should normally use canonical/official/project documentation unless the user
explicitly asks for academic evidence.

Researcher wording now tells query generation to use docs/manual/reference terms
for those canonical technical cases and not add paper, arXiv,
academic-literature, or study terms unless the user explicitly asks for
peer-reviewed research, academic papers, empirical studies, literature reviews,
arXiv, or independent academic benchmark evidence.

## Tests Added Or Changed

Added:

- `tests/test_ag57b_router_researcher_canonical_academic_prompt_contract.py`

Coverage:

- Router prompt keeps canonical docs distinct from academic evidence;
- Researcher prompt uses docs/manual/reference terms for canonical behavior;
- canonical docs positive cases include PostgreSQL MVCC plus SQLite WAL, Python
  dataclasses, and MDN Fetch API;
- explicit academic controls include peer-reviewed PostgreSQL MVCC performance,
  SQLite WAL benchmark literature review, and arXiv database concurrency;
- ordinary conceptual explainer does not force canonical docs;
- AG-57A mixed canonical plus academic gap remains a strict xfail.

## Mixed Canonical Plus Academic Gap

The mixed obligation shape remains unresolved by design:

```text
What do the docs say, and what do studies show?
```

AG-57B does not model simultaneous independent canonical and academic source
obligations. That remains a product/modeling decision for a later phase.

## Validation Decision

No live validation was used.

Offline prompt-contract tests are sufficient for this phase because the licensed
surface is repo-tracked Router/Researcher wording and deterministic
prompt-policy invariants. Live provider/model/search runs remain closed.

## Next Recommended Surface

If future work wants to resolve the known mixed-obligation xfail, open a
separate product/modeling phase for multi-source AnswerContract representation.

Do not open provider routing/depth, adapters, citation, Author, or final-answer
behavior from AG-57B alone.
