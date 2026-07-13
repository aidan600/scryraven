Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (L1_SOURCE_CLASS_RECOVERY_DIAGNOSTICS).

# L1 Source-Class Recovery Diagnostics

Status: L1 diagnostics-only validation packet. Classification: pure/offline
telemetry exposure.

This note documents the sanitized `source_class_recovery_validation_l1` packet.
The packet is built from already-computed trace facts after retrieval and
authoring. It does not change provider routing, provider choice, search depth,
query construction, prompts, source ranking, final answer cleanup, persistence
schema, protected handoffs, or controller authority.

## Purpose

AG-22 showed official/legal/current-primary live failures, but the allowed
validation artifacts did not expose enough source-class recovery telemetry to
tell whether failure happened at recommendation, eligibility, provider/depth,
domain constraints, classification, recovered visibility, or final citation
survival.

L1 adds a compact sanitized packet that can be copied into validation notes or
summarized by `scripts/aggregate_run_quality.py` without opening raw traces,
provider payloads, prompts, DB rows, private logs, caches, or generated output
packets.

## AG-25 Alignment

The packet does not define a new action envelope. It carries an `ag25_action`
projection for the existing AG-25 action `recover_missing_source_class`:

- `name`: `recover_missing_source_class`;
- `status`: AG-25 status vocabulary such as `approved`, `blocked`, or
  `skipped`;
- `authority`: descriptor value from the AG-25 registry, currently `active`;
- `side_effect_class`: `retrieval` only when the existing controller approved
  the action, otherwise `none`;
- `handoff_boundary`: AG-25 descriptor value,
  `ordinary_evidence_eligible`;
- `executor`: the existing source-class recovery executor only when approved.

The packet sits beside the envelope as validation telemetry. It reuses the
action vocabulary but does not compete with, schedule, reduce, or execute
controller actions.

## Field Map

| Field | Consumer | Decision enabled |
| --- | --- | --- |
| `schema_version`, `diagnostic_only`, `sanitized` | Validation harness and aggregate script | Confirm the payload is the L1 safe diagnostics shape. |
| `ag25_action` | Architecture review | Verify the packet aligns with AG-25 `recover_missing_source_class` rather than inventing a parallel action abstraction. |
| `recovery_considered`, `recovery_recommended`, `recovery_eligible`, `recovery_used` | Live validation reviewer | Separate "not triggered" from "triggered but blocked" and "approved but not executed." |
| `trigger_reason`, `skip_reason`, `blockers` | Controller diagnostics reviewer | Identify whether the failure was recommendation, lifecycle eligibility, or scope/policy blocking. |
| `missing_source_classes` | Legal/source-quality reviewer | Identify whether the gap was official rules, legal text, current-primary, or another source class. |
| `recovery_query_previews` | Validation reviewer | Confirm the already-used recovery queries were plausible without exposing prompts or provider payloads. |
| `official_domain_constraints`, `jurisdiction_constraints`, `domain_constraint_source` | Legal-source validation reviewer | Check whether the official-domain lane constrained recovery and which jurisdiction lane was active. |
| `provider_attempts`, `provider_attempt_totals` | Provider diagnostics reviewer | Check provider, provider role, depth, max results, result count, accepted URL count, and failures where already available. |
| `active_result_count`, `active_new_url_count`, `accepted_url_count` | Recovery reviewer | Distinguish no candidates from candidates that failed acceptance. |
| `recovered_source_tier_counts`, `recovered_source_class_counts`, `recovered_official_or_primary_count` | Source classification reviewer | Determine whether accepted recovered URLs classified as useful official/legal/primary sources. |
| `recovered_promoted_source_count`, `recovered_visibility_decision` | Evidence visibility reviewer | Determine whether accepted recovered sources reached the final evidence bundle. |
| `recovery_source_quality_status` | Validation reviewer | Compact recovered-source quality result: official/primary found, secondary only, mismatch, no relevant sources, promoted but not final, or unknown. |
| `evidence_bundle_official_legal_current_primary_counts` | Validation reviewer | Check whether the final evidence bundle had official/legal/current-primary proxy support. |
| `final_cited_counts_available`, `final_cited_official_legal_current_primary_counts` | Citation survival reviewer | Check whether final cited sources included official/legal/current-primary support when citation IDs are parseable; a present empty citation-ID list is available zero-count telemetry, while an absent field remains unavailable. |
| `recovery_bottleneck_status` | Phase reviewer | Compact classification: `not_triggered`, `triggered_no_candidates`, `candidates_not_accepted`, `accepted_not_visible`, `visible_not_final_cited`, `satisfied`, or `unknown`. |
| `blind_spots` | Architecture reviewer | See explicit limits before using the packet to justify provider, domain, or legal retrieval tuning. |

## Sanitization Boundary

The packet includes only capped scalar fields, counts, domain names, selected
AG-25 descriptor values, provider attempt metadata, and capped query previews.
The builder ignores unrelated trace keys and redacts secret-like values in
strings.

It must not include secrets, `.env` values, API keys, raw provider payloads, raw
prompts, DB rows, full traces, private logs, caches, output-quality packets, or
unrelated generated outputs. Tests assert that raw/prompt/provider-payload
markers and secret-like values do not survive packet construction.

## Deletion Or Promotion Criterion

Delete this packet if a later M3 action-loop validation layer provides the same
diagnostic decisions through the shared AG-25 envelope without requiring raw
trace inspection.

Promote the useful fields into a stable validation contract only after at least
one bounded live validation proves that reviewers can diagnose official/legal
failure location from the packet alone and after the M3 action-loop design
decides where validation-visible action outputs belong.

## Known Blind Spots

- `current_primary_or_official` is represented as a proxy count unless a direct
  future field exists.
- Final cited counts require parseable final-answer source IDs.
- Provider candidate counts are limited to existing provider diagnostics fields.
- The packet cannot prove provider recall quality when a provider returns no
  accepted URLs and no raw candidate counts are safely available.
- It does not tune domains, providers, depth, query templates, prompts, source
  ranking, visibility rules, or final answer citation behavior.
