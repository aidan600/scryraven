Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (AG8_OFFICIAL_LEGAL_CALIBRATION).

# AG-8 Official/Current Legal Calibration

Status: offline calibration revision completed; no live validation used.

Scope: improve answer-contract family/posture calibration for official/current
legal questions when Router metadata says news/current-events, and surface
official/current evidence gaps in the handoff without promoting active behavior.
This phase did not change provider routing, prompts, search-depth policy, source
ranking/filtering, persistence schema, social provider integration, or downstream
handoff consumers.

Base: updated `main` at `780d2a9a06ba172bbf797ab1b1e902deb0d086b3`.

## Calibration Change

- Added general current legal-rule cues for obligations, compliance, deadlines,
  enforcement milestones, timelines, eligibility, and primary legal text.
- Official/current legal-rule cues now beat Router `intent=news` only when the
  user asks for rules, obligations, requirements, deadlines, enforcement,
  compliance, timelines, or primary text.
- Developing-event posture is preserved for breaking-policy-news and unsettled
  agency/guideline status questions.
- Choice/recommendation wording remains recommendation-first when legal context
  is only a constraint on a product or tool decision.

## Validation

| Check | Result | Notes |
| --- | --- | --- |
| `py -m pytest tests/test_answer_contract_calibration_ag8.py --basetemp=C:\tmp\.pytest-tmp-ag8-focused -o cache_dir=C:\tmp\pytest_cache_ag8_focused` | pass, 9 passed | Positive and negative-control AG-8 calibration cases. |
| `py -m pytest tests/test_answer_contract_calibration_ag6.py` | pass, 9 passed | Initial run emitted repo-local pytest cache warning. |
| `py -m pytest tests/test_answer_contract_runtime_validation.py` | pass, 9 passed | Initial run hit known repo-local `.pytest-tmp` cleanup permission issue after 8 passed; rerun used `C:\tmp`. |
| `py -m pytest tests/test_answer_contract_runtime_handoff.py` | pass, 9 passed | Initial run hit known repo-local `.pytest-tmp` cleanup permission issue after 8 passed; rerun used `C:\tmp`. |
| `py -m pytest tests/test_answer_contract_controller.py tests/test_answer_contract_pipeline_adapter.py tests/test_answer_contract_loop_harness.py` | pass, 32 passed | AG-1/2/3 controller, adapter, and loop harness. |
| `py -m pytest tests/test_weak_corpus_controller.py tests/test_weak_corpus_recovery.py --basetemp=C:\tmp\.pytest-tmp-ag8-weak -o cache_dir=C:\tmp\pytest_cache_ag8_weak` | pass, 14 passed | Protected weak-corpus guardrail scan. |
| `py -m pytest tests/test_source_class_recovery_controller.py tests/test_source_class_recovery_lifecycle.py --basetemp=C:\tmp\.pytest-tmp-ag8-source -o cache_dir=C:\tmp\pytest_cache_ag8_source` | pass, 11 passed | Protected source-class guardrail scan. |
| `py -m pytest tests/test_retrieval_stop_controller.py --basetemp=C:\tmp\.pytest-tmp-ag8-retrieval -o cache_dir=C:\tmp\pytest_cache_ag8_retrieval` | pass, 10 passed | Protected retrieval-stop guardrail scan. |
| `py -m ruff check .` | pass | No lint failures. |
| `git diff --check` | pass | No whitespace failures. |
| `py -m pytest --basetemp=C:\tmp\.pytest-tmp-ag8 -o cache_dir=C:\tmp\pytest_cache_ag8` | expected path-name failure | 969 passed, 1 failed because `test_pytest_tmp_path_hardening.py` expects a path segment named exactly `.pytest-tmp`. |
| `py -m pytest --basetemp=C:\tmp\.pytest-tmp -o cache_dir=C:\tmp\pytest_cache_ag8` | pass, 970 passed, 1 deselected | Full offline suite. |

## Result

AG-8 resolves the AG-7 official/current legal calibration failure class for the
bounded offline cases. EU AI Act GPAI obligations and federal EV charger tax
credit rules now draft official/legal answer-contract posture even when Router
metadata says news/current-events. Unsettled agency/guideline status remains
developing-event posture and, with secondary-only evidence, surfaces the missing
`current_primary_or_official` evidence class in the handoff.

This supports another bounded live validation pass. It does not justify active
behavior promotion.
