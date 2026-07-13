Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG56A_PROMPT_STACK_EXTERNAL_REVIEW_PACKET).

# AG-56A Prompt Stack External Review Packet

## Phase purpose

AG-56A built a sanitized local prompt-stack review packet for external Pro /
Deep Research model analysis. This was a packet-building phase only. It did not
rewrite prompts, change runtime behavior, run live validation, or call
providers/models/search.

## Local packet

Created local packet:

- `output/ag56a_prompt_stack_external_review_packet.md`

The packet is local/untracked, begins with `LOCAL/UNTRACKED — DO NOT COMMIT`,
and is intended to be pasted into a Pro / Deep Research model for systemic
prompt review. It includes prompt inventory, call-site and stage maps,
prompt-to-decision maps, source-quality instruction maps, academic vs canonical
docs policy context, likely conflicts, eval proposals, external-review
questions, and a clean paste-ready Pro-model prompt.

The local packet itself is not committed.

## Source-layer boundary handling

Referenced Project Source context was provided inline in the AG-56A prompt.

Inputs used:

- repo-tracked files in the local checkout;
- inline Project Source rules in the phase prompt;
- explicitly scoped sanitized local packets under `output/`;
- verified git/local repo state.

No Project Source files were assumed to exist in the repo unless repo-tracked.
No raw runtime prompts, raw provider payloads, DB rows, private logs, caches,
secrets, `.env`, or full traces were inspected.

Scoped local packets were available and used only for summarized sanitized
observations:

- `output/ag50f_output_quality_review_packet.md`
- `output/ag52a_output_quality_review_packet.md`
- `output/ag52b_output_quality_review_packet.md`
- `output/ag51a_output_quality_review_packet.md`
- `output/ag51d_post_policy_live_classification_packet.md`

## Repo files and prompt surfaces inspected

Required docs read:

- `docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md`
- `docs/codex/PHASE_BRIEF_TEMPLATE.md`
- `docs/history/architecture/phases/AG51B_SOURCE_ACQUISITION_ARCHITECTURE_REVIEW.md`
- `docs/history/validation/AG51C_CANONICAL_TECHNICAL_DOCUMENTATION_PROMPT_QUERY_POLICY_REPAIR.md`
- `docs/history/validation/AG51D_POST_POLICY_CANONICAL_TECH_DOCS_LIVE_CLASSIFICATION.md`
- `docs/history/validation/AG51A_EXISTING_PROVIDER_OFFICIAL_CANONICAL_RECOVERY_ACQUISITION_STRATEGY.md`
- `docs/history/validation/AG52B_OFFICIAL_CANONICAL_RECOVERY_CANDIDATE_VISIBILITY_CLASSIFICATION.md`
- `docs/history/validation/AG52A_OFFICIAL_CANONICAL_RECOVERY_EVIDENCE_ACCEPTANCE_SOURCE_FIT.md`
- `docs/history/validation/AG50F_OFFICIAL_CANONICAL_CANDIDATE_ACQUISITION_LIVE_CLASSIFICATION.md`

Primary prompt and prompt-adjacent surfaces inspected:

- `core/prompts.py`
- `core/canonical_technical_docs_policy.py`
- `core/official_canonical_recovery_query_acquisition.py`
- `core/official_canonical_recovery_candidate_acquisition.py`
- `core/official_canonical_recovery_execution_admission.py`
- `core/official_canonical_recovery_visibility_export.py`
- `core/official_numeric_source_grounding.py`
- `core/official_source_obligation_bridge.py`
- `core/official_source_obligation_candidate_visibility.py`
- `core/official_source_survival_diagnostics.py`
- `core/official_source_survival_projection.py`
- `core/source_class_recovery.py`
- `core/source_class_recovery_controller.py`
- `core/source_class_recovery_executor.py`
- `core/source_class_recovery_lifecycle.py`
- `core/recovered_evidence_visibility.py`
- `core/retrieval_quality.py`
- `core/routing.py`
- `core/source_classifier.py`
- `core/weak_corpus_controller.py`
- `core/pipeline.py`
- `core/pipeline_orchestrator.py` for call-site and stage mapping only
- `core/scout.py`
- `core/followup.py`
- prompt-policy, handoff, source-class recovery, Economist, Author, and
  prompt-leakage tests under `tests/`

## Use instructions

Use the local packet as the source material for an external systemic prompt
review. The Pro / Deep Research model should review conflicts, source-quality
hierarchy, prompt wording risks, protected surfaces, and offline eval
invariants. It should not be asked to run ProPlex, inspect private runtime
artifacts, or perform live validation.

## Confirmations

- No prompt behavior changed.
- No code behavior changed.
- No runtime prompts were copied from logs or traces.
- No live validation was used.
- No provider, routing, depth, citation, Analyst, Economist, Author, or
  Scrutineer behavior changed.
- `core/pipeline_orchestrator.py` was read only for call-site/stage mapping and
  was not edited.

## Checks run

- `git check-ignore -v output/ag56a_prompt_stack_external_review_packet.md`
- `git ls-files output`
- `git diff --check`
- `git diff --cached --check`

No pytest or live ProPlex validation was required because this was a doc-only
packet-building phase.

## Remaining recommended next action

Give `output/ag56a_prompt_stack_external_review_packet.md` to the external Pro /
Deep Research model. Use its findings to decide a future licensed prompt-review
or prompt-repair phase. Do not treat AG-56A itself as authorization for prompt
rewrites or runtime behavior changes.
