# AG-82A Cache Architecture and Cost-Efficiency Design

Status: architecture design / docs-first; no runtime behavior change; no live validation; no provider/model/search calls; no runtime cache reuse

## Purpose and scope

AG-82A defines a durable cache and cost-efficiency architecture for ScryRaven so future phases can reduce repeated work without weakening source obligations, privacy boundaries, citation integrity, or current-answer safety.

This document is intentionally design-only. It does not implement cache keys, cache storage, cache instrumentation, cache reuse, provider/search/retrieval changes, prompt changes, final evidence changes, citation changes, `RunOutcome`/session/DB shape changes, or orchestrator rewrites. If future cache instrumentation needs `core/pipeline_orchestrator.py` hooks, this document records seams for AG-82B and AG-82C to consider; AG-82A stops at documentation.

The intended roadmap split is:

1. **AG-82A — Cache Architecture / Cost-Efficiency Design.** Repo-visible design only.
2. **AG-82B — Cache Instrumentation and Readiness.** Record cacheability, cost, latency, freshness, and reuse-block telemetry, but do not reuse artifacts for runtime decisions.
3. **AG-82C — Bounded Cache Reuse.** Enable narrowly scoped reuse only where keys, privacy scope, freshness, and source obligations are strong enough.

## Current-state inventory

The current repo already contains several persistence, dedup, telemetry, fixture, and output mechanisms that look cache-adjacent. They should not be treated as a general-purpose runtime cache without a later phase.

| Mechanism | Current surface | Classification | Cache relevance | AG-82A interpretation |
| --- | --- | --- | --- | --- |
| In-session duplicate-run guard | `core.run_dedup` normalizes query text, builds a JSON signature from query/mode/provider override/corpus state, and stores a TTL row in caller-owned memory. | **Dedup / guardrail**, not durable artifact cache. | Avoids immediate repeated user-run waste inside a short TTL window. | Useful precedent for normalized inputs and TTL handling, but not sufficient for source-obligation or evidence-safe cache keys. |
| Session history | `core.storage` writes `output/history.json` and per-session `*_passages.json`; Streamlit history reads and displays saved sessions. | **Persistence / saved output**, not runtime cache. | Supports user library/history UX. | Must not be reused as evidence unless future phases explicitly design source/freshness/key semantics. |
| Execution JSONL | `core.run_logging` appends `output/execution_log.jsonl` events and execution payloads. | **Telemetry / raw-ish run trace artifact**, not cache. | Provides cost, latency, provider, retrieval, and diagnostic observations. | AG-82B can add sanitized cache-candidate telemetry here or beside it, but full raw traces must remain local-only and not be committed. |
| SQLite telemetry summaries | `core.db` maps execution events into a `runs`/`sessions` SQLite schema with cost, latency, retrieval, output preview, and run summaries. | **Telemetry summary persistence**, not cache. | Enables aggregation and product cost review. | Candidate destination for coarse cache-readiness summaries only if schema changes are explicitly licensed later. |
| Cost accumulator | `core.cost_accounting` records model/search calls, token estimates, and cost snapshots by phase/model/provider. | **Cost telemetry**, not cache. | Establishes measurable cost surfaces. | AG-82B should build on this by attributing estimated avoidable cost/latency to cacheable steps. |
| Provider/search diagnostics | Retrieval/provider modules and aggregation scripts record provider attempts, errors, chunks, URLs fetched, and timing summaries. | **Telemetry / diagnostics**, not cache. | Identifies high-cost and high-latency retrieval paths. | Must remain observational until AG-82C; provider result reuse is high risk for current/source-obligation answers. |
| Output packaging and persistence side effects | `core.outcome_persistence_packaging` builds JSON-safe run/session/SQLite payloads; `core.persistence_side_effects` executes approved writes. | **Persistence helper layer**, not cache. | Clear seam between runtime facts and local artifacts. | Future instrumentation should use similar packaging/side-effect separation. Do not change runtime shape in AG-82A. |
| Runtime trace export attachment | `core.runtime_trace_export_attachment` attaches export/checkpoint-friendly trace fragments. | **Trace/export projection**, not cache. | Useful for review and replay diagnostics. | Never treat full trace as reusable evidence; future cache telemetry should be redacted and bounded. |
| KB trigger/backfill scripts | Scripts read `execution_log.jsonl` and append `kb_triggers.jsonl` review lines. | **Post-hoc review persistence**, not cache. | Shows local append-only review flows. | Cache telemetry can follow append-only principles but must avoid private logs and raw trace commits. |
| Offline UX demo fixtures | `ui.demo_fixtures`, `ui.pages_demo`, and `demo/fixtures/offline_ux_scenarios.json` project canned demo sessions. | **Offline fixtures**, not validation and not runtime cache. | Allows product-shell review without live providers or model calls. | Safe to reuse as fixture artifacts because they are explicitly demo-only and labeled. |
| Source/citation projections | `ui.source_display`, citation handoff contracts, final evidence bundle builders, and source-survival projections present source cards/source IDs/citation observations. | **Output projection / source-display metadata**, not cache. | Supports user trust and review readability. | Reusing a cached source list is unsafe unless source-obligation, evidence digest, freshness, and presentation posture all still match. |
| Export or saved-output surfaces | Saved sessions, passage JSON, history pages, and fixture sessions display reports and sources. | **Saved output artifacts**, not source-grounded runtime inputs. | Important for user library and future export flows. | Reuse for display is different from reuse for answering. Future export flows must preserve provenance and freshness labels. |

