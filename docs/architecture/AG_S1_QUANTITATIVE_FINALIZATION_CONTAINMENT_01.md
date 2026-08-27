# Quantitative FAP Authority And Evaluator Containment

Status: current
Authority: canonical:quantitative-finalization-containment
Default-read: no
Applies-to: structured pre-Author quantitative authority in FinalAnswerPacket (FAP), retained evaluator diagnostics, and the ordinary/compatibility finalization consumer census
Does-not-authorize: new facts, calculation, conversion, claim admission, Sufficiency changes, route changes, acquisition changes, retries, semantic repair, or live validation
Verified-against-runtime: 969e3085922d10985d406bac1d620d459e2731c6
Update-trigger: merged change to quantitative FAP projection, Author numeric instructions, post-Author mechanics, evaluator disposition, or a guarded finalization consumer

## Responsibility

This document owns the quantitative boundary after the explicit architecture
decision:

```text
FAP    = final semantic-authority boundary
Author = final semantic actor
post-Author PRODUCT = mechanics only
```

It preserves hard quantitative authority before Author without creating a new
semantic voter. FAP structurally verifies authority already produced by current
Component Analyst, applicable Specialist/result, RunKernel admission,
ComponentCoverage, Sufficiency, source, and citation owners. It does not decide
what a claim means, create a claim, revise Sufficiency, or add a second
semantic-support decision.

FAP is the final semantic-authority boundary. Author is the final semantic
actor.

The former shared natural-language quantitative validator is retained as an
evaluator. Its diagnostic is evidence about candidate prose, not authority over
FAP, Author authorization, Author output, citation authority, canonical state,
RunOutcome, product success/failure, or retry behavior.

## Structured Quantitative Authority

`quantitative_finalization_authority_manifest_v2` is transient FAP-side
authority material. Its durable safe shape is:

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
  applicable_validator_ref
  applicable_validator_consumption_ref
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

- `direct_source_numeric`: retained only as an evaluator/diagnostic claim
  shape. Ordinary PRODUCT no longer creates or requires these rows for
  admitted direct-source claims merely because the claim text contains digits.
  Direct-source semantic support is Analyst explanation plus RunKernel
  admission. FAP packages the admitted claim, evidence context, and citations,
  and verifies mechanical provenance only; and
- `specialist_derived_numeric`: the current FAP-selected claim has a completed
  installed S1 result, exact claim-material alignment, canonical result unit and
  precision, exact result/handoff lineage, and applicable Component Analyst or
  synthesis validation consumption.

Generic admission is not an authority kind. FAP does not rediscover required
numeric occurrences from admitted prose, classify incidental digits, decide
whether a token is a unit or version, or judge whether one sentence
semantically supports another. A bad Analyst semantic judgment is not rescued
by reparsing its prose. Derived/calculated quantitative results remain
separately protected by exact Specialist authority.

Admitted direct-source numbers are ordinary claim content for Author to
restate. They are not a separate FAP numeric-authorization row.

## FAP Pre-Author Gate

`quantitative_fap_authority_preflight_v1` operates only on FAP-selected
structured state. For admitted direct-source claims it checks mechanical
lineage only: current/not-stale component identity, observation, Coverage,
content digest, and evidence/citation custody. It does not extract claim-text
literals, match them against bounded excerpts, or classify incidental numeric
surfaces. It still blocks using existing FAP/Author-input semantics when it
finds, for example:

- missing or incomplete Specialist authority for a declared derived/calculated
  quantitative result or admitted-synthesis numeric claim;
- an unadmitted, stale, foreign, or mismatched component/content/coverage
  identity;
- missing semantic-observation, Coverage, or evidence/citation lineage;
- malformed or impossible authority state.

A block does not rewrite a claim, create a fallback answer, alter Sufficiency,
or invoke Author. Its safe diagnostic records counts, enum reason codes, and
digest/ref-shaped facts only; it includes no final text, raw source text, prompt,
model response, provider payload, private log, or full trace.

The desired failure boundary is mechanical, not semantic interpretation of
admitted prose. Digest-verified bounded material may retain up to 2000
characters of packet-owned text. Author presentation of that material remains
independently capped at 600 characters.

The hardened `SufficiencyReadiness -> HardenedFinalAnswerPacket ->
AuthorProseFinalization` route applies the same pre-Author FAP preflight. Direct
source material uses current component, semantic-observation, content, coverage,
and evidence-custody identity; it does not require FAP to re-prove literal
signatures from prose. Installed Specialist capability/version, result and
handoff identities/digests, canonical component target, exact claim-material
binding, canonical `result_unit` and precision, and terminal consumption by the
applicable Component Analyst case remain hard for derived numeric results.
Generic D-prime admission alone remains nonauthority. The hardened packet
packages component entries only; it does not project synthesis entries and does
not install a hardened synthesis sidecar.

## Author And Post-Author Boundary

Author receives admitted direct-source claims, packet-owned evidence/citation
context, caveats, prohibited transformations, and any listed Specialist-derived
quantitative results. Author may restate numbers from those admitted
direct-source claims and bounded evidence. It must preserve authorized derived
meaning when Specialist results are listed: value, unit, sign, scale, percent
convention, material precision, subject, and proposition. It may explain or
paraphrase that material naturally.

