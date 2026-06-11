# AG-94D Official Source Acquisition Quality Audit

Status: implemented as an offline audit with fixture-backed diagnostics and
bounded local repairs.

Branch: `codex/ag94d-official-source-acquisition-quality-audit`
Base: `8e5ba9ada76b290f9026539cc4bc8bc0c3be4afc`

Validation boundary: repo-visible code and tests only. No live provider, model,
search, retrieval, secret, DB, cache, raw prompt, raw provider payload, private
log, full trace, or local output packet inspection was used.

## Executive Verdict

The sanitized live shape is not an AG-94B custody/export/report regression. The
run reached the RunAuthority-subordinated source-class recovery lane, executed
provider/candidate acquisition, and exposed the failure at the acquisition and
candidate-fit boundary.

The audit found two local, fixture-proven weaknesses:

1. Role-only airport ID / accepted-ID recovery had airport-screening intent
   terms, but did not expose TSA/DHS as soft candidate official domains. Hard
   domains correctly remained empty for role-only inference, but the diagnostic
   plan was too weak to show the obvious official-domain targets.
2. Candidate fit rejected an official/current recovered duplicate when the same
   URL was already visible as a non-authority source. That produced the live
   shaped `already_visible_not_authority_satisfying` failure instead of allowing
   the recovered official candidate to satisfy the active obligation.

The audit did not prove that provider results containing official TSA/DHS pages
were dropped in the live run, because raw provider payloads were out of scope.
It added a diagnostic-only export classifier that can distinguish that case
when sanitized provider-result bridge records are present.

Final A-H classification: primary `D` and `E`; possible `C` as a query/targeting
quality contributor; `A`, `B`, `F`, and `G` not proven for the sanitized live
shape; `H` recorded as out-of-scope product posture follow-up.

## Acquisition Path Map

1. SearchJudgment authority begins in `core/run_authority_search_judgment.py`
   and is consumed by `core/run_authority_search_judgment_consumers.py`.
   `core/authoritative_source_action.py` applies the reduced SearchJudgment to
   source-class recovery compatibility facts.
2. Recovery queries are generated in `core/source_class_recovery.py` by
   `build_source_class_recovery_recommendation()` and `_candidate_queries_for_bucket()`.
   AG-50A query acquisition can append obligation-specific queries through
   `core/official_canonical_recovery_query_acquisition.py`.
3. Official authority plans are built in
   `build_official_authority_acquisition_plan()` and
   `_official_authority_acquisition_plan()`. Hard official domains and soft
   candidate domains are created from `_infer_official_authority_venue()`.
4. Hard official domains are projected into
   `source_class_recovery_official_domains`, copied through
   `record_source_class_recovery_lifecycle()`, and attached to the retrieval
   action metadata as `official_domain_constraints`.
5. Provider domain constraints are applied in
   `core/source_class_recovery_executor.py`: hard domains merge into
   `include_domains` and `exa_domain_filter` before calling
   `process_search_queries(..., provider_role="source_class_recovery")`.
   Soft candidate domains are diagnostic/query-plan hints only; they are not
   forwarded to provider include-domain arguments.
6. Provider results are returned through the injected `process_search_queries`
   executor seam. The executor tags usable returned passages with
   `_provider_role` and `retrieval_stage` of `source_class_recovery`, appends
   them to `all_passages`, and records provider diagnostics.
7. Result URLs/domains and source-class counts are summarized by
   `build_recovery_source_quality_diagnostics()` in `core/source_class_recovery.py`.
   Candidate-acquisition counts/statuses are built by
   `core/official_canonical_recovery_candidate_acquisition.py`.
8. Candidate official/canonical status is classified from recovered
   source-class/tier counts, source-fit projections, passport projections, and
   sanitized provider-result bridge records in
   `core/official_canonical_recovery_visibility_export.py`.