Distinctions that future work must preserve:

- **Real cache:** a keyed artifact reused to skip or shortcut future work. ScryRaven currently has no durable, source-obligation-aware runtime cache.
- **Dedup:** short-lived repeated-run interception. It can prevent waste but does not validate evidence reuse.
- **Persistence:** local storage of history, passages, telemetry, or summaries. Persistence is not consent to reuse.
- **Telemetry:** observations about calls, cost, timing, source classes, traces, and outcomes. Telemetry can guide reuse but must not decide answers.
- **Offline fixtures:** canned product-review artifacts. They are reusable only as demo data and must stay visibly labeled.
- **Output artifacts:** generated reports, source cards, passages, exports, and saved sessions. They are display/library artifacts, not proof that future source obligations are met.
- **Validation artifacts:** bounded review packets. They are not general cache inputs.
- **Raw traces and private/generated/local-only data:** local diagnostics only; they must not be committed, exported broadly, or used as cross-workspace cache contents.

## Cache layer taxonomy

| Candidate layer | What could be cached | Cost/latency/UX value | Main invalidation risks | Privacy risks | Roadmap posture |
| --- | --- | --- | --- | --- | --- |
| Document parsing | Parsed text/metadata for unchanged local files. | Avoid repeated CPU/parsing work; improves document-review latency. | File content hash/version, parser version, OCR settings, extraction bugs. | User-private document text. | AG-82B instrument; AG-82C safe early reuse only under local workspace scope; deeper policy in AG-83A/AG-84A. |
| Document chunking | Chunk boundaries, normalized text spans, section IDs. | Avoid repeated chunking and stable source-card anchors. | Parser output, chunker version/config, document version. | User-private document text and structure. | AG-82B instrument; AG-82C safe early reuse when document and chunker versions match. |
| Embeddings | Vectors for document chunks or fetched text. | Avoid repeated embedding model calls and speed corpus search. | Embedding model/version/config, chunk text, normalization, privacy boundary. | High: vectors can leak corpus membership/content. | AG-82B instrument; AG-82C only when model/version/document version/privacy scope match; fuller corpus design later. |
| User corpus indexing | Local index metadata, document IDs, chunk refs, source refs. | Enables personal library and repeated review without waste. | Corpus membership changes, document versions, index schema, permissions. | Very high: personal corpus contents and relationships. | Later AG-84A/local-corpus phase; AG-82A only records key and privacy requirements. |
| Fetched/readable pages | URL fetch result, readable text, title/domain, fetch timestamp, HTTP metadata. | Saves network latency and repeated fetch/readability cost. | Page updates, dynamic content, paywalls, robots/policy changes, currentness. | May include user-specific or sensitive fetched content. | AG-82B instrument; AG-82C freshness-gated only, blocked for official/current/legal when stale. |
| Source classification | Domain/source-class labels, official/canonical/current/reputable-secondary posture. | Avoids repeated classification and helps source obligations. | Domain role changes, page-specific classification, date/currentness, source-obligation changes. | Moderate; URL history can be sensitive. | Stable domain metadata can be AG-82C early; page/current-claim classification is caution/freshness-gated. |
| Source/domain/tier telemetry | Aggregated provider/domain success, source-survival, citation-fit, cost/latency stats. | Improves cost caps and future ranking decisions after explicit authorization. | Telemetry schema drift, sampling bias, stale provider behavior. | Low-to-moderate if aggregated; high if raw URLs/users retained. | AG-82B instrument as redacted aggregates; behavior use later only. |
| Provider search results | Provider query result URLs/snippets/metadata for non-current queries. | Avoids repeated provider calls; high cost/latency value. | Freshness, provider ranking drift, source obligations, regional/session variance. | Query and URL history can identify user interests. | AG-82B instrument-only; AG-82C only freshness-gated and never for stronger changed source obligations. |
| Stable prompt prefixes | Static prompt prefixes or policy blocks by prompt key/version. | Saves prompt assembly/tokens if provider supports prefix caching later. | Prompt version, mode, policy, model/provider behavior, hidden prompt changes. | Prompts are protected and may be sensitive. | Later only; AG-82A forbids prompt tuning or raw prompt caching. Instrument prompt identity, not prompt text. |
| Deterministic/replayable non-current model outputs | Summaries/classifications from stable inputs for non-current content. | Can reduce repeated synthesis/analysis costs. | Model/version/config, source digest, inference posture, unsupported values, prompt drift. | May expose user queries/documents and model-derived claims. | Instrumentation-only until strong safeguards; bounded reuse later for non-answer internal summaries only. |
| Offline fixture artifacts | Demo sessions and fixture source cards. | Reliable product demos without live cost. | Fixture schema/version, stale demo labels. | Low if committed fixture data is curated. | Safe reuse now as fixture/demo-only; AG-82C may cache fixture projections for UI speed. |
| Final answer exports | Saved reports, exports, report snapshots, source cards. | User library/export UX. | Freshness, changed obligations, citation integrity, model drift. | High if user-private or generated from private docs. | Display/export reuse only; blocked as answer input for current/legal/financial/government and changed obligations. |

