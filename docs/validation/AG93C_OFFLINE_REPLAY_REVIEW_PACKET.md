# AG-93C Offline End-to-End Replay Review Packet

Status: implemented as an offline review/export artifact.

## Purpose

AG-93C builds on the AG-93B golden-task harness by producing a compact packet
that explains why a replay passed or failed. The packet answers:

```text
Given what was available in the fixture or replay, did ScryRaven
retrieve/classify/admit/use the right answer ingredients, and did the final
answer match the evidence posture?
```

AG-93B remains the evaluator. AG-93C is the review packet that makes the
evaluation inspectable from query through final answer.

## Files

- `core/offline_replay_review_packet.py`
- `tests/test_ag93c_offline_replay_review_packet.py`
- `docs/validation/AG93C_OFFLINE_REPLAY_REVIEW_PACKET.md`

## Public API

```python
from core.offline_golden_harness import OfflineGoldenTaskEvaluator
from core.offline_golden_tasks import load_golden_tasks
from core.offline_replay_review_packet import (
    build_offline_replay_review_packet,
    render_offline_replay_review_packet_markdown,
)

task = load_golden_tasks("tests/fixtures/ag93b/golden_tasks.json")[0]
observed = {...}
result = OfflineGoldenTaskEvaluator().evaluate(task, observed)

packet = build_offline_replay_review_packet(task, observed, result)
machine_payload = packet.to_dict()
markdown = packet.to_markdown()
```

`build_offline_replay_review_packets_from_fixture_paths(...)` is available for
building one packet per matching AG-93B fixture task/snapshot pair.

## Machine-Readable Shape

Top-level packet fields:

- `schema_version`: `offline_replay_review_packet_ag93c_v1`
- `phase`: `AG-93C`
- `task_id`
- `metadata`
- `golden_expectations`
- `corpus_availability`
- `observed_contract`
- `observed_evidence_ledger`
- `observed_search_judgment`
- `observed_sufficiency_judgment`
- `observed_final_answer_packet`
- `final_answer`
- `ag93b_evaluation`
- `privacy`

The packet includes the AG-93B status, pass/fail boolean, failing statuses and
codes, non-failing prose notes, expected ingredients/source obligations/search
bounds/final-packet guardrails, observed contract and ledger summaries, search
and recovery counts, sufficiency posture, FinalAnswerPacket caveats and
citation-eligible source IDs, final answer text, observed ingredients/claims,
missing ingredients, unsupported claims, and citation alignment findings.

## Human-Readable Rendering

`packet.to_markdown()` renders a compact review packet with these sections:

- metadata;
- golden expectations;
- corpus/source availability;
- contract/ledger;
- search/sufficiency/final packet;
- final answer;
- AG-93B evaluation findings.

The renderer keeps `PROSE_STYLE_NOTE` visibly separate from evidence and posture
failures. Prose notes remain non-failing when structured ingredients, evidence
posture, and citation alignment pass.

## Privacy / Output Hygiene

The packet is built from sanitized fixture/replay projections. It blocks or
redacts forbidden private fields before output and reports only an aggregate
warning/count. It does not echo forbidden field names or values in the packet or
Markdown output.

Blocked/redacted private surfaces include raw provider payloads, raw prompts,
API keys, secrets, DB rows, cache blobs, private logs, and full raw traces.
Tests use synthetic forbidden fields only; no real secrets or private payloads
are required.

## Boundary

AG-93C is offline-only. It does not change production runtime behavior, provider
routing, provider selection, search depth, query generation, retrieval ranking
or filtering, source recovery behavior, prompt behavior, Author prose style,
citation formatting, DB/session shape, cache behavior, or live validation
posture.

`core/pipeline_orchestrator.py` is not changed.

No live ScryRaven/proplex provider, model, search, retrieval, or CLI dogfood
calls are part of this phase.

## Validation Coverage

Focused tests cover:

- passing AG-93B fixture packet construction and Markdown/dict output;
- missing expected ingredient surfaced in machine-readable and Markdown output;
- lower-tier/secondary evidence satisfying a stronger obligation;
- search/recovery count out-of-bounds reporting;
- direct sufficiency posture with missing obligations;
- dropped FinalAnswerPacket caveats/prohibited-upgrade guardrails;
- citation source alignment mismatches;
- non-failing prose notes separated from evidence failures;
- weak-corpus insufficient-evidence posture;
- privacy/output hygiene for synthetic forbidden keys;
- static offline-boundary guards for the AG-93C module.

## Known Limitations

The packet is a compact review artifact, not a dashboard, benchmark platform, or
new evaluator. It reports observed normalized replay facts and AG-93B findings.
It does not inspect raw traces or private runtime artifacts and does not tune
final-answer prose or runtime decisions.
