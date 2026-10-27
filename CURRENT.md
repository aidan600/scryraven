# ScryRaven Current Truth

## Production baseline

Research–Answer Briefing Promotion 01 merged into `main` in
[PR #679](https://github.com/aidan600/scryraven/pull/679), merge commit
`33511b268d9b07ab10bc0725d488132fb5e3f324`. Its tree exactly matches reviewed
promotion head `c3fdcebdf6cc87a3b1902dcc05e11f229d089a6c`, from convergence
source `980c7db06a23d0f6f0ed7a95cee6df020fe7f0a5`.

The merged implementation includes operational repair
`c21d4274f8995ea601a91fb9bc5dbd0e7dbd368e`. Rejected one-pass Research,
Cheap Discovery batching and Parallel Semantic Lanes are not production paths.
The promotion passed the full offline suite (1,028 passed, four existing Windows
link/junction skips), Ruff, compilation, whitespace checks and all six configured
pre-commit hooks. Those checks establish mechanical behavior, not general
semantic reliability. See
`docs/operator/RESEARCH_ANSWER_BRIEFING_PROMOTION_01.md` for exact scope and review.

## Ordinary architecture

CLI, durable sessions and Reading Room share initial Research -> Answer ->
optional delegated Research returning to the same continuing Answer interaction.
Initial and delegated Research share one decision contract and episode loop.
Research investigates and develops one compact provisional briefing: useful
findings, relationships, qualifications and consequential unresolved needs.
A null update retains the latest account; newly resolving or changing evidence
calls for an updated account. The briefing reaches Answer alongside exact
selected originals. It is fallible working analysis, never external Evidence or
citation authority, and is not persisted as session state.

Answer owns final intellectual responsibility: meaning, synthesis, completeness,
supported/partial/unable posture, consequential missing needs and citations. It
may adopt adequate Research findings, inspect retained originals, calculate,
revise or reject the briefing, and request targeted Research. Delegation retains
the same native Answer interaction, library and resource accounting. There is no
third semantic owner, mandatory coverage checker, Analyst checkpoint, Answer
bypass, semantic router, fallback engine or alternate product path.

Search/Read/Find have operation-specific request shapes. One turn-scoped
acquisition history replaces overlapping operation packets. Exact selections
retain immutable source/version/range custody; valid selections survive invalid
neighbors with honest omissions. Schema/action failures have one Research
correction per episode. Invalid final shapes/citations share one Answer
correction allowance. Valid partials complete honestly; exhausted or incomplete
execution cannot publish provisional Research notes as an answer. Fit/repacking
loops, automatic unselected-source completion, mandatory citation localization
and full Answer-stage restart remain removed.

Each turn shares 900 seconds, 40 physically dispatched model requests, 16 external
attempts, 128,000 cumulative Answer source characters and 12 Answer local
operations. Individual model requests are capped at 300 seconds and remaining
turn time. No terminal reserve or separate Answer clock exists. Local inspection
does not spend external attempts; corrections and continuations share the same
limits. These are operational ceilings, not latency targets or evidence of
sufficiency. Research preserves a physical Answer completion opportunity where
feasible.

Architecture details: `docs/architecture/RESEARCH.md`. Historical design and native
continuation evidence: `docs/operator/RESEARCH_ANSWER_BRIEFING_01.md` and
`docs/operator/RESEARCH_FIRST_RESUMABLE_ANSWER_01.md`.

## Models, acquisition and operational repair

Shipped defaults are GPT-6 Luna / high / Fast Research and GPT-6.1 Sol / medium /
Fast Answer. Explicit `ModelConfig` injection takes precedence over an optional
complete per-user `model_roles.json`, which takes precedence over package-owned
`scryraven/model_roles.defaults.json`. Invalid user settings fail locally without
fallback. New ordinary turns resolve a fresh snapshot; explicitly retained model
instances retain theirs. The external file is the settings boundary; no settings
UI, write API, watcher or model-value environment overrides exist. These are
reversible configuration choices, not architectural requirements.

Exa supplies generic Search, Serper selectable lexical/community/current
navigation, and LinkUp static Fetch external known-URL Read. Serper snippets are
navigation only. Generic Exa queries describe the evidence objective while
retaining consequential entity, scope, chronology and comparison constraints.
Exa requests six results, `text=false` and Dynamic/high source-bound Highlights.
Generated provider synthesis is excluded. On the first fresh session turn with
no retained acquisitions, the first executed generic Search uses Deep and later
ones use Auto; other turns use Auto throughout. A failed executed Deep consumes
that bootstrap. Documents and non-generic operations do not consume it.

Groups of at most three contiguous independent generic Exa requests may overlap
network transport. Admission and identity allocation retain original request
order after transports settle. Mixed routes and other operations remain serial.
This is mechanical acquisition overlap, not parallel semantic interpretation.
No automatic provider fallback or retry policy is added. Search novelty counts
remain diagnostic only, excluded from role packets and stopping decisions.

The merged provider-configuration repair marks a definitively unconfigured Exa,
Serper or LinkUp unavailable only for the current turn, across both Research
episodes. Repeated requests to that provider are denied locally without another
external attempt, and fixed provider/failure codes reach both roles as operational
limitations. Other providers, retained material, documents and premise-only
answers remain available. Empty results, access/rate-limit errors and transient
failures do not disable configuration. A later turn starts fresh. The repair has
offline scripted verification; no dedicated live repair confirmation is claimed.

Ordinary transport is API-default. Optional programmatic ChatGPT-plan selection
uses the existing account flow and Windows CurrentUser DPAPI vault, with no API
fallback. Plan streaming uses `store=false` and does not promise API-equivalent
caching, requested service tier or output cap. API retains its 12,000-token output
cap. Missing usage remains unknown. The base `urllib3>=2.6,<3` watchdog dependency
does not require optional JWT/cryptography authentication packages for API use.

The forensic launcher injects the personal plan backend through the existing
Reading Room seam and delegates credential custody to the existing doorman.
Its child checks acquisition configuration and proves localhost readiness with
zero startup model dispatches; authentication/inference wait for the first ask.
This does not prove live account/model access. Ordinary launch selection is
unchanged. See `docs/operator/CHATGPT_PLAN_BACKEND.md` and
`docs/operator/BROKERED_COMMAND_SESSION_OPERATOR_FLOW.md`.

## Sessions and source custody

Immutable acquisitions, source identities, exact views and historical citation
snapshots survive save/reopen. Citation validation proves custody/membership,
not semantic entailment. New answers open their exact selected saved material;
historical localized citations retain their saved coordinates and hashes without
rewriting or provider I/O. Answer may inspect legitimate retained material not
selected by Research. Only originals actually supplied/read become citable.

Follow-ups receive fresh semantic decisions. Conversation is non-evidentiary task
context; explicit user premises may define a conditional task, while prior
assistant answers cannot silently become facts or premises. Research receives
historical citation navigation and the immediately preceding answer's actual
cited material when it fits attention. Historical Analyst records remain
decode-only history. All prior questions/answers are replayed without aging or
compaction; long-session performance and catalog scaling remain unproved.

SQLite schema 2 stores atomic revision-checked completed turns and session-owned
PDFs, with backward-readable historical turns. Failed asks do not commit partial
state. PDFs retain original bytes, identity and deterministic extracted text;
bounds are 20 MiB, 500 pages and 2,000,000 extracted characters. Local document
Read/Find spends no external attempt. No OCR, vision or image interpretation is
implemented. Textless pages are counted, and document provenance verifies what
the document states rather than outside-world truth. Answer's disclosure of
extracted-text-only coverage remains an observed limitation.

Reading Room and CLI share the session application, history and citation Reader.
Body-free dogfood diagnostics and opt-in source-bearing forensic observation
remain separate from session persistence and from each other. Raw provider
payloads, hidden reasoning and credentials do not enter those safe diagnostics.

## Demonstrated frontier and remaining limits

The nine ordinary convergence submissions used 37 physical model requests,
29 external attempts and 475.986 product seconds. They demonstrated briefing
receipt/adoption, compact factual and premise-calculation answers, targeted
Klamath delegation, developed Waymo comparison, honest sparse/community partials,
and a genuine retained Waymo follow-up with zero new acquisition. The follow-up
preserved the earlier turn and all 25 originals. Exact live revisions, reviews
and qualifications remain in `docs/operator/RESEARCH_ANSWER_BRIEFING_01.md`.

Known limitations include Klamath's missing unacquired October 2025 restoration
completion milestone and a smaller acquired-source geographic omission; Heidi's
repeated low-gain searches and duplicate profile inspection; and overlapping
Waymo reads plus long Answer latency/prose. These draws do not establish causal
efficiency improvements. Correction of a consequential mistaken briefing and
sensible stopping after failed community materialization are not newly
demonstrated. Generic Reddit body acquisition remains unreliable.

The separate four-case Luna/high Answer screen was reconstructed-packet,
fixed-evidence screening. Compact lookup and retained follow-up were comparable;
Waymo reasoning was materially weaker and Klamath failed the end-2025 reporting
cutoff. It does not justify replacing Sol/medium or establish ordinary PRODUCT
reliability. No model assignments changed in promotion or aftercare.

Earlier bounded evidence extends through open-world synthesis and dynamic
multi-component research; general completeness, currentness, semantic reliability,
acceptable dogfood latency and causal cost gains remain unproved. Level 6
revision/recovery under superseding Evidence is not established. No earned Sol
interpretation stage is implemented. Level-8 C02 remains operationally
unassessable; a later replay identified `content_filter`, not an output-cap
failure, without establishing historical reasons. See the tracked Level-7/8,
acquisition, finalization and latency reports for their exact evidence boundaries.

## Local evidence and aftercare

Post-merge aftercare removed classified disposable campaign output and clean
inactive auxiliary worktrees, retaining every branch reference. Three comparison
families (Klamath, Waymo, Heidi) retain exact public questions, originals, answers,
configuration, provenance and evaluation notes under ignored
`local-evals/candidates/`. Two already-indexed rejected-lane captures also remain
to preserve the unchanged index. These are development candidates, not new gold
or turnkey runnable tests. The local navigation receipt is
`local-evals/RESEARCH_ANSWER_COMPARISONS_20261027.md`; exact selections, cleanup
results and deliberately preserved worktrees are recorded in
`docs/operator/RESEARCH_ANSWER_POST_MERGE_AFTERCARE_01.md`.

Historical report paths to removed run trees describe original provenance, not
surviving copies. Earlier compact history remains indexed by
`local-evals/closure-2026-10-19/HISTORICAL_INDEX.md`. Local evidence is optional,
ignored and outside runtime. Unclassified forensic material, unrelated files,
credentials, saved user sessions and uncommitted auxiliary work remain untouched.
No implementation, new experiment, live PRODUCT execution or provider/model call
was part of this aftercare.