## Cache-key design

Future cache keys must be explicit and conservative. Weak keys are dangerous because ScryRaven answers can depend on source class, currentness, inference posture, conflict arbitration, and presentation boundaries, not only on query text.

Likely key inputs:

- normalized user query and normalized intent/query type;
- mode/depth and any user-visible cost/quality posture;
- current date, requested date, and freshness boundary;
- source-obligation digest, including required source classes and official/current/canonical requirements;
- evidence/source digest over URLs, source IDs, document IDs, source titles/domains, fetch timestamps, and content hashes where available;
- conflict posture digest, including whether conflicts were found, unresolved, arbitrated, or blocked;
- indirect-inference posture digest;
- direct-vs-inferred presentation digest;
- provider/model/version/config identity, including embedding model identity when vectors are reused;
- retrieval settings: provider list, depth, query set/order, limits, domain constraints, recency bounds, ranking/filtering configuration;
- document/corpus IDs, content hashes, versions, parser/chunker/schema versions, and corpus membership version;
- privacy/session/workspace boundary;
- feature flag, cache schema version, and artifact type/version.

Illustrative, non-executable key shape:

```text
cache_key = hash({
  artifact_type,
  schema_version,
  privacy_scope,
  normalized_query,
  intent_and_mode,
  freshness_boundary,
  source_obligation_digest,
  evidence_or_document_digest,
  conflict_posture_digest,
  inference_presentation_digest,
  provider_model_config_identity,
  retrieval_settings_digest,
  document_or_corpus_version,
})
```

Weak keys are dangerous because they can cause:

- stale current/legal/financial/government claims;
- citation laundering, where old citations appear to satisfy a new or stronger source obligation;
- inference laundering, where model-derived or speculative claims are presented as source-bound;
- unsupported/model-derived numeric values masquerading as source-grounded values;
- cross-user, cross-session, or cross-workspace leakage;
- prompt/model/provider/config drift hidden behind a reused artifact;
- reuse across changed retrieval settings or source-obligation semantics.

## Invalidation and freshness policy

Freshness policy should be assigned before reuse, not retrofitted after a cache hit.

