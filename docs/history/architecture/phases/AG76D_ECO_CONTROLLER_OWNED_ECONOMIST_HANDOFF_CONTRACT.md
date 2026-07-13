Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG76D_ECO_CONTROLLER_OWNED_ECONOMIST_HANDOFF_CONTRACT).

# AG-76D-ECO — Controller-Owned Economist Handoff Contract

Date: 2026-05-31
Phase type: Core authority transfer
Mode: Architecture Groove / Prove Mode

## Licensed Protected Surface

AG-76D-ECO is limited to the Economist handoff seam: Economist admission,
preflight posture, source-bound quantitative packet identity, unsupported / missing
/ model-derived value posture, Economist output identity, Economist-to-Analyst and
Economist-to-Author exposure facts, no-code-execution safety posture, and
Controller / AnswerContract visibility for quantitative/source-bound posture.

Closed surfaces remain closed: Economist prompt text, Economist model behavior,
quantitative policy, source-bound numeric policy, Analyst behavior, Author
behavior, final-answer prose, citation formatting/selection, provider/search/query
behavior, Scrutineer, follow-up, DB/session/RunOutcome shape, cache behavior, live
validation, and package/CLI/env compatibility names.

## Previously Local / Orchestrator-Owned Economist Handoff State

Before AG-76D-ECO, `core/pipeline_orchestrator.py` held the runtime facts for the
Economist seam in local variables and trace assembly:

- `need_economist`, `economist_ran`, `economist_safety_telemetry`, and
  `economist_skip_reason` represented run/block/unavailable and safety posture.
- `economist_preflight_allowed`, `economist_preflight_block_reason`, and
  `economist_preflight_missing_entities` represented preflight posture.
- `economist_safety_telemetry["quantitative_packet"]` and related telemetry
  represented source-bound quantitative packet identity and validation posture.
- `target_metric_missing`, `unsupported_values`, `estimate_from_priors_requested`,
  and `estimate_from_priors_blocked_by_pre_analyst_gate` represented unsupported,
  missing, and model-derived numeric posture.
- `post_economist_gate`, `analyst_skipped_after_economist`,
  `analyst_after_economist_skip_reason`, and `economist_output_used_as_analysis`
  represented Economist-to-Analyst exposure posture.
- `analyst_quant_packet_handoff_telemetry` and `author_quant_source_telemetry`
  represented whether quantitative/Economist material reached Analyst or Author.
- Final trace construction copied these facts directly into the trace without a
  named Controller-owned Economist handoff contract.

## New Controller-Owned Contract / State

`core.economist_handoff_contract` now owns the passive
`EconomistHandoffState` contract and deterministic builder/executor functions:

- `build_economist_handoff_state(...)` consumes already-computed Economist,
  preflight, quantitative-packet, Analyst/Author, AnswerContract, and citation
  facts.
- `execute_economist_handoff(...)` returns a legacy-compatible mechanical
  envelope for existing handoff values without making new product decisions.
- `EconomistHandoffState.to_trace_fragment()` emits the additive
  `economist_handoff_contract` trace fragment.
- The contract stores sanitized identities and hashes/length metadata instead of
  raw prompt text, raw provider payloads, raw Economist JSON, local traces, DB
  rows, output packets, or secrets.

The contract is deterministic and passive. It copies, hashes, classifies
provenance, and exposes Controller-owned handoff facts. It does not run the
Economist, build prompts, call models/providers/search, execute code, change
quantitative policy, select citations, build final prose, or persist run output.

## Mechanical Executor / Handoff Boundary

The orchestrator remains the mechanical executor for existing runtime work:
retrieval, existing preflight model call, existing Economist model call when
allowed, existing quantitative packet creation in `core.pipeline`, existing
Analyst/Author calls, final-answer assembly, citation/source-list assembly, and
persistence packaging.

After the post-Economist gate produces existing facts, the orchestrator builds
`EconomistHandoffState` and consumes `execute_economist_handoff(...)` for the
legacy variables that continue downstream. After `AnalystAuthorHandoffState` and
`CitationSourceHandoffState` exist, the orchestrator rebuilds the Economist
contract with upstream contract refs and adds the sanitized trace fragment. This
keeps execution mechanical while moving the handoff authority facts into the
Controller-owned contract.

## Relationship to AnswerContract / Runtime Handoff

AG-76D-ECO stores an `answer_contract_ref` when runtime AnswerContract handoff
facts are available. The ref is copied/sanitized via the contract helper; it is
used for visibility only. The Economist contract does not change
AnswerContract/controller-ledger fulfillment semantics, obligation decisions,
evidence sufficiency decisions, or final-answer obligations.

## Relationship to AnalystAuthorHandoffState

AG-76D-ECO stores an `analyst_author_handoff_ref` and embeds Analyst exposure
facts:

- whether Analyst was skipped after Economist;
- the post-Economist skip reason;
- whether Economist output was used as analysis;
- whether a quantitative packet was injected for Analyst review;
- whether the Analyst reviewed the packet;
- explicit evidence that Economist output does not bypass the
  Analyst/Author handoff contract.

The contract does not alter Analyst prompt text, Analyst admission behavior,
Analyst synthesis behavior, Author prompt input behavior, or final-answer prose.

## Relationship to CitationSourceHandoffState

When available, AG-76D-ECO stores a `citation_source_handoff_ref` and embeds
Author exposure facts alongside citation/source-list handoff visibility. This is
visibility only. Citation selection, citation formatting, source-list ordering,
source-ID assignment/reuse, final evidence selection, and final-answer citation
behavior remain owned by the existing citation/source-list surfaces and are not
changed by AG-76D-ECO.

## Source-Bound Quantitative Packet Posture

