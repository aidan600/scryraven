# AID-12 opening Research request

**Decision. Defer the shortcut prototype.** Removing the whole opening model
request projects a 34.6% saving in the closest timed lookup. The two retained
model requests alone exceed half that turn's elapsed time. The available traces
do not establish enough headroom to offset scope and source risks. The
[early-stop counterfactuals](README.md#counterfactual-early-stops) remain negative
evidence. This follow-up adds an offline feasibility analysis and a measurement
design. It contains no new executable route and made zero live calls.

The product inputs are pinned to `8ecf38816a0aea2f146c5af0b600e28decc2a66f`.
This analysis started from the reviewed AID-12 head
`3106f22ef4a6548e14d77cbb341b4d1a5a4adc80`.

## What deleting one request buys

On an eligible fresh lookup, an opt-in experiment could supply the first
acquisition request from a small, predeclared public-authority registry and
start Terra with the acquired original material. Terra would still interpret
the whole question and choose the evidence or request further research. Sol
would still own the final judgment and use ordinary citation validation. This
would omit the serial request that currently chooses the first Search. The
registry would contain a query or a known official source and version, with
no expected answer or prewritten evidence judgment.

For a baseline elapsed time `B`, opening model time `O`, old first
acquisition `S`, and replacement acquisition `S_new`, the deletion-only
projection for a successful route is `B - O - S + S_new`. This grants free
routing and keeps the downstream calls and their measured durations fixed.
Any added verification, continuation, or routing costs increase that
projection. The half-time threshold allows combined added cost of at most
`O + S - B/2`, including replacement acquisition.

| Historical path | Baseline | Opening | First Search | Delete opening, retain Search | Delete opening and make first Search free | Half-time threshold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Terra/medium BIPM canary, Lite | 12.547 s | 4.344 s | 0.812 s | 8.203 s | 7.391 s | 6.274 s |
| S8 BIPM, Lite | 9.484 s | 2.218 s | 0.703 s | 7.266 s | 6.563 s | 4.742 s |
| S8 Baltimore/Dali, Lite | 19.812 s | 2.781 s | 0.672 s | 17.031 s | 16.359 s | 9.906 s |
| S8 Passport, Lite | 20.828 s | 2.578 s | 1.391 s | 18.250 s | 16.859 s | 10.414 s |

The canary ran through the personal-plan adapter with an earlier Answer model.
Its 7.391 s is fully accounted for by the necessary post-Search Terra request
(2.688 s) and Sol Answer request (4.703 s). The canary misses the target by
1.118 s even with free acquisition. The remaining model time would need to
fall by 15.1% with free acquisition or 26.1% with the observed Search. A direct
full-source Read could improve coverage, but any positive Read time widens the
gap at fixed model durations. The later 12.344 s browser lookup has the same
request counts and no published opening split. At unchanged Search and
downstream timings its opening would need to account for at least 6.172 s.
[Canary timings](../../docs/operator/RESEARCH_DEFAULTS_CONSOLIDATION_01.md#production-verification-and-one-canary),
[browser timings](../../docs/operator/READING_ROOM_PRODUCT_UX_01.md#bounded-live-result-and-resources)

The three S8 rows use a measured Luna opening and its separately executed Lite
continuation, so their full durations are reconstructed rather than independent
starts. Their last two columns are arithmetic on those timings. Their remaining
time includes subsequent work and any overhead, so it cannot be labeled model
time alone. Baltimore/Dali and Passport are stresses for discovery and
qualification, outside the clean single-fact sample. A historical Deep BIPM
run also supplies a check against cherry-picking long retrieval: its 2.844 s
opening proxy plus 4.328 s Search leave 16.110 s of a 23.282 s turn, above
the half-time threshold despite making first retrieval free.
[S8 timings](../../docs/operator/RESEARCH_DEFAULTS_CONSOLIDATION_01.md#8-final-deeplite-comparison-a-coverage-exception-remains-visible),
[Deep timings](../../docs/operator/EXA_DEEP_BOOTSTRAP_01.md)

Across the two decomposed BIPM examples, the **illustrative median** moves
from 11.016 s to 7.735 s (29.8% lower). Their nearest-rank p95 is simply the
larger observation and moves from 12.547 s to 8.203 s. These descriptive
numbers combine different historical configurations on one subject and
optimistically assume both routes succeed. They supply no current Terra 6.1 /
Sol 6.2 Standard cohort median or p95 estimate.

## Fallback and the tail

A low-confidence registry match would take the ordinary path before any
acquisition. A speculative acquisition followed by an ordinary restart would
take approximately `B + elapsed speculation`, before any restart or
resource-contention overhead. On the 12.547 s canary, spending 0.812 s first
would raise elapsed time to 13.359 s (+6.5%). The 1.391 s Passport Lite Search
gives a historical sensitivity point of 13.938 s (+11.1%). A 5 s slow-probe
sensitivity gives 17.547 s (+39.9%). Those are counterfactuals with the ordinary
path held fixed, including an illustrative slow value, rather than observed
candidate latency. If slow fallbacks exceed all clean-route times and occur on
more than 5% of draws, the population p95 is in the fallback path. In the
registered 16-draw positive sample the nearest-rank p95 is the single slowest
result, so one slow fallback can dominate it.

Search speed does not determine completion. In S8, Passport's first Lite
Search was 5.281 s faster than Deep while the full turn was 3.062 s slower.
Time outside the first Search increased by 8.343 s, with two extra provider
requests and an extra model request required to recover the manufacturer
source. Baltimore/Dali's authoritative Deep highlight ended inside a causal
qualification. The supported source reference survived and the final answer
omitted that qualification. Together with the hidden retroactive correction
in the prior AID-12 replay, these cases make a primary-looking result alone
insufficient evidence for an early route success.
[S8 coverage and route evidence](../../docs/operator/RESEARCH_DEFAULTS_CONSOLIDATION_01.md#8-final-deeplite-comparison-a-coverage-exception-remains-visible)

If a later timing screen earns a prototype, the following cases define its
minimum offline comparison on the ordinary validation and save path.

| Case | Behavior to check |
| --- | --- |
| Exact registered lookup with complete original | One Terra interpretation and one Sol Answer may suffice. Cite the actual acquired passage and reopen its saved text and provenance through the ordinary validator. |
| Misleading official highlight or invisible later qualification | Compare a truncated or apparently complete highlight with the full original and its version or correction trail. The candidate must surface the necessary qualification or fall back for research. Compare against the ordinary route and independently adjudicate support. |
| Unknown or ambiguous identity, changed version, conflicting sources, multipart or unsupported claim | A registry miss avoids speculative dispatch. A concern discovered after acquisition returns investigation to the ordinary Research owner, with the original question and remaining budgets. Evidence discovery and qualification stay semantic decisions. |
| Slow, failed or incomplete acquisition | Account for all elapsed time before fallback, including failed or overlapping provider legs. Exercise a late return after the fallback decision and verify a single final result and no budget renewal. |
| Experiment disabled | The ordinary request sequence, provider choices, evidence IDs and citation validation match control. |

Use frozen originals and deliberate bad replies to verify the boundary.
Scripted success or fallback does not show that a model will spot hidden
conflict. A live claim requires review of the full relevant original and the
exact passage shown to both roles, not just the saved citation's syntax.

## Narrow measurement design

1. **Direction only, if model access is separately authorized.** Use a small
   fixed set of public questions with independently frozen acquisitions and
   answer rubrics. Pair ordinary opening plus continuation against no opening
   plus the same saved original, keeping GPT-6.1 Terra/medium and GPT-6.2
   Sol/medium. Classify the baseline opening's intent before injecting
   retrieval. If it calls for materially different evidence, report that
   difference as a route failure to match, not as an identical-packet result.
   Alternate arm order. Measure physical model request durations and any
   extra requests, judge citations and qualifications blind, and keep frozen
   acquisition time outside the clock. Such a comparison can inform direction
   and downstream behavior. It cannot establish end-to-end elapsed time.
2. **First decision-quality live step.** If true Standard API use is separately
   authorized, run the four existing D01–D04 control submissions through the
   ordinary Reading Room with the fixed Terra/medium and Sol/medium roles,
   both explicitly requesting Standard. Verify actual dispatch and returned
   model and tier. Use the existing logs and observed submit-to-render timer.
   For each draw retain the post-acquisition Research and Answer timings and
   compute the median floor with all acquisition free. Then price a
   credible first-acquisition strategy starting with the observed Lite
   requests, including durations and failures. Use contemporaneous direct
   Read timings if a known-source variant is proposed. A longer Search
   selected solely to enlarge the baseline would invalidate the comparison.
   Advance only if the same-cohort median has room to reach half the
   baseline after preserving evidence checks and accounting for realistic
   acquisition and fallback. Four draws screen headroom. Their tail is
   descriptive.
3. **Paired live claims, if the screen earns them.** Use the existing frozen
   P and N sets with balanced arm order, fresh sessions, matched local
   browser/account/provider conditions, and ordinary unmocked retrieval.
   Trace dispatch, version checks, fallback and continuation time under the
   submit-to-finished-cited-answer clock. Count fallback draws in the
   attempted cohort and report median, p95, completion, correctness,
   citation support and cost by arm. Use the established
   [telemetry methodology](README.md#live-measurement-and-cost). With fixed
   frozen retrieval one can measure model-path time only.

The interactive Blinky catalog confirmation establishes that Terra and Sol
are selectable there. The broker could not see that login. The separate
AID-10 user-run transport smoke contributes zero AID-12 observations. The
personal-plan adapter omits the API service-tier override, so a plan receipt
returning `default` alone supplies no Standard API validation.

The next decision is whether to authorize the four-draw fixed-configuration
control screen. It would show whether current request timings leave room to
remove one opening request without weakening research. If that floor remains
above half, the next best option within the fixed model path is to consider a
smaller, explicitly scoped lookup target only if the measured gain justifies
the acquisition and fallback trade-offs. To keep the 50% target, a separate
investigation would need to find how to shorten the retained serial requests
while preserving semantic review. Faster Search alone cannot close the
measured canary gap.