| Answer/artifact class | Default policy | Reuse examples |
| --- | --- | --- |
| Current/legal/financial/government rule answers | Block final-answer reuse; require fresh source-obligation evaluation and current official/primary sources. | A cached final answer about current IRS thresholds is blocked. A previously fetched official page is only a candidate if freshness and obligation gates pass. |
| Official/current source obligations | Source-obligation digest must match; source freshness must be checked; stale or secondary-only evidence cannot satisfy a stronger obligation. | A cached official-domain classification may be reused; the actual current rule content must be freshness-gated. |
| Ordinary non-current explainers | Allow bounded reuse candidates when query/mode/source digest/model identity match and no currentness markers exist. | A stable explainer about historical background may reuse fetched pages or summaries after TTL and source checks. |
| Academic/literature-style answers | Reuse may be safe for stable paper metadata, parsed PDFs, chunks, and embeddings; model summaries require source and model identity match. | Parsed unchanged arXiv/PDF text is a safe candidate; literature search results need publication-date/source-obligation checks. |
| Document-internal review | Reuse document parsing/chunking/embeddings for unchanged local documents within the same workspace. | Same uploaded PDF hash + parser/chunker/embedding version can reuse parse/chunks/vectors. |
| User corpus/library state | Invalidate on document add/remove/update, permission change, corpus index schema change, or workspace boundary change. | A personal corpus index is reusable only inside the same workspace/library version. |
| Provider/model/prompt/config changes | Invalidate or mark instrumentation-only when model, provider, prompt key/version, retrieval settings, or ranking/filtering config changes. | Embeddings from one model version cannot satisfy another model version key. |
| Source-obligation changes | Invalidate evidence/source-list/model-output reuse when required source classes, officialness, currentness, citation posture, or answer contract changes. | Cached secondary sources cannot satisfy a later official-source requirement. |
| Date-sensitive queries | Require explicit date/freshness key and TTL; block when current date crosses policy boundary. | “Who is the current CEO” requires fresh verification; a stale cache is blocked. |
| Non-date-sensitive queries | Permit longer TTLs for stable documents/sources with matching digests. | “Explain photosynthesis” can reuse stable document parsing and maybe source summaries. |
| Offline fixtures | Reuse by fixture id/schema/version only, always labeled demo-only. | Fixture source cards can be reused for demo UI; they cannot validate live retrieval. |

Examples:

- **Safe reuse:** unchanged local document hash + same parser/chunker version + same workspace -> parsed text/chunks reused for document review.
- **Instrumentation-only reuse candidate:** provider search result for a non-current ordinary explainer -> record that a hit would have occurred, but do not use it in AG-82B.
- **Freshness-gated reuse:** fetched official page with URL/content timestamp -> allow only if source-obligation digest, currentness policy, and TTL/fetch validation pass.
- **Blocked reuse:** final answer, citation list, or numeric claim for a current legal/financial/government question; any artifact containing raw prompts, raw provider payloads, full raw traces, or user-private documents without explicit storage design.

## Safety and privacy boundaries

Future cache phases must explicitly forbid caching, committing, exporting, or broadening access to:

- secrets;
- `.env` files;
- API keys;
- raw provider payloads;
- raw prompts;
- DB rows;
- private logs;
- cache directories/files;
- full raw traces;
- unrelated generated outputs;
- user-private document contents unless a future document/corpus phase designs explicit local storage, consent, retention, and deletion boundaries.

Safety rules:

- no cross-user leakage;
- no cross-workspace leakage;
- no stale official/current/legal/financial/government claim reuse;
- no unsupported/model-derived values masquerading as source-bound values;
- no cached citation list satisfying a stronger or changed source obligation unless the source-obligation digest still matches;
- no reuse across changed prompt/model/provider/config identity unless explicitly designed and tested;
- local-first privacy assumptions for personal use;
- future hosted/private deployments must revisit encryption, tenancy, retention, deletion, access logs, abuse monitoring, and enterprise/private corpus boundaries before enabling shared caches.

Redaction guidance for AG-82B telemetry:

- Prefer artifact type, hashes, counts, posture strings, policy classes, and reason codes.
- Avoid raw query text where a digest or short preview is sufficient.
- Avoid storing full source text, raw prompt text, raw provider payloads, DB rows, or full traces.
- Mark each artifact as safe-to-persist, safe-to-export, safe-to-commit, fixture-only, or local-private-only.

## Cost/latency telemetry plan for AG-82B

AG-82B should add instrumentation and readiness only. It may record candidate telemetry, but it must not reuse cached outputs for runtime decisions and must not change provider/search/retrieval behavior.