The `SourceBoundQuantitativePacketDescriptor` records:

- packet presence, validity, direct-use eligibility, requires-Analyst posture,
  gate reason, and validation errors;
- packet schema version;
- packet hash and repr length;
- source IDs used;
- source-bound value count and hash;
- unsupported value count and hash;
- calculation-result count and hash;
- high-stakes quantitative posture.

The raw quantitative packet is not included in the contract trace. Existing
legacy trace fields remain present; the new contract trace is additive.

## Unsupported / Model-Derived Value Posture

The `UnsupportedQuantitativeValueDescriptor` records unsupported value count,
unsupported value hash, missing target metrics, source-bound/direct-use/requires-
Analyst flags, shadow pre-Analyst skip-candidate posture, and
estimate-from-priors requested/blocked facts. Unsupported and missing values stay
explicit and separate from source-bound values. The contract does not promote
unsupported/model-derived values into cited source-bound facts.

## Code-Execution Safety Boundary

The `EconomistSafetyDescriptor` records code-execution request/block status,
`economist_safety_status`, and explicit booleans that model-generated code
execution remains disabled. AG-76D-ECO adds no subprocess, eval, exec, shell,
dynamic-script, notebook, temporary-file, or equivalent execution path. Existing
`run_economist_code(...)` remains a blocking stub that reports disabled code
execution.

## Behavior Preserved

AG-76D-ECO preserves:

- Economist run/block/unavailable behavior;
- Economist preflight behavior and posture;
- source-bound quantitative packet identity and source-bound value posture;
- unsupported, missing, and model-derived value posture;
- no-code-execution behavior;
- Analyst/Author handoff behavior;
- final-answer prose behavior;
- citation/source-list behavior;
- provider/model/search/query behavior;
- DB/session/SQLite/RunOutcome shape;
- existing trace fields, with additive Economist handoff visibility only.

## Production-Active vs Shadow-Only Paths

The contract path is production-active for handoff authority visibility and for
mechanically returning the same downstream Economist handoff values already
computed by the runtime. It remains passive: all Economist execution, preflight
model calls, quantitative packet construction, Analyst/Author execution, final
answering, and citation behavior continue through the pre-existing paths.

No replacement Economist execution path was introduced. No shadow-only live
validation path was introduced.

## Tests Added / Updated

Added `tests/test_ag76d_eco_controller_owned_economist_handoff_contract.py`
covering:

1. Economist run/block/unavailable parity and skip reasons.
2. Preflight posture parity.
3. Source-bound packet identity and unsupported/model-derived posture.
4. No model-generated code execution boundary visibility.
5. Economist output non-bypass of Analyst/Author contracts.
6. Analyst/Author/final-answer/citation non-change flags.
7. Trace compatibility and additive `economist_handoff_contract` visibility.
8. Static protected-import guard for the contract.
9. Orchestrator authority guard for build/execute/use at the handoff seam.
10. Upstream AnswerContract, AnalystAuthorHandoffState, and
    CitationSourceHandoffState integration.
11. Protected-surface guard proving prompt/provider/search/DB/live surfaces remain
    unopened.

## Trace Compatibility and Additive Visibility

Existing Economist/quantitative fields remain in the execution trace, including
`economist_ran`, `economist_preflight_allowed`,
`economist_preflight_block_reason`, `economist_preflight_missing_entities`,
`economist_safety_telemetry` fields, quantitative packet telemetry,
Analyst/Author quantitative handoff telemetry, and post-Economist Analyst gate
fields.

AG-76D-ECO adds only `economist_handoff_contract`, a sanitized Controller-owned
trace packet. It does not include raw prompts, raw provider payloads, raw
Economist JSON, raw local traces, DB rows, output packets, or secrets.

## Economist Prompt Non-Change Note

Economist prompt text remains unchanged. The contract does not import or edit
`core.prompts`, does not assemble prompt text, and does not call `ask_model`.

## Analyst / Author / Final-Answer / Citation Non-Change Note

Analyst behavior, Author behavior, final-answer prose, and citation/source-list
behavior are unchanged. The new contract only references the existing
`AnalystAuthorHandoffState` and `CitationSourceHandoffState` once those states
already exist.

## Protected Surfaces Kept Closed

AG-76D-ECO keeps closed: Economist prompts, Economist model behavior,
quantitative policy, source-bound numeric policy, Analyst/Author/final-answer
behavior, citation behavior, provider/search/query behavior, source-class and
currentness classifiers, candidate-fit semantics, retrieval ranking/filtering,
Scrutineer, follow-up, DB/session/RunOutcome shape, LLM workflow cache, live
validation, direct source-specific hardcoding, and package/CLI/env/session/DB
compatibility names.

## Stop Conditions

Stop future ECO work instead of expanding scope if parity would require prompt
changes, Economist behavior changes, quantitative/source-bound policy changes,
model-generated code execution changes, Analyst/Author/final-answer/citation
changes, provider/search/query/model changes, ControllerEvidenceLedger or
AnswerContract decision-semantic changes, DB/session/RunOutcome changes, live
validation, cache implementation, package/CLI/env renames, direct source-specific
hardcoding, or a broad orchestrator rewrite.

## Recommended Next Phase

Recommended next phase: **AG-76D-FU — Follow-up as Controller Initial State**.

Rationale: the AG-76D core authority transfers now cover retrieval
stop/continue, Router/query preparation, retrieval loop, weak/failure gate,
Analyst/Author handoff, citation/source-list handoff, and Economist handoff.
Follow-up state remains a coherent remaining Controller initial-state seam and is
less coupled to the now-covered Economist/Analyst/Author handoff contracts than a
broad AG-77A transition.
