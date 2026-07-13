Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG94F_R1_WEAK_CORPUS_OFFICIAL_AUTHORITY_RECOVERY_ADMISSION).

# AG-94F-R1 Weak-Corpus / Official-Authority Recovery Admission

Status: implemented as an offline fixture-backed behavior repair.

Validation boundary: repo-visible code and synthetic fixtures only. No live
provider, model, search, retrieval, secret, `.env`, DB row, raw provider
payload, raw prompt, private log, cache, full trace, local output packet, or
private artifact access was used.

## Executive Verdict

AG-94F live recognition worked, but weak-corpus arbitration could still own the
path before official/legal/canonical source-class recovery spent its bounded
execution slot. The repaired rule subordinates weak corpus when structured
RunAuthority/source-class state shows an unsatisfied supported strong authority
obligation and executable recovery queries are available, while preserving
terminal, conflict, provider-policy, depth-policy, budget, and hard attempt-cap
blockers.

The phase also repaired generic legal/regulatory fallback wording. U.S. legal
artifacts such as Federal Register, CFR, eCFR, GovInfo, and Code of Federal
Regulations are now used only when U.S./federal context is present. Non-U.S. and
jurisdiction-neutral legal/regulatory fallbacks use generic authority language.

## Sanitized AG-94F Live Signal

The sanitized live query was:

```text
What official legal or regulatory source currently lists which preservatives or
additives are permitted in infant formula sold in Denmark? Answer from
official/current regulatory sources if available.
```

The live signal showed:

- required source class: `legal_or_regulatory_text` plus
  `official_current_rules` posture;
- official/current obligation unmet;
- source-class recovery queries existed;
- corpus was weak and weak-corpus ownership blockers were present;
- admission was considered but not eligible or used;
- acquisition repair was considered but blocked by an existing runtime blocker;
- source-class recovery execution was not attempted;
- final answer posture was acceptable insufficiency, but recovery never ran.

## Danish Query Lesson

The Danish query is useful because it stresses generic authority-seeking for a
non-U.S. regulatory task. It is not a Denmark-specific target. This phase did
not add Denmark regulator names, EU food-specific domains, source adapters, a
domain registry, or food-law corridors.

## Hardcoded Authority-Concept Problem

The prior generic legal/regulatory fallback treated U.S. legal artifacts as
generic authority language. For non-U.S. tasks, terms such as Federal Register,
CFR, eCFR, GovInfo, and Code of Federal Regulations are not harmless hints; they
encode a U.S. concept of where legal authority lives.

After repair, those terms remain available for U.S./federal tasks. Without
U.S./federal signals, legal/regulatory fallback queries use neutral terms such
as official legal text, current regulatory source, competent authority, primary
legal source, regulator guidance, approved list, and current rule.

## Exact Offline Reproduction

`tests/test_ag94f_r1_weak_corpus_official_authority_admission.py` adds a
synthetic live-shaped admission fixture:

- non-U.S. food/product safety regulation topic;
- required `legal_or_regulatory_text` and official-current authority posture;
- secondary-only evidence and unsatisfied stronger authority;
- weak corpus and weak-corpus ownership blockers;
- executable recovery queries;
- no terminal stop, conflict ownership, provider/depth policy blocker, hard
  budget exhaustion, or exhausted hard attempt cap.

Before the repair, neutral authority queries did not satisfy the old
query-text-based weak-corpus coexistence gate, so weak-corpus blockers remained
hard and admission stayed unused. After repair, admission is eligible and used,
weak-corpus blockers are removed or subordinated, and source-class recovery is
admitted.

## Root Cause

The break was a legacy arbitration mismatch:

1. Execution admission treated weak-corpus coexistence as partly query-text
   dependent. It required an unsatisfied official/legal class and a recovery
   query containing a small set of strings, including several U.S. legal-source
   artifacts.
2. Canonical/source-class primary-document obligations needed to remain tied to
   the existing authority-lifecycle permission path instead of gaining a broad
   weak-corpus bypass.
3. Acquisition-path visibility recognized the official-canonical query
   acquisition adapter, but native AG-94E-style source-class recovery
   recommendations with executable queries needed a narrower explicit
   visibility rule.
4. Generic legal/regulatory query generation injected U.S. artifacts into
   non-U.S. and jurisdiction-neutral fallback queries. Those generated terms
   could also make U.S. official-domain constraints appear for non-U.S. tasks.

## Weak-Corpus Coexistence Rule After Repair

Weak corpus is non-hard for recovery admission when all of these are true:

- the source obligation is required;
- at least one required class remains unsatisfied;
- the unsatisfied class is supported by the official/legal/canonical recovery
  lane: `official_current_rules`, `legal_or_regulatory_text`,
  `current_primary_or_official`, `primary_source_documents`, or
  `archival_primary_text`;
