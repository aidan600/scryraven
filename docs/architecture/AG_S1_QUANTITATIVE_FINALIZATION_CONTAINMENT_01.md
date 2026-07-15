# Quantitative Finalization Containment

Status: current
Authority: canonical:quantitative-finalization-containment
Default-read: no
Applies-to: claim-scoped quantitative authority in every active accepted-prose finalization route
Does-not-authorize: new facts, calculation, conversion, claim admission, Sufficiency changes, route changes, acquisition changes, retries, or live validation
Verified-against-runtime: d8fac7719d1f6a3d50a804b7f6a0762c5268f59a
Update-trigger: merged change to quantitative FAP projection, Author numeric instructions, accepted-prose validation, or an active finalization entrypoint

## Responsibility

This document owns the installed invariant that unsupported derived
quantitative content cannot enter accepted user-facing answer prose. It does
not identify which earlier model or role first produced a rejected value. The
earlier origin of the observed B01/D02 values remains `NOT_OBSERVABLE`.

The repair classifies the existing finalization capability as `ADAPT`: it
reuses current FinalAnswerPacket, admitted-claim, D-prime, Specialist-result,
and prose-finalization owners, and adds one shared deterministic containment
owner at `core/quantitative_finalization_authority.py`. It creates no parallel
truth, admission, calculation, conversion, Sufficiency, or retry path.

## Claim-Scoped Authority Manifest

`quantitative_finalization_authority_manifest_v1` is derived from current FAP
authority. Its durable shape is:

```text
schema_version
source_fap_ref
authorized_numeric_claims[]
  local_claim_key
  claim_literal_ordinal
  current_claim_ref
  claim_authority_posture
  authority_kind
  normalized_numeric_value_text
  canonical_unit
  precision_posture
  evidence_or_specialist_ref
  applicable_dprime_ref
  applicable_dprime_consumption_ref
  admitted_claim_ref
  fap_material_ref
  semantic_claim_fingerprint_or_existing_equivalent
  literal_signature_digest
prohibited_transformations
claim_scoped
value_only_matching_prohibited
calculation_performed
conversion_performed
claim_admission_performed
sufficiency_changed
manifest_digest
```

The two authority kinds are:

- `direct_source_numeric`: the exact proposition and literal come from current
  FAP-authorized bounded source material. A current admitted component
  paraphrase may retain this kind only when its complete literal signature,
  component identity, exact content and coverage refs, and conservative
  subject/metric proposition core all bind to that same source material; and
- `specialist_derived_numeric`: the exact claim comes from a completed installed
  S1 result with canonical `result_unit`, `exact_match` claim-material binding,
  applicable component or synthesis D-prime consumption, admission, and current
  FAP inclusion.

Generic admission is not an authority kind. An admitted component, synthesis,
or hardened-FAP numeric proposition that has only a D-prime ref, observation
ref, coverage ref, matching value, or Author claim ref is omitted. It becomes
direct-source authority only through the complete source binding above, or
Specialist-derived authority only through the complete installed result and
consumption lineage above.

## Hardened Component Route

The hardened `SufficiencyReadiness -> HardenedFinalAnswerPacket ->
AuthorProseFinalization` route preserves two component-scoped quantitative
authority classes. Hardened direct source-explicit numeric authority requires
exact current component, semantic-observation, content, coverage,
evidence-custody, proposition-fingerprint, and complete literal-signature
binding.

Completed component S1 authority preserves the installed capability and
version, result and handoff identities and digests, canonical component target,
exact claim-material binding, canonical `result_unit` and precision, and
terminal consumption by the applicable component D-prime. Generic D-prime
admission alone remains nonauthority for arithmetic, conversion, aggregation,
comparison, or same-value proposition reuse. Deterministic AuthorProse accepts
valid bound direct-source and component S1 numeric claims and fails atomically
on unsupported quantitative prose.

The current hardened FinalAnswerPacket owner packages component entries only.
It does not project synthesis entries and does not install a hardened synthesis
sidecar. Ordinary synthesis-origin S1 authority remains owned by the ordinary
ComponentWorkGraph / synthesis D-prime / ordinary FinalAnswerPacket path.

The manifest is not a global numeric allowlist. A value/unit match is
insufficient without the same complete assertion fingerprint and literal
signature or the stricter current component/content/coverage equivalence above.
An authorized value cannot be reused for another subject, metric, calculation
result, conversion, estimate, comparison, ratio, rate, percentage, or
proposition.

Retained references are limited to bounded identifier, digest, status,
posture, route, and version shapes. Claim prose is used transiently to build
the fingerprint and the Author instruction, then omitted from the manifest.
The Author payload trace carries only shallow digest-and-count envelopes for the
manifest and multi-component entries, not the full manifest, graph entries, or
claim text.

## Before And After Author

