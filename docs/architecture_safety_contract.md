# Architecture Safety Contract

Status: Phase 1 contract documentation. Classification: no-op/docs-only.

This note documents the safety boundary for the ScryRaven research pipeline.
It was originally written during the ProPlex/FauxPlex private-prototype era,
and some historical artifact names remain for continuity. It is descriptive
only: it does not authorize code, prompt, routing, retrieval, provider,
source-filtering, telemetry, Analyst, Economist, or Author behavior changes.

## Recommendation Classifications

| Recommendation | Classification |
| --- | --- |
| Document the pipeline contract and handoff rules. | no-op/docs-only |
| Keep active Project Sources to a small canonical set. | no-op/docs-only |
| Supersede old roadmap/baseline notes instead of duplicating them. | no-op/docs-only |
| Preserve JSONL as the rich safety trace and SQLite as summary telemetry. | no-op/docs-only |
| Keep Economist skip signals in shadow/safety telemetry only. | no-op/docs-only |
| Add or change assertions for these contracts in tests. | test-only |
| Add or rename telemetry fields. | diagnostics/telemetry-only |
| Use Economist output to skip Analyst, change weak-corpus gates, or route raw Economist artifacts to Author. | behavior-changing; prohibited by this contract |

## Pipeline Map

Router -> Retrieval -> Economist -> Analyst -> Author -> Telemetry

The pipeline may emit telemetry at several points, but telemetry does not change
the stage order unless an existing active gate already does so. In particular,
Economist shadow signals are diagnostic artifacts, not routing decisions.

## Stage Responsibility Table

| Stage | Responsibility | Must not do |
| --- | --- | --- |
| Router | Classify intent, query type, entities, report type, and mode-related routing metadata. | Bypass retrieval, select providers outside existing policy, or decide Analyst skip from Economist fields. |
| Retrieval | Search, fetch, chunk, score, filter, and assess corpus state, including existing weak-corpus recovery and pre-Analyst gating. | Change weak-corpus gating because of Economist output or send unsupported evidence forward as if healthy. |
| Economist | Produce bounded quantitative scaffolding, safety telemetry, raw framework output, and shadow `quantitative_packet` diagnostics when applicable. | Execute code, become the final analysis, skip Analyst, or hand raw artifacts directly to Author. |
| Analyst | Review evidence and any permitted quantitative scaffolding, synthesize conclusions, qualify uncertainty, and produce Author-ready analysis. | Treat raw Economist material as already reviewed or omit required caveats for weak evidence. |
| Author | Write the final user-facing answer from retrieved evidence and Analyst-reviewed synthesis. | Receive or rely on raw `quantitative_packet`, raw Economist framework text, or raw `economist_v1` JSON. |
| Telemetry | Record rich JSONL trace data, compact SQLite summary data, and read-only offline summaries. | Promote shadow fields into runtime control flow or let summarizer output affect behavior. |

## Artifact Handoff Rules

| Artifact | Producer | Allowed consumer | Rule |
| --- | --- | --- | --- |
| Retrieved evidence | Retrieval | Economist, Analyst, Author through approved context | Evidence remains source-bound and must carry enough provenance for citations and safety review. |
| Corpus state / weak-corpus directive | Retrieval | Analyst, Author, Telemetry | Existing pre-Analyst retrieval gating is active behavior and remains separate from Economist skip telemetry. |
| `quantitative_packet` | Economist shadow telemetry | Analyst only through a capped/review-oriented handoff | Raw packet is not Author-ready and must not be used as final analysis. |
| Raw Economist framework / `economist_v1` JSON | Economist | Analyst as unreviewed material; Telemetry as trace | Must be treated as unreviewed legacy or shadow material. It must not go directly to Author. |
| Economist skip candidate / skip eligibility | Telemetry helpers | Offline review and diagnostics | Shadow only. These fields must not skip Analyst or change routing. |
| Analyst-reviewed quantitative synthesis | Analyst | Author | This is the Author-facing quantitative handoff. It may include source-bound values, declared assumptions, and approved deterministic calculations only with Analyst review and appropriate qualification. |
| JSONL trace | Pipeline telemetry | Offline diagnostics, migration, summaries | Rich/source-of-truth safety trace for per-run behavior and safety anomalies. |
| SQLite summary | Pipeline telemetry / migration | UI summaries, compact analytics | Compact derived telemetry. It is not the full safety trace. |
| Summarizer output | Offline summarizer | Humans reviewing historical logs | Historical/read-only. It must not affect runtime behavior. |