9. Candidate source-fit acceptance happens in
   `core/recovered_evidence_visibility.py`. It checks duplicate visibility,
   strong source class, required class match, explicit readability failure, and
   currentness before reserving a recovered authority source into final evidence.
10. Candidate fit/readability/passport state is projected by
    `core/authority_lifecycle_candidate_visibility.py` and
    `core/authority_candidate_passport.py`. Passport stages can distinguish
    readability, source-class misclassification, fit/currentness rejection,
    controller/context loss, and citation-surface loss when represented
    candidates are available.
11. Accepted/readable authority evidence enters canonical custody when
    `core/evidence_ledger.py` receives candidate/final-evidence observations.
    FinalAnswerPacket input is assembled through
    `core/final_answer_runtime_adapter.py` from EvidenceLedger/Sufficiency state.
12. Diagnostic/export fields are derived in
    `core/official_canonical_recovery_visibility_export.py`,
    `core/session_output_projection.py`, and
    `core/runtime_trace_projection_assembly.py`. These are observer surfaces,
    not final authority.

## Sanitized Live-Shape Summary

The live-shaped facts show:

- `required_source_class=official_current_rules`;
- official/current obligation unmet;
- recovery admitted and executed with two queries;
- provider role `source_class_recovery`;
- provider/candidate acquisition used;
- provider results returned;
- recovered domains mostly news: NBC, NPR, CBS, AP;
- one official/canonical-looking candidate was counted;
- zero accepted/readable official/canonical candidates;
- zero accepted readable authority evidence;
- source fit reported `no_matching_source_fit`;
- rejection included `already_visible_not_authority_satisfying`;
- next visible failure layer was `canonical_candidate_returned_not_accepted`.

This is a candidate-fit/source-targeting failure shape, not a final custody
success shape.

## Failure Taxonomy A-H

| Code | Meaning | AG-94D finding |
| --- | --- | --- |
| A | Provider did not return usable official TSA/DHS pages. | Not proven for live. Fixture now classifies news-only provider results as `provider_or_query_failed_to_return_official_candidate`. |
| B | Provider returned official TSA/DHS pages, but ScryRaven dropped or failed to forward them. | Not proven for live. Fixture now classifies sanitized bridge evidence as `provider_result_forwarding_or_filtering_dropped_official_candidate`. |
| C | Queries were too generic or news-attracting. | Plausible contributor. Current role-only queries use official/accepted-ID/airport-screening language but no TSA/DHS query terms and no soft-domain provider forwarding. |
| D | Official-domain targeting was too weak for role-only airport/ID recovery. | Proven as a diagnostic gap. Fixed by exposing `tsa.gov` and `dhs.gov` as soft candidate domains while keeping hard domains empty. |
| E | Candidate-source fit rejected an actually usable official page. | Proven by fixture. Fixed duplicate handling so non-authority visible context does not block a readable official duplicate. |
| F | Readability/passport/content projection failed to expose a usable official page. | Not proven for live. Fixture now classifies unreadable official candidates as `official_candidate_readability_or_passport_failed`. |
| G | EvidenceLedger/final authority custody failed after acceptance. | Not proven for live because accepted/readable count was zero. Fixture now classifies accepted-but-final-missing as `accepted_official_candidate_lost_after_acquisition`. |
| H | Final answer posture/prose over-emphasized news after recovery failed. | Out of scope. Recorded only; no Author/prose/citation behavior changed. |

## Provider Result Forwarding Findings

Hard official domains were already forwarded when present:

- `record_source_class_recovery_lifecycle()` copies
  `source_class_recovery_official_domains` into action metadata.
- `execute_source_class_recovery_action()` merges those domains into
  `include_domains` and `exa_domain_filter`.
- Existing and AG-94D tests prove this with `irs.gov` hard-domain fixtures.

Soft candidate domains were not forwarded and should remain non-forcing until a
future provider-hint policy is explicitly licensed. AG-94D adds diagnostic
counts to the visibility export:

