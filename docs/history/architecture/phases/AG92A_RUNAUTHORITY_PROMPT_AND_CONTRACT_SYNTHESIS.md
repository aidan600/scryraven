Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG92A_RUNAUTHORITY_PROMPT_AND_CONTRACT_SYNTHESIS).

# AG-92A RunAuthority Prompt And Contract Synthesis

Status: implemented on `codex/ag92a-runauthority-contract-synthesis`.

## Previous Authority Shape

Before AG-92A, source obligations were assembled from local deterministic facts
inside downstream handoffs:

- Query production could bias queries through router/source-class heuristics, but
  it did not consume a canonical RunAuthority contract.
- EvidenceLedger owned custody after AG-91J, but requirements were observed from
  source-class recovery and final evidence facts rather than a pre-retrieval run
  contract.
- AnswerContract consumed EvidenceLedger where available, then fell back to
  source-class recovery telemetry and aggregate counts.
- FinalAnswerPacket consumed AnswerContract and EvidenceLedger outputs, but no
  first-class RunAuthority contract supplied source hierarchy policy.

That shape made obligations real only after helper/runtime surfaces rediscovered
them. AG-92A adds the missing early contract authority.

## New Owner

`RunKernel` now owns canonical RunAuthority contract state.

- Stage: `RUN_CONTRACT_STAGE`
- Action: `ActionType.RUN_CONTRACT_SYNTHESIZE`
- Observation: `ObservationType.RUN_CONTRACT_SYNTHESIZED`
- State: `RunState.run_contract`, `RunState.run_contract_projection`,
  `RunState.run_contract_validation`

The reducer accepts only a structured contract synthesis observation and stores
a JSON-safe projection. Trace/export derives from that RunState projection.

## Contract Model

New modules:

- `core/run_authority_contract.py`
- `core/run_authority_contract_templates.py`
- `core/run_authority_contract_prompt.py`
- `core/run_authority_contract_validation.py`
- `core/run_authority_contract_runtime.py`

The compact contract records:

- schema and contract id
- synthesis mode and validation status
- selected template ids
- user query hash/length reference, selected depth, and route facts
- question/claim type
- source requirements with strictness, class, tier, currentness, satisfaction
  rule, lower-tier use, and cannot-satisfy lists
- inference, conflict, numeric, recovery, and final-posture policies
- downstream hints for query production, EvidenceLedger, and final answer packet

The projection stores prompt hash/length and model/provider/effort identity when
smart synthesis is attempted. It stores no raw prompt, raw model response, raw
provider payload, secrets, DB rows, logs, caches, output packets, or full traces.

## Templates

The deterministic registry provides safe defaults:

- `current_official_numeric_or_rule`
- `legal_or_regulatory_current_primary`
- `canonical_technical_docs`
- `academic_literature`
- `ordinary_explainer`
- `user_document_or_personal_corpus`
- `indirect_inference`
- `conflict_sensitive`

Ordinary explainers prefer reputable secondary evidence without over-requiring
official/current sources. Current official numeric/rule, legal/current-primary,
canonical technical, academic, user-document, indirect-inference, and
conflict-sensitive questions get stricter obligations and posture policies.

## Smart Prompt

`core/run_authority_contract_prompt.py` frames the smart model as a research
director, not an Author, search helper, citation formatter, or vibes machine.
The prompt asks for strict JSON, compact rationales rather than chain-of-thought,
and forbids weakening official/current/legal/canonical/source-bound obligations
because retrieval may be hard.

The production executor accepts an injected `ask_model` callable and a
conservative `RunConfig.run_authority_contract_smart_model` opt-in. Default
pipeline behavior is deterministic template synthesis; tests exercise both
deterministic and smart-model paths with fake callables.

## Validation And Repair

Deterministic validation enforces source hierarchy invariants:

- official/current/source-bound requirements cannot become secondary-only
- legal/current-primary requirements cannot be satisfied by secondary explainers
- canonical current technical behavior requires canonical/project docs
- social/forum/community/aggregate/helper signals cannot satisfy stronger
  obligations
- source-bound numeric values stay unknown unless bound to an identified source
- lower-tier evidence remains context/leads for stronger obligations
- model output cannot remove stricter deterministic obligations
- malformed or unsafe model output falls back to the deterministic contract

Safe omissions are repaired when possible; invalid JSON or unsafe structure falls
back to deterministic template authority.

## Runtime Consumers

AG-92A wires multiple real consumers:

1. Query production / QueryPlan admission
   `execute_query_production_action` accepts `run_contract_projection`,
   converts it to source requirement hints, and stores those hints in reduced
   query posture. QueryPlan admission records a metadata-only
   `run_authority_contract` item showing the contract was consumed without
   changing query order.

2. EvidenceLedger
   The pipeline emits a RunKernel-authorized EvidenceLedger observation from the
   committed contract before query production. Ledger requirements retain
   `RunKernel.RunAuthorityContract:<contract_id>` provenance and custody gaps are
   evaluated by EvidenceLedger, not by the contract layer.

3. AnswerContract runtime handoff
   `RuntimeAnswerContractFacts` carries `run_contract_projection`. When ledger
   facts are unavailable, required contract source classes become missing
   obligations instead of being satisfied by aggregate source-tier counts.

4. FinalAnswerPacket preparation
   FinalAnswerPacket assembly accepts `run_contract_projection` and carries
   missing required obligations, mandatory caveats, and prohibited upgrades into
   the packet-derived Author payload.

Post-Author AnswerContract trace packaging remains compatibility-preserved in
AG-92A. AG-92B/AG-92C should decide whether active/post-author sufficiency
judgment should consume the contract directly.

## Compatibility-Only Or Demoted Surfaces

- Aggregate source-tier counts remain telemetry and fallback context; they do
  not satisfy stronger contract requirements when contract or ledger state is
  available.
- Source-class recovery still observes evidence and can produce recovery facts,
  but it does not own contract law.
- QueryPlan receives contract hints as metadata and does not let the contract
  rewrite query order in this phase.
- Pipeline orchestration authorizes and passes projections; it does not contain
  template selection, smart prompt construction, or source hierarchy validators.

## Opened Surfaces

AG-92A deliberately opened:

- RunAuthority contract prompt behavior
- deterministic template selection
- smart-model contract adaptation
- validation and repair
- query/source-obligation handoff
- EvidenceLedger requirement observation from contract state
- AnswerContract source-obligation handoff
- FinalAnswerPacket source-obligation handoff
- static guards for old non-contract authority shapes

## Closed Surfaces

The phase kept closed:

- live provider/model/search validation
- broad provider/search/retrieval/query rewrite
- retrieval ranking/filtering changes
- Author prose or citation style rewrite
- hosted/cache/deployment behavior
- secrets, `.env`, raw payloads, raw prompts, raw model responses, DB rows,
  private logs, caches, full traces, local output packets, and private artifacts

## Remaining Work

AG-92B should activate RunAuthority iterative search judgment against this
contract state. AG-92C should activate a sufficiency judge that decides whether
the committed contract and EvidenceLedger custody have been satisfied before the
final-answer packet is prepared.