- bounded recovery queries exist;
- the recovery slot is available;
- no terminal stop, conflict ownership, provider/depth policy blocker,
  hard budget exhaustion, active recovery already used, or hard attempt cap
  blocks the lane.

Weak corpus may still inform final insufficiency posture. It no longer silently
owns the path when a stronger source obligation remains unsatisfied and a
bounded recovery attempt is otherwise available.

## Acquisition-Path Visibility Rule After Repair

Admission now treats a recovery path as visible when a native source-class
recommendation is present with:

- `source_class_recovery_recommended=true`;
- executable recovery queries;
- a supported stronger authority class in missing/required/gap/status fields;
- source-class, AnswerContract, RunAuthority, or official-obligation trigger
  provenance.

This does not make every weak-corpus path acquisition-visible. It is tied to an
unsatisfied supported stronger authority class plus existing recovery queries.

## Jurisdiction-Neutral Fallback Query Rule After Repair

Legal/regulatory fallback query wording now follows this rule:

- U.S./federal context present: U.S. legal artifacts may be used.
- No U.S./federal context: fallback uses jurisdiction-neutral authority terms.
- Existing EU/UK-aware domain hints remain bounded to explicit EU/UK context.

No local-language query expansion or multilingual retrieval was implemented.

## Language-Aware Authority Acquisition Future Work

The Danish query also shows why future authority acquisition may need to infer
likely source languages and search in those languages, then answer back in the
user's language. That is deferred. AG-94F-R1 does not implement language
shifting, multilingual retrieval, or local-language source expansion.

## Implemented Bounded Fixes

- `core/official_canonical_recovery_execution_admission.py`
  - Weak-corpus coexistence now relies on structured unsatisfied stronger
    authority classes plus recovery-query availability, not U.S.-coded query
    text.
  - Native source-class recommendations with supported strong classes and
    executable queries can make the acquisition path visible.
- `core/authoritative_source_action.py`
  - Hard iteration-budget exhaustion remains an admission blocker before the
    source-class lifecycle can spend an official/canonical recovery slot.
- `core/source_class_recovery.py`
  - Generic legal/regulatory and official/current fallback queries are
    jurisdiction-neutral unless U.S./federal context is present.

## Controls Proving Weak Corpus Still Matters

The AG-94F-R1 test suite proves:

- weak corpus still blocks or owns the path when no stronger source obligation
  exists;
- weak corpus plus a stronger obligation but no recovery queries remains
  ineligible;
- terminal stop still blocks;
- hard budget exhaustion still blocks;
- already-attempted hard cap still blocks;
- conflict-resolution ownership still blocks;
- ordinary explainer queries do not trigger official recovery;
- secondary-only evidence does not satisfy a stronger legal/regulatory
  obligation.

## Protected Surfaces Kept Closed

Kept closed:

- live provider/model/search/retrieval calls;
- provider routing, provider selection, provider order, provider depth, provider
  swaps, and new provider integration;
- search budget changes;
- curated domain registry or expanded hardcoded official-domain mappings;
- source-specific adapters;
- Denmark regulator, EU food, TSA, IRS, or package-docs hardcoding;
- multilingual/language-shifting retrieval;
- ranking/filtering overhaul;
- Author prose, prompt, citation, and final-answer behavior;
- package/CLI/env/database/session renames;
- `core/pipeline_orchestrator.py`.

`core/pipeline_orchestrator.py` line delta: `0`.

## Decision Packet For Next Validation

1. Did AG-94F live recognition work?
   - Yes. The sanitized live signal had required official/legal authority
     recognition and recovery queries.
2. Did weak-corpus arbitration block official/legal recovery?
   - Yes. Weak-corpus ownership remained a hard runtime blocker before the
     official/legal recovery execution slot was admitted.
3. Was provider/candidate acquisition tested?
   - No. This phase stopped upstream of providers and candidates and used only
     synthetic offline fixtures.
4. What admission/coexistence repair was made?
   - Weak-corpus blockers are subordinated when structured state shows an
     unsatisfied supported stronger authority class and executable recovery
     queries, with no terminal/conflict/provider/depth/budget/hard-cap blocker.
5. Did terminal/budget/conflict controls remain intact?
   - Yes. Focused controls cover terminal stop, hard budget exhaustion,
     already-attempted hard cap, and conflict-resolution ownership.
6. Was non-U.S./jurisdiction-neutral legal/regulatory query fallback repaired or
   deferred?
   - Repaired in bounded form. U.S. legal artifacts are conditional on
     U.S./federal context; neutral authority terms are used otherwise.
7. Was language-aware acquisition implemented, deferred, or explicitly out of
   scope?
   - Deferred and explicitly out of scope.
8. Should the next step be one live rerun of `food_regulatory_non_us` or
   rotating multi-family live validation?
   - Run exactly one live rerun of `food_regulatory_non_us` first. If it reaches
     `source_class_recovery_execution_attempted=true`, resume the remaining
     rotating AG-94F live families.