Before ordinary Author execution, FAP adds fixed authority instructions and
transient exact quantitative renderings. Author may explain and present those
propositions while preserving value, unit, sign, scale, percent convention,
and precision. Comma digit grouping is the only installed numeric surface
equivalence. Author may not calculate, convert, estimate, interpolate, round,
rescale, aggregate, or introduce a new numeric conclusion.

After candidate prose exists, the shared deterministic validator:

1. removes URL syntax, machine citations, reference-only rows, true digests,
   and transport identifiers while keeping factual assertions under
   source/reference headings inspectable;
2. extracts bounded digit, compact-currency, and common-cardinal candidates,
   including bounded hyphenated forms;
3. preserves value, unit, accounting sign, scale, notation, percent convention,
   and declared precision in each literal signature;
4. emits enum-only unsupported markers for bounded ordinal, Unicode-fraction,
   fullwidth-digit, or unmatched numeric-looking nontransport surfaces;
5. fingerprints the complete assertion rather than the value alone; and
6. accepts only an exact manifest binding or fails closed.

This parser identifies candidates; it does not infer factual authority,
perform arithmetic, convert units, or act as a general language theorem
prover. Common cardinal forms are contained deterministically. Unsupported
quantifier forms fail closed rather than becoming a completeness claim about
all natural-language numbers.

The older two-item quantitative consistency diagnostic remains observable but
is subordinated. It no longer deletes or rewrites answer text.

## Active Finalization Route Inventory

| Accepted-prose route | Manifest source | Validation point | Failure effect |
| --- | --- | --- | --- |
| Ordinary `AuthorExecutor` | ordinary FinalAnswerPacket Author payload | after the one model response is fully buffered, before display or `AUTHOR_OUTPUT_OBSERVED` | rejected prose is not displayed or reduced; no retry |
| Deterministic `AuthorProseFinalization` | hardened FAP state/projection | before AuthorProse state or projection construction | no successful AuthorProse state |
| Follow-up AF5B response finalization | serialized follow-up/current FAP authority | during the existing AF5B validation context, before authorization/reduction | no successful Author observation or final-answer outcome |

No accepted-prose compatibility formatter bypasses the shared validator. The
ordinary route has no existing safe structured partial renderer that can
replace a rejected model response without editing or trusting it, so it blocks
rather than performing sentence surgery. No route automatically calls Author
again.

## Proof Posture

Focused offline tests establish:

- B-equivalent arithmetic rejection while the two direct source values remain
  individually eligible;
- D02-equivalent mile conversions and the derived mile difference rejection;
- subject, result, unit, precision, repeated-literal, sign, scale, percent,
  basis-point, scientific-notation, rate, textual-cardinal, and mixed-sentence
  adversarial controls;
- direct number, date, port, percentage, citation, URL, and comma-grouping
  controls;
- source-section assertions, compact currency, bracketed propositions,
  hyphenated cardinals, digest-shaped decimals, and leading numeric
  propositions cannot disappear into a zero-candidate acceptance;
- accounting currency parentheses preserve negative sign posture while valid
  positive, explicit-negative, Unicode-minus, and explanatory-parenthesis
  controls remain distinct and stable;
- component-origin S1 and synthesis-origin two-hop S1 positive paths produced
  by the installed adapter, registry, policy, and generic S0 handoff owners;
- canonical `result_unit`, explicit legacy-only `unit` compatibility, same-unit
  agreement, conflict rejection, exact claim-material digest, and consumed
  component/synthesis D-prime lineage controls;
- admitted non-Specialist component/synthesis arithmetic, conversion, and
  same-value proposition-laundering rejection while direct source propositions
  remain eligible;
- atomic rejection with no display, successful Author/AuthorProse/final
  outcome, answer rewrite, fragment deletion, or automatic retry; and
- absence of raw prompts, model responses, source text, provider payloads,
  private logs, and complete evidence candidates from retained manifests and
  diagnostics.

The reassessment's generic-conversion containment sentinel is now passing.
The four numbered-imperative route-qualification sentinels remain strict
expected-fails. The pre-FAP prompt-retention sentinel also remains expected-
fail: prompt retention is not accepted-output authority once post-Author
validation is mandatory, and removing it is not causally required by this
repair. Acquisition completeness is unchanged and was not converted.

## Nonproofs

- No live validation was performed.
- No route-qualification repair was performed.
- No acquisition-completeness repair was performed.
- No provider or model changed.
- No S1 proposal or invocation policy expanded.
- No new Specialist capability was added.
- No hardened synthesis path was activated.
- Broad live correctness, answer quality, and production stability remain
  unproved.

This offline repair also does not prove which upstream role originated a
rejected number, arbitrary-query coverage, unrestricted natural-language
number understanding, or citation correctness. It does not change component
selection, ranking, Specialist operators, conversion support, or Sufficiency
policy.