Each cacheable step should eventually record:

- cacheable step name;
- cache candidate identity or digest;
- privacy scope: global-public, workspace-local, session-local, fixture-only, or local-private;
- freshness class: current/legal/financial/government, official-current, ordinary-stable, academic, document-internal, fixture;
- provider/model/config identity;
- estimated cost;
- estimated latency;
- hit/miss candidate status;
- invalidation reason;
- reuse blocked reason;
- source-obligation digest;
- whether reuse would have been safe;
- redaction/output hygiene class;
- storage location class;
- whether the artifact is safe to persist;
- whether the artifact is safe to export or commit;
- whether the artifact is fixture/demo-only.

AG-82B expected behavior:

- add redacted candidate observations to existing telemetry surfaces or a tightly scoped adjacent artifact;
- measure avoidable cost/latency without skipping calls or changing decisions;
- preserve existing provider/model/search/retrieval behavior;
- preserve prompts, Author/Analyst/Economist/Scrutineer/synthesis-evaluator behavior, final evidence, citations, DB/session/RunOutcome runtime shape, and cache behavior;
- include static tests proving instrumentation cannot satisfy runtime decisions.

## Runtime reuse policy for AG-82C

AG-82C should start with low-risk, bounded reuse and keep high-risk answer surfaces closed.

### Safe early reuse candidates

- document parsing for unchanged local documents within the same workspace;
- document chunking for unchanged local documents with matching parser/chunker/schema versions;
- embeddings where embedding model/version/config, chunk text digest, document version, and workspace boundary match;
- offline fixture artifacts, by fixture id and schema version, always labeled demo-only;
- stable source/domain classification metadata where freshness does not matter and the source-obligation digest does not strengthen.

### Instrumentation-only candidates

- prompt-prefix identity observations;
- model-output summaries that would influence answer posture;
- provider search result hits for current or source-obligation-heavy answers;
- source-card projection reuse where final evidence/citation behavior could be affected;
- corpus-level reuse before AG-84A defines local library boundaries.

### Live-gated or freshness-gated candidates

- fetched/readable pages;
- page-level source classification for current claims;
- provider search results for non-current questions;
- non-current model summaries;
- source-card projections derived from unchanged evidence digests.

### Blocked or heavily gated candidates

- final answers for current/legal/financial/government questions;
- citation/source lists for changed source obligations;
- any unsupported/model-derived numeric values;
- raw prompts;
- raw provider payloads;
- full raw traces;
- raw DB rows;
- user-private documents without explicit local storage/privacy design;
- reuse across different users, workspaces, or provider/model/prompt/config identities.

## Relationship to product roadmap

This cache design supports productization by separating “work already done” from “evidence still valid.”

- **AG-81A offline UX/demo fixtures:** fixtures remain reusable and cost-free because they are explicitly demo-only, not validation or live evidence.
- **AG-81B answer-quality rubric:** cache telemetry can expose when cost-saving would have risked source quality, citation fit, inference posture, or unsupported values.
- **AG-83A document review:** parsing, chunking, and embedding caches are the strongest early product win for repeated document review.
- **AG-84A personal corpus/library:** corpus caches require workspace/library versions, document IDs, privacy scope, and local-first retention/deletion design.
- **Local-first productization:** local caches can reduce repeated provider/model cost while respecting personal workspace boundaries.
- **Repeated use without waste:** candidate telemetry should show repeated work by step and estimate savings before any reuse changes behavior.
- **Future hosted/private deployment:** tenancy, encryption, retention, deletion, access controls, and auditability must be resolved before shared caches.
- **Cost caps and latency UX:** cost/latency telemetry can power future UX that explains saved work, blocked reuse, or freshness-driven revalidation.
- **Future export flows:** saved answers and source cards can be exported with provenance/freshness labels, but exports must not become hidden answer inputs.

## Implementation roadmap

### AG-82B — Cache Instrumentation and Readiness, no reuse yet