- `provider_result_official_or_canonical_count`;
- `provider_result_represented_official_or_canonical_count`;
- `provider_result_unrepresented_official_or_canonical_count`;
- `official_source_acquisition_quality_layer`.

These fields use sanitized provider-result bridge records only.

## Query Wording / Official-Domain Targeting Findings

For role-only airport ID / accepted-ID tasks, the current plan produced useful
intent terms:

- `official current source`;
- `airport screening`;
- `accepted-ID guidance`;
- `enforcement-date notice`;
- `checkpoint requirements`.

Before AG-94D, the same plan did not expose TSA/DHS as soft candidate domains.
AG-94D now exposes `tsa.gov` and `dhs.gov` under `soft_candidate_domains`
through a family-keyed data file, not case-specific core dispatch predicates.
Queries still do not include TSA/DHS terms, and soft domains still do not affect
provider include-domain filters. That is the smallest bounded change within this
phase; broader query-template or provider-hint changes are a next-phase decision.

## Hard-Domain Vs Soft-Domain Findings

Hard-domain behavior remains appropriate for explicit agency families such as
IRS, USCIS, FDA, FTC, DOT, DOL, SEC, and similar contexts where the agency is
named or strongly inferred.

Role-only airport ID is different. It strongly suggests TSA/DHS, but forcing
those domains would be a provider-domain policy change. The correct AG-94D
repair was diagnostic: expose TSA/DHS as soft candidate domains so the next
phase can decide whether and how provider hints should consume them.

## Candidate Fit / Acceptance Findings

The local bug was in duplicate handling order. Before AG-94D, a recovered source
whose URL was already visible could be rejected before the recovered source's
own authority class was evaluated. If the visible copy was a non-authority
source, the rejection became `already_visible_not_authority_satisfying`.

AG-94D changes the rule:

- an already-visible duplicate blocks only when the visible source is already
  authority-satisfying for the active missing class;
- a recovered strong official/current duplicate survives the duplicate check;
- if it is accepted, it replaces the non-authority visible duplicate in final
  evidence instead of appending a duplicate URL;
- lower-tier and unreadable candidates remain rejected with durable reasons.

This is a local candidate-fit/visibility repair, not ranking, citation, prompt,
provider, or final-answer behavior tuning.

## Readability / Passport Findings

Readability remains a candidate-fit gate. Explicit
`readable_text_available=False` or `readability_status=readability_failed`
keeps an official-looking candidate out of accepted/readable authority evidence.

AG-94D did not add a fetch/readability provider. It only added a stable export
classification that reports readability/passport failures separately from
provider/query miss and generic source-fit rejection.

## EvidenceLedger / Final Custody Findings

No fresh EvidenceLedger or FinalAnswerPacket custody regression was proven.
The sanitized live shape had:

- accepted/readable official/canonical count: `0`;
- accepted readable authority evidence count: `0`.

Because no accepted official evidence existed, there was nothing for
EvidenceLedger/final authority custody to preserve. The new fixture matrix still
includes an accepted-but-final-missing case so future regressions classify as
`accepted_official_candidate_lost_after_acquisition` rather than reopening
provider/query diagnosis.

## Fixture / Test Matrix

New focused suite: `tests/test_ag94d_official_source_acquisition_quality.py`.

| Fixture case | Expected stable diagnosis |
| --- | --- |
| News-only provider results | `provider_or_query_failed_to_return_official_candidate` |
| Provider bridge includes TSA official result, candidate count remains zero | `provider_result_forwarding_or_filtering_dropped_official_candidate` |
| Readable TSA official guidance returned | accepted/readable count `1`; `official_source_acquisition_quality_satisfied` |
| Same TSA URL visible as news/non-authority context | official duplicate replaces non-authority duplicate; no `already_visible_not_authority_satisfying` rejection |
| Official candidate is historical/stale | `candidate_source_fit_rejected_official_candidate` |
| Official candidate is unreadable | `official_candidate_readability_or_passport_failed` |
| Accepted readable official candidate absent from final authority | `accepted_official_candidate_lost_after_acquisition` |
| Role-only airport ID plan | hard domains `[]`; soft candidate domains include `tsa.gov`, `dhs.gov` |
| Hard official domain fixture | hard domain forwards to `include_domains` and `exa_domain_filter` |
| Static fixture guard | no live provider/search imports in AG-94D tests |