The Author instruction does not mention parser acceptance, fingerprints,
regexes, or an exact required surface. It continues to prohibit calculation,
conversion, estimation, interpolation, unsupported rounding, rescaling,
aggregation, and a new quantitative conclusion unless listed derived Specialist
authority authorizes that exact result. It does not require Author to
reproduce a canonical sentence merely so a downstream parser recognizes it, and
it does not tell Author to emit no quantitative assertion merely because no
`direct_source_numeric` row exists.

After Author, ordinary PRODUCT code may enforce mechanics such as required text
presence, citation-token identity/placeholder resolution, private/control
material protection, serialization, envelope shape, encoding, and size bounds.
It may not reinterpret free-form prose to decide semantic acceptability. There
is no post-Author semantic model, deterministic accepted-prose theorem prover,
Author retry, revision loop, semantic repair loop, second FAP, or semantic
readmission.

## Retained Evaluator

`validate_author_output_quantitative_authority()` remains a throwing evaluator
helper for explicit validation contexts, and
`evaluate_author_output_quantitative_authority()` returns the same safe
accepted/rejected diagnostic without making it authoritative. The evaluator can
continue to report unsupported arithmetic, conversion, subject/value/unit/sign/
scale/precision drift, unsupported numeric surfaces, unauthorized propositions,
and fingerprint mismatch.

The evaluator may be wrong. No PRODUCT runtime consumer may use it as a success
or failure decision, mutate text because of it, delete a fragment, alter
citations, change canonical state, or request another model call. The older
two-item quantitative consistency diagnostic is retained for validation and
regression tooling only; ordinary PRODUCT does not invoke it inline after
Author output.

## Guarded Finalization Consumer Inventory

| Guarded consumer | Current disposition | Product effect |
| --- | --- | --- |
| Ordinary `AuthorExecutor` | Post-Author semantic hard gate retired | FAP preflight occurs before Author; Author output is not reparsed for PRODUCT acceptance or withheld solely for quantitative semantics. |
| Deterministic `AuthorProseFinalization` | Post-Author semantic hard gate retired | Structured hardened FAP preflight remains hard; deterministic generated prose is not semantically reparsed after construction. |
| Guarded follow-up response finalizer | Semantic hard-gate authority retired | Internal compatibility finalization is mechanical-only; retained evaluator calls, if any, are non-throwing diagnostic only and do not affect final text or RunOutcome. |

The guarded follow-up capability remains internal supporting machinery. It does
not establish saved-thread product consumption. `ui.pages_followup` and
`core.followup` are retired from ordinary product use and are not a current
consumer of a shared accepted-prose validator: no shared accepted-prose
validator remains as final-answer authority. Any future follow-up activation
must consume the FAP/Author boundary deliberately; it cannot restore a
post-Author semantic gate by compatibility naming.

## Proof Posture

Focused offline proofs establish:

- FAP blocks unadmitted, stale, foreign, or mismatched mechanical lineage,
  missing Coverage/observation/content/evidence custody, and incomplete
  Specialist authority before ordinary Author input;
- FAP does not block an admitted same-lineage direct-source claim by reparsing
  its numbers, units, ordinals, or incidental digits;
- genuinely derived Specialist numeric authority retains exact lineage and
  still reaches the FAP/Author path only when complete;
- the N1 Q1-shaped ordinary pipeline uses one answer-bearing READ, one Component
  Analyst, deterministic admission, Coverage, Sufficiency, FAP mechanical
  lineage, zero `direct_source_numeric` PRODUCT rows, zero
  Specialist/D-prime/Cross/synthesis/Scrutineer calls, one Author call,
  mechanically finalized citations, and a successful offline RunOutcome;
- a lawful ordinary Q1 Author paraphrase can complete even when the retained
  evaluator directly reports a rejection diagnostic;
- evaluator acceptance and rejection diagnostics do not mutate FAP state,
  Author output, citation authority, RunOutcome, or product success; and
- truly mechanical FAP/citation/output failures remain fail-closed.

The parser's adversarial surface matrix remains a validation/regression asset.
It no longer asserts that Author output is withheld because a natural-language
proposition matcher disagrees.

## Nonproofs

- This boundary does not prove arbitrary-query readiness, broad Author quality,
  citation rendering correctness, source-obligation satisfaction, or broad
  quantitative reasoning quality.
- It does not identify which upstream actor would have originated a bad Author
  proposition, nor does it make evaluator disagreement a canonical truth.
- No provider or model changed.
- No route-qualification repair was performed.
- No Specialist capability, operator, proposal policy, budget, route,
  acquisition behavior, provider/model selection, synthesis architecture, or
  follow-up product activation is changed.
- Ordinary synthesis-origin S1 authority remains owned by the ordinary
  ComponentWorkGraph / synthesis D-prime / ordinary FinalAnswerPacket path.
- Broad live correctness, answer quality, and production stability remain
  unproved.
- Live evidence, when separately recorded by the current-state owner, remains
  bounded evidence rather than a general reliability claim.