- **Scope:** add redacted telemetry for cacheable step candidates, candidate keys/digests, cost/latency estimates, privacy scope, freshness class, invalidation/reuse-block reasons, and safe-to-persist/export/commit labels.
- **Non-goals:** no runtime reuse, no cache storage backend for answers, no provider/search/retrieval behavior change, no prompt tuning, no final evidence or citation changes.
- **Expected touched surfaces:** cost accounting telemetry, run logging/trace projection helpers, provider/retrieval diagnostics projection, document/demo surfaces if purely observational, tests/static guards.
- **Required tests/checks:** unit tests for redaction and reason-code stability; static guards proving no runtime cache decisions; tests proving provider/search/retrieval calls are unchanged; artifact-boundary tests for fixture-only/local-private labels.
- **Stop conditions:** if instrumentation requires changing provider routing, search depth, query generation, final evidence selection, citation behavior, prompts, DB/session/RunOutcome runtime shape, or `core/pipeline_orchestrator.py` beyond an explicitly licensed tiny hook.
- **Protected surfaces kept closed:** prompts, provider/search/retrieval behavior, source ordering/citations, Author/Analyst/Economist/Scrutineer/synthesis-evaluator behavior, runtime cache reuse, raw traces/payloads/prompts/secrets.
- **Live-validation posture:** none.

### AG-82C — Bounded Cache Reuse

- **Scope:** enable reuse only for the safest AG-82B-observed surfaces with strong keys, privacy scope, freshness policy, and negative-control tests.
- **Non-goals:** no final-answer reuse for current/legal/financial/government questions; no changed source-obligation citation reuse; no prompt/model/provider behavior change; no broad orchestrator rewrite; no hosted shared cache.
- **Expected touched surfaces:** explicit cache access layer, document parse/chunk/embedding artifacts, fixture projection artifacts, maybe source/domain metadata with conservative invalidation.
- **Required tests/checks:** key-drift tests, invalidation tests, privacy-boundary tests, stale-current blocked tests, source-obligation changed blocked tests, fixture-only tests, no-cross-workspace tests, static guards for protected surfaces.
- **Stop conditions:** any cache hit would alter final evidence/citations for a stronger source obligation; any raw provider payload/raw prompt/full trace is proposed as cache content; any cross-workspace reuse is needed without explicit design.
- **Protected surfaces kept closed:** all high-risk answer surfaces unless separately and explicitly licensed.
- **Live-validation posture:** none by default; if a future phase requests live validation, it must be a separate bounded validation brief.

### Optional later phase — Document/corpus cache integration

- **Scope:** design and implement local document/corpus storage, index versions, deletion/retention, encryption or filesystem boundaries, and user-visible library controls.
- **Non-goals:** no shared hosted cache by default; no implicit upload or cross-user corpus reuse.
- **Expected touched surfaces:** document ingestion/review, corpus index metadata, UI library controls, local storage privacy settings, export surfaces.
- **Required tests/checks:** document update invalidation, deletion, workspace separation, embedding model drift, export redaction, fixture/demo separation.
- **Stop conditions:** unclear consent/retention/deletion requirements; inability to separate public, workspace-local, session-local, fixture-only, and local-private artifacts.
- **Protected surfaces kept closed:** raw private documents are not committed or exported; provider/search/prompt/final-answer behavior remains separately authorized.
- **Live-validation posture:** none unless a future phase explicitly authorizes bounded live checks.

## Explicit non-goals

AG-82A must not:

- implement runtime cache reuse;
- implement cache-key code;
- change provider/search/retrieval behavior;
- change prompts;
- change final evidence selection;
- change citation behavior;
- change Author, Analyst, Economist, Scrutineer, or synthesis-evaluator behavior;
- change DB/session/`RunOutcome` runtime shape;
- change package, CLI, or environment-variable compatibility names;
- run live validation;
- touch secrets, raw prompts, raw provider payloads, DB rows, caches, full traces, or private logs;
- modify `core/pipeline_orchestrator.py`.

Protected surfaces explicitly kept closed:

- prompts;
- provider/search/retrieval behavior;
- provider routing, depth, selection, swaps, or new providers;
- query generation, finalization, recency merge, official-bias insertion, and ordering;
- retrieval ranking/filtering;
- final evidence selection;
- citation behavior and source ordering;
- Author prose and final-answer posture;
- Analyst, Economist, Scrutineer, and synthesis-evaluator behavior;
- DB/session/`RunOutcome` runtime shape;
- cache behavior, cache keys, and runtime cache reuse;
- package/CLI/env compatibility rename;
- live validation;
- hosted deployment;
- broad `core/pipeline_orchestrator.py` rewrite.