Nearby updated regression:

- `tests/test_ag70b_irs_candidate_fit_readable_visibility.py` now preserves
  unreadable and lower-tier rejection coverage while allowing readable official
  duplicates to satisfy the active obligation.

## Implemented Bounded Fixes

1. `core/source_class_recovery.py` and
   `core/official_authority_venue_soft_domains.json`
   - Old behavior: airport accepted-ID role-only inference had no hard domains
     and no TSA/DHS soft candidate domains.
   - New behavior: it still has no hard domains, but exposes `tsa.gov` and
     `dhs.gov` as soft candidate domains from family-keyed data.
   - Boundary: diagnostics/query plan only; no provider routing, provider
     selection, search depth, query budget, Author prose, citation, or final
     answer behavior changed.

2. `core/recovered_evidence_visibility.py`
   - Old behavior: an official recovered candidate could be rejected solely
     because the same URL was already visible as non-authority context.
   - New behavior: only an already-visible authority-satisfying duplicate
     blocks. A readable official duplicate can replace the non-authority visible
     copy.
   - Boundary: local candidate-fit/visibility handling only.

3. `core/official_canonical_recovery_visibility_export.py`
   - Old behavior: `canonical_candidate_returned_not_accepted` did not separate
     provider miss, forwarding/drop, source-fit rejection, readability/passport
     failure, or accepted-evidence loss.
   - New behavior: `official_source_acquisition_quality_layer` exposes those
     distinctions from sanitized telemetry.
   - Boundary: diagnostic/export only.

## Decision Packet For Next Phase

1. Did the fixture audit prove provider returned official pages and ScryRaven
   dropped them?
   - It proved the diagnostic can expose that case when sanitized provider
     bridge records show an unrepresented official result. It did not prove that
     the live run did this.
2. Did it prove provider failed to return official pages?
   - Not for the live run. The live shape had one official/canonical-looking
     candidate. News-only fixtures are now classified separately.
3. Did it prove queries/domain targeting were too generic or news-attracting?
   - Partly. Airport role-only queries lacked TSA/DHS terms and no provider
     soft-domain hint is consumed. The audit did not run live provider
     experiments.
4. Did it prove candidate fit rejected a usable official source?
   - Yes. The duplicate-visible non-authority fixture reproduced and fixed the
     local `already_visible_not_authority_satisfying` class of failure.
5. Did it prove readability/passport failed after an official candidate appeared?
   - Not for the live run. The fixture path now exposes that case distinctly.
6. Did it prove accepted evidence was lost after acquisition?
   - Not for the live run. The fixture path now exposes that case distinctly.
7. What is the smallest next phase?
   - AG-94E should be a decision/implementation phase for role-only official
     domain hint consumption and airport-ID query specificity. It should choose
     whether soft candidate domains may become provider hints or query terms for
     TSA/DHS-style tasks, with offline fixtures first and any live validation
     separately licensed.

## Protected Surfaces

Kept closed:

- live provider/model/search/retrieval calls;
- provider routing, provider selection, provider order, provider depth, provider
  swaps, and new provider integration;
- broad query-template rewrite;
- source-specific TSA/DHS adapter;
- fetch/readability provider;
- Author prose, prompts, citation behavior, and final-answer formatting;
- DB rows, secrets, raw prompts, raw provider payloads, caches, private logs,
  full traces, and local output packets;
- package/CLI/env/database naming compatibility;
- `core/pipeline_orchestrator.py`.

`core/pipeline_orchestrator.py` line delta: `0`.
