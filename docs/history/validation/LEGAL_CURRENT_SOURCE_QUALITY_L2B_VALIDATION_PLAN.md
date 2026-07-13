Status: historical
Authority: none
Default-read: no
Historical-scope: Historical validation evidence / phase-validation record (LEGAL_CURRENT_SOURCE_QUALITY_L2B_VALIDATION_PLAN).

# L2B Legal/current Source-quality Validation Plan

## Status

Validation-plan note only. This document defines what L2C should validate using
the current provider stack after explicit live-validation approval. L2B used no
live ProPlex/provider/model/search calls and adds no runtime behavior.

## L2C Scope

L2C should classify failures, not fix them. It should run the exact reference
cases below with the current provider stack only and collect sanitized
diagnostics sufficient to distinguish source-obligation detection, recovery
eligibility, acquisition, acceptance/classification, evidence visibility, final
citation survival, and final answer posture.

L2C must not change provider routing, provider selection, search depth, provider
escalation, query generation, domain constraints, ranking, source
classification, evidence visibility, prompts, final-answer behavior, controller
authority, weak-corpus behavior, source-class recovery runtime behavior,
targeted retrieval runtime behavior, or protected handoffs.

## Exact Reference Cases

| Case id | Query shape | Expected source obligation |
| --- | --- | --- |
| `cta_fincen_boi_current_status` | "As of today, what is the current status of CTA/FinCEN BOI reporting obligations?" | Current official agency/legal source. FinCEN/BOI page, official rule/status update, agency notice, or official court/order/regulatory source if applicability changed. |
| `osha_heat_illness_prevention` | "What are OSHA's current heat illness prevention requirements or enforcement posture?" | Official OSHA source plus current rule/guidance/enforcement/rulemaking/legal text as applicable, including Federal Register, eCFR, OSH Act, General Duty Clause, or Regulations.gov context where relevant. |
| `eu_ai_act_dates_obligations` | "As of today, what EU AI Act dates, obligations, and implementation milestones apply?" | Official EU legal text and identifiers such as EUR-Lex/OJ/CELEX/ELI; Commission/AI Office guidance where current implementation status is central. |
| `ssdi_eligibility_positive_control` | "What are the current official SSDI eligibility rules?" | Official federal legal/regulatory sources such as eCFR, Federal Register, SSA official pages, or equivalent current regulatory text. |
| `court_injunction_status` | "What is the current status and effect of a named injunction or court order?" | Court docket, order, opinion, official court page, or reliable docket mirror. News may provide context but cannot satisfy legal status. |
| `legal_regulatory_current_event` | "What happened in a recent agency/court/regulatory event, and what legal effect does it have now?" | Reputable news can satisfy reported-event chronology. Official/legal/current support is required for current legal effect. |
| `secondary_legal_analysis_only` | "What do legal commentators say about a current rule or case?" | Secondary legal analysis can satisfy interpretation/context only. Embedded current-law claims require official/current support. |

## Expected Sanitized Diagnostics

Each L2C packet should contain only sanitized fields and should exclude secrets,
raw provider payloads, raw prompts, DB rows, caches, full traces, private logs,
credential material, and generated raw output packets.

Required diagnostic groups:

- Question classification: `legal_current_question_type`, `jurisdiction`,
  `currentness_required`, `official_current_primary_required`,
  `court_order_or_docket_required`, `legal_text_required`,
  `secondary_context_allowed`.
- Source obligations: `required_source_classes`, `must_cite_source_classes`,
  `currentness_fields_required`.
- Recovery lifecycle: `source_class_recovery_considered`,
  `source_class_recovery_eligible`, `source_class_recovery_used`,
  `recovery_reason`, `missing_source_classes`, bounded query previews,
  official domain constraints, provider role, provider depth, provider names,
  result counts, new URL counts, accepted URL counts, recovered tier counts,
  recovered source-class counts, and `recovery_source_quality_status`.
- Candidate disposition: official candidates returned, accepted, rejected,
  misclassified, stale/non-current where visible through sanitized fields, and
  any accepted official URL count.
- Evidence survival: accepted official sources visible to Analyst/Author
  evidence, official sources in final source list, official sources cited in the
  final answer, and secondary sources displacing official sources.
- Final posture: `legal_current_under_supported`, final answer posture,
  source-failure wording, and whether the answer avoided confident legal effect
  or compliance claims when source obligations were unmet.

Where an existing packet cannot provide a field, L2C should mark the blind spot
explicitly rather than inspect raw logs or payloads.

## Expected Output-quality Packet

If live validation is approved later, the local untracked output-quality packet
must contain:

- Exact query text and run settings needed to reproduce the validation.
- Final answer excerpt or summary sufficient to judge answer posture.
- Final cited URLs and source titles.
- Visible evidence source list with sanitized titles, URLs, source tiers, source
  classes, and short snippets if safe.
