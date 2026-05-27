# Frozen eval query set (manual / CLI)

Use this list as a manual review aid when validating retrieval, utilization, or
author behavior after pipeline changes. It is not a benchmark, scoring policy,
golden-answer set, or approval to run live queries.

Live ProPlex CLI/UI/Streamlit/reference-query runs, provider/model calls, and
competitor comparisons require explicit approval before execution. Do not store
golden answers, raw transcripts, provider payloads, or competitor outputs.

For approved local review of existing run logs only, run offline summaries with:

```powershell
python scripts/aggregate_run_quality.py
```

Spot-check approved rows in `output/execution_log.jsonl` for
`utilization_rate`, `waste_flags`, and `latency_seconds`.

When explicitly approved, headless runs (no browser) use:

```powershell
python -m proplex "your query here" --mode Balanced
```

## Person / disambiguation

1. Scott Galloway controversy
2. Taylor Swift ticket policy Europe 2026
3. Sam Altman OpenAI board history summary

## News / recency

4. latest on [current major news topic — replace quarterly]
5. breaking news White House today
6. oil and equity markets past week

## Product / how-to

7. Diablo 4 battle pass purchase currency
8. most efficient difficulty for leveling in Diablo 4
9. how to enable two-factor on GitHub

## Academic / technical

10. arxiv attention is all you need summary for practitioners
11. CRISPR off-target mitigation methods 2025 2026

## Quantitative / comparison

12. compare cost per passenger mile MD-80 vs 777-300
13. average electricity price Germany vs France 2026

## Conceptual / broad

14. what causes auroras at mid latitudes
15. overview of EU CBAM implementation status

## Place / event

16. London Marathon 2026 men's winner time
17. state of aviation in Europe May 2026

## Ambiguous / thin evidence (failure UX)

18. fictional character from obscure podcast episode title only
19. single-word query: graphene

## Follow-up style (requires an approved app thread)

20. What sources contradict that conclusion?
21. Narrow to peer-reviewed only.

## Collision stress

22. Java Indonesia earthquake latest
23. Java programming language release timeline

## Misc coverage

24. Cursor IDE auto model list current
25. compare Brave vs Safari privacy defaults iOS

---

**Habit:** After substantive changes to `core/pipeline_orchestrator.py`,
`core/retrieval_quality.py`, or search providers, request approval before any
live query execution. When a local log review is approved, inspect approved
`output/execution_log.jsonl` rows with `aggregate_run_quality.py`.
