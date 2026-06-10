# AG-93B Offline Golden Task / Answer-Ingredient Harness

Status: implemented as an offline fixture-backed evaluation harness.

## Purpose

AG-93B adds a deterministic harness for answering:

```text
For this task, the needed answer ingredients were available.
Did ScryRaven retrieve/classify/admit/use them correctly?
```

The harness grades truth-throughput and source posture through the current
authority chain:

```text
RunAuthorityContract
  -> EvidenceLedger
  -> SearchJudgment
  -> SufficiencyJudgment
  -> FinalAnswerPacket
  -> AuthorExecutor
```

It does not grade prose beauty except for non-failing `PROSE_STYLE_NOTE`
findings.

## Files

- `core/offline_golden_tasks.py` defines the golden task schema and JSON loader.
- `core/offline_golden_harness.py` normalizes observed snapshots and evaluates
  tasks.
- `tests/fixtures/ag93b/golden_tasks.json` contains eight synthetic golden task
  definitions.
- `tests/fixtures/ag93b/observed_snapshots.json` contains matching normalized
  offline observed-run snapshots.
- `tests/test_ag93b_offline_golden_task_harness.py` proves positive and
  negative behavior.

## Golden Families

The initial fixtures cover:

- current official fact;
- legal/regulatory current-primary fact;
- canonical technical documentation;
- source-bound numeric fact;
- ordinary explainer where reputable secondary evidence is allowed;
- conflict/changed-over-time fact;
- indirect inference from sourced premises;
- weak corpus / insufficient evidence.

All fixture sources use `fixture://` URLs and synthetic facts.

## Result Taxonomy

Machine-readable results expose:

- `PASS`
- `ANSWER_INGREDIENT_FAILED`
- `SOURCE_POSTURE_FAILED`
- `LEDGER_CUSTODY_FAILED`
- `SEARCH_JUDGMENT_FAILED`
- `SUFFICIENCY_POSTURE_FAILED`
- `FINAL_PACKET_FAILED`
- `FINAL_ANSWER_OMISSION`
- `UNSUPPORTED_CLAIM`
- `CITATION_ALIGNMENT_FAILED`
- `SEARCH_COUNT_OUT_OF_BOUNDS`
- `PROSE_STYLE_NOTE`

`PROSE_STYLE_NOTE` is non-failing unless another evidence/posture failure is
present.

## Usage

```python
from core.offline_golden_harness import OfflineGoldenTaskEvaluator
from core.offline_golden_tasks import load_golden_tasks
from core.offline_golden_harness import load_observed_run_snapshots

tasks = {task.task_id: task for task in load_golden_tasks("tests/fixtures/ag93b/golden_tasks.json")}
snapshots = load_observed_run_snapshots("tests/fixtures/ag93b/observed_snapshots.json")

result = OfflineGoldenTaskEvaluator().evaluate(
    tasks["ag93b_current_official_fact"],
    snapshots["ag93b_current_official_fact"],
)
print(result.to_dict())
print(result.human_summary())
```

Observed snapshots can be normalized dicts or objects exposing `to_dict`,
`to_projection`, `to_trace_fragment`, or `to_trace_projection`.

## Boundary

This phase is offline-only. It does not change production runtime behavior,
provider routing, provider selection, search depth, query generation,
retrieval/ranking/filtering, citation formatting, Author prose style, prompts,
DB/session shape, cache behavior, or live validation posture.

No live provider/model/search calls were run or authorized. No secrets, `.env`,
raw provider payloads, raw prompts, DB rows, private logs, caches, full raw
traces, local output packets, or private artifacts are required by the harness.