- Sanitized source-class recovery validation packet.
- Sanitized controller-loop/action packet sufficient to show whether recovery
  was considered, promoted, dispatched, blocked, or skipped.
- Case-level reviewer notes mapping observed behavior to the L2B bottleneck
  taxonomy.
- Decision note for whether the case supports no action, L2C repeat, or L2D
  candidate design.

The packet must not be committed unless a later phase explicitly asks for a
sanitized committed summary. The packet should live under an ignored output
location and should have a deletion or retention decision in the L2C final
bundle.

## Decision Rules for L2D

L2D is justified only if L2C shows repeated material failures under the current
provider stack and those failures block confident legal/current claims.

L2D may be justified when:

- The correct source obligation is detected and recovery is used, but no
  official candidates are returned across repeated cases.
- Official sources require stable identifiers or source-specific lookup that
  general search fails to acquire, such as CELEX, ELI, CFR part, agency docket,
  or court docket/order identifiers.
- Official candidates are available through a narrow public official source/API
  and the current stack repeatedly misses them.
- The failure remains after source-class and visibility diagnostics prove the
  issue is acquisition/resolution rather than final citation survival or
  classification.

L2D is not justified when:

- The issue is only final answer posture, citation survival, or source dominance.
- Official sources were found and cited in a positive-control pattern.
- The only support is one failed run without repeated sanitized diagnostics.
- Fixing the issue would require provider routing, search depth, prompts,
  ranking, handoff, or controller authority changes outside an explicit phase.

## Stop Conditions for Live Validation

Stop L2C live validation if any of these become necessary:

- Raw traces, raw provider payloads, raw prompts, DB rows, caches, logs, secrets,
  credentials, or API keys.
- Provider routing, provider selection, provider depth, provider escalation, or
  query/domain strategy changes.
- Source classification, ranking, evidence visibility, final citation behavior,
  prompt, final-answer behavior, or protected handoff changes.
- A new source-specific API, adapter, resolver, legal-source framework, schema
  migration, or broad test harness.
- Output-quality packet contents cannot be sanitized enough to share or review.
- Test or validation results reveal an architecture choice outside L2C scope.

## Case-specific Pass/fail Expectations

| Case id | Pass condition | Failure classes to distinguish |
| --- | --- | --- |
| `cta_fincen_boi_current_status` | FinCEN/official legal-current source is required, recovered or already visible, and cited for current status; otherwise final posture is caveated. | Need not detected; recovery not triggered; no official candidates; query/domain insufficient; unavailable from stack; final posture too confident. |
| `osha_heat_illness_prevention` | Official OSHA/legal text/rulemaking/enforcement source is required and cited when current requirements or enforcement posture are claimed. | Need not detected; recovery not triggered; no official candidates; official rejected/misclassified; final posture too confident. |
| `eu_ai_act_dates_obligations` | EUR-Lex/OJ/CELEX/ELI or official EU implementation guidance is visible and cited for legal-current obligations; secondary sources do not satisfy legal-effect claims. | Official misclassified; accepted official not visible; visible official not cited; secondary displacement. |
| `ssdi_eligibility_positive_control` | Official federal legal/regulatory sources satisfy the obligation and survive to final citation. | Regression in official-source satisfaction, visibility, or citation survival. |
| `court_injunction_status` | Docket/order/opinion/official court page/reliable docket mirror supports status claims; news only is caveated. | No docket/order candidate; source unavailable from stack; final posture too confident. |
| `legal_regulatory_current_event` | Reputable news can answer what happened, while legal effect is caveated unless official/current source is found. | News incorrectly satisfies legal-effect obligation; missing official-current caveat. |
| `secondary_legal_analysis_only` | Secondary analysis is labeled as interpretation/context and not treated as current legal authority. | Secondary analysis used as current law; final posture too confident. |

## Local Packet Minimum Fields

If approved later, each local packet must include:

- `case_id`
- `query`
- `run_date`
- `provider_stack_summary`
- `final_answer_posture`
- `final_cited_urls`
- `required_source_classes`
- `must_cite_source_classes`
- `currentness_fields_required`
- `source_class_recovery_considered`
- `source_class_recovery_eligible`
- `source_class_recovery_used`
- `provider_attempts`
- `candidate_counts`
- `accepted_url_count`
- `recovered_source_class_counts`
- `evidence_visibility_status`
- `final_citation_survival_status`
- `bottleneck_classification`
- `l2d_decision`
- `redaction_review`

This packet is for L2C reviewer decision-making only. It should not become
runtime telemetry unless a later phase names the consumer, promotion rule, and
retention/deletion criteria.
