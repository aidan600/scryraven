# Quantitative Finalization Containment

Status: current
Authority: canonical:quantitative-finalization-containment
Default-read: no
Applies-to: claim-scoped quantitative authority in every active accepted-prose finalization route
Does-not-authorize: new facts, calculation, conversion, claim admission, Sufficiency changes, route changes, acquisition changes, retries, or live validation
Verified-against-runtime: 4e095c7db287ab29fbe748bdd5c24cf4f2545e15
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

The three authority kinds are:

- `direct_source_numeric`: the exact proposition and literal come from current
  FAP-authorized bounded source material;
- `admitted_quantitative_claim`: the exact proposition is current, admitted,
  and applicable-D-prime-supported; and
- `specialist_derived_numeric`: the exact result comes from a completed S1
  result with `exact_match` claim alignment, applicable component or synthesis
  D-prime consumption, admission, and current FAP inclusion.

The manifest is not a global numeric allowlist. A value/unit match is
insufficient without the same complete assertion fingerprint and literal
signature. An authorized value cannot be reused for another subject, metric,
calculation result, conversion, estimate, comparison, ratio, rate, percentage,
or proposition.

Retained references are limited to bounded identifier, digest, status,
posture, route, and version shapes. Claim prose is used transiently to build
the fingerprint and the Author instruction, then omitted from the manifest.
The Author payload trace carries only a shallow digest-and-count envelope, not
the full manifest or claim text.

## Before And After Author

Before ordinary Author execution, FAP adds fixed authority instructions and
transient exact quantitative renderings. Author may explain and present those
propositions while preserving value, unit, sign, scale, percent convention,
and precision. Comma digit grouping is the only installed numeric surface
equivalence. Author may not calculate, convert, estimate, interpolate, round,
rescale, aggregate, or introduce a new numeric conclusion.

After candidate prose exists, the shared deterministic validator:

1. removes URL syntax, machine citations, support-reference sections, and
   transport identifiers from the inspected prose surface;
2. extracts bounded digit and common-cardinal candidates;
3. preserves value, unit, sign, scale, notation, percent convention, and
   declared precision in each literal signature;
4. fingerprints the complete assertion rather than the value alone; and
5. accepts only an exact manifest binding or fails closed.

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
- component-origin S1 and synthesis-origin two-hop S1 positive paths;
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

This offline repair does not prove which upstream role originated a rejected
number, broad live correctness, arbitrary-query coverage, unrestricted
natural-language number understanding, citation correctness, answer quality,
or production stability. It does not change query qualification, component
selection, S1 invocation policy, acquisition, provider/model behavior,
ranking, Specialist operators, conversion support, or Sufficiency policy.