## Active vs Shadow Gates

| Gate or field | Status | Contract |
| --- | --- | --- |
| Pre-Analyst retrieval gate | Active existing behavior | May skip or thin Analyst work only under existing retrieval/corpus rules and must emit stable reason telemetry. |
| Post-Economist Analyst skip | Forbidden/disabled | Economist output must not skip Analyst. |
| `economist_pre_analyst_skip_candidate_shadow` | Shadow only | Candidate signal for offline readiness analysis; no control-flow authority. |
| `economist_skip_eligible_shadow` | Shadow only | Posthoc eligibility signal; no control-flow authority. |
| `economist_skip_shadow_alignment` | Shadow only | Alignment label comparing shadow signals; no control-flow authority. |
| `analyst_skipped_after_economist` | Safety telemetry | Should remain false. True indicates a safety anomaly to investigate. |
| `economist_output_used_as_analysis` | Safety telemetry | Should remain false. True indicates a safety anomaly to investigate. |

## Glossary

Pre-Analyst retrieval gate: Existing retrieval/corpus quality behavior that can
alter Analyst work before expensive analysis when evidence is weak, off-topic,
or otherwise unsafe to synthesize at full depth.

Post-Economist Analyst skip: A forbidden path where Economist output would cause
the Analyst stage to be skipped after the Economist runs.

Economist skip candidate: A shadow diagnostic indicating that a future policy
might consider some Economist output reviewable. It is not active policy.

Posthoc skip eligibility: A shadow diagnostic computed after downstream handoff
checks to study whether a hypothetical skip would have looked eligible.

Raw `quantitative_packet`: The shadow `quantitative_packet_v1` artifact built
from Economist-adjacent telemetry. It is not Author-ready.

Raw Economist framework: Unreviewed Economist text or structured JSON,
including raw `economist_v1` output, before Analyst review.

Analyst-reviewed quantitative synthesis: The Analyst's vetted synthesis of
source-bound quantitative evidence and any permitted Economist scaffolding. This
is the only quantitative synthesis that may flow to Author.

## Hard Invariants

- Economist code execution is categorically prohibited.
- No Economist-driven Analyst skip.
- No direct Economist-to-Author handoff.
- Author must not receive raw `quantitative_packet`.
- Author must not receive raw Economist framework or raw `economist_v1` JSON.
- Existing weak-corpus retrieval gating is separate and unchanged.
- Every skip, drop, suppression, or safety block must emit stable telemetry and
  a stable reason.

## Telemetry Source of Truth

The JSONL full trace is the rich/source-of-truth safety trace. Use it for
per-run reconstruction, safety anomaly review, shadow gate analysis, and
historical debugging.

SQLite is compact summary telemetry. It is useful for UI and aggregate views but
does not replace JSONL when auditing safety handoffs.

Summarizer output is historical/read-only. It may help humans inspect trends,
but it must not feed back into runtime prompts, gates, routing, retrieval,
provider selection, source filtering, Analyst behavior, Economist behavior, or
Author behavior.

## Project Source Hygiene

- Keep active Project Sources to roughly 4-6 canonical notes.
- Supersede old roadmap or baseline notes rather than duplicating them.
- Do not upload raw transcripts unless the transcript itself is evidence.
- Keep Project Instructions compact and durable.
- Keep richer history, baselines, dated context, raw logs, transcripts, and
  implementation narratives repo-local unless they are compacted into a durable
  source and explicitly approved for Project Sources.
