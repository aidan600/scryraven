# AID-10 Luna reliability protocol

Baseline revision `8ecf38816a0aea2f146c5af0b600e28decc2a66f` is the branch
fork and was also the remote `main` tip when inspected. Control uses that
revision's ordinary Research and Answer prompts and execution path, with the
role configuration below. Keep the two model configurations fixed within
their respective comparisons.

## Frozen workload

Freeze recorded before candidate changes. The private-to-checkout case
manifest is `local-evals/runs/aid-10-freeze/cases.json`, SHA-256
`2d19f8b89fa1c23aedda269bbba53644bd2066eea807afeafa1c241487d5a470`.
It lists ten development questions (two per category) and 40 reserved
questions (eight per category). The five categories are citation fidelity,
material coverage, ambiguous/insufficient evidence boundaries,
lookalike discrimination, and factual or premise-based application.
The manifest contains the original questions, primary-source targets or
explicit premise basis, and material obligations. Only the question is sent
to either model. The ten reserved diagnostic/repeat IDs are H01, H02, H09,
H10, H17, H18, H25, H26, H33 and H34, fixed by taking the first two IDs
in every category.

This deliberately balanced workload represents baseline obligations from
the product charter. It is a designed sample without measured production
traffic weights. Exact historical evaluation packets were unavailable in
this checkout. The public-source targets and question-specific obligations
are frozen but still require independent preflight verification and
operator agreement before any reserved run. The reviewer should record
the exact primary passages/links and qualification checks in the ignored
corpus before looking at model outputs. Flag a genuinely broken case before
dispatch. Any revised workload must preserve the original, document the
reason and receive a new digest before it is used. Keep reserved cases out
of intervention design, tuning and repair. A touched reserved case becomes
development and a replacement held-out set requires a new freeze. Store
case files and run artifacts under the ignored corpus per
[Local Evaluation Corpus](LOCAL_EVALUATION_CORPUS.md).

## Run order

1. Compare control and hardened harness on the ten development cases
   with exact GPT-6 Luna / high Research and fixed exact GPT-6.2 Sol /
   medium Answer. Inspect the traces before proceeding. A small initial
   configuration check comes out of this block. Stop for incompatible
   model identity, tier or provider parameters.
2. With the candidate frozen, use the same mixed roles on the ten reserved
   diagnostic cases. Both arms retain the ordinary Answer prompt. Report this
   as a Research diagnostic and record instances where Sol recovered a
   deficient Luna handoff.
3. Compare both arms on all 40 reserved cases with exact GPT-6 Luna / high
   Research and exact GPT-6 Luna / medium Answer. The hardened arm also
   receives the Luna Answer guidance. This paired test measures the combined
   intervention. Use step 2 and exposure traces to assess failure ownership.
4. Repeat both Luna-only arms once for the ten prespecified reserved
   cases. Report repeats and within-case disagreement separately.

Use OpenAI API Standard (`service_tier=default`) in both roles, with ordinary
shared limits, providers, schemas and tools held fixed. Interleave the two
arms per question in alternating order and keep each pair close in time.
Use a fresh research session per turn. Record model identity, requested
effort, returned tier, revision, prompt hashes, corpus hash, clock window and
physical dispatch counts. Require the returned identity and Standard tier
on each successful Responses request. A missing or mismatched receipt
makes that turn ineligible. Record failed dispatches separately. There is
no model fallback. A whole-turn timeout remains in its original slot.
Resume only at a complete, undispatched pair. An interrupted pair stays in
the denominator and its missing slot is recorded as a failed execution
rather than replaced with a fresh draw.

## Review and reporting

Have two independent reviewers score shuffled outputs without arm, model,
timing or trace labels. Provide the question, frozen obligations, answer,
posture and exact resolved evidence. Adjudicate disagreement with a third
blinded reviewer before revealing the mapping. Preserve the original
verdicts, disagreement rate and adjudicated verdicts. After judging the
answers, inspect unblinded traces to attribute failures.

A pass requires a fully useful supported answer at the scope of the original
question, with no material omission or error. Central external factual
claims need adjacent citations resolving to the actual acquired text, and
that text must warrant the claim at the right authority, entity, version,
units, time and conditions. Compare the answer and citation text with the
frozen primary-source checks as needed. On a boundary case, a fully
supported explanation of what the source establishes and what requires
more evidence can pass. An actual partial or unable product posture,
timeout, unverified model/tier, unsupported central claim, decisive
omission, or stronger-model escalation fails the Luna-only endpoint.
Keep credit for honest limits and for mixed-role recoveries as secondary
annotations. Minor wording or optional detail does not change a verdict.

Record multiple defect flags where relevant (unsupported central claim,
misapplied or missing citation, omission, lookalike, unwarranted certainty,
and incorrect inference/calculation). For causal diagnosis, assign the
earliest attributable failure with an evidence reference. Use provider
access/availability if the needed original could not be materialized;
Research acquisition if a credible route went uninvestigated; Research
interpretation or handoff if acquired evidence contradicts the briefing or
decisive support was dropped before delivery; Answer synthesis or citation
if the necessary material reached Answer; and transport/runtime for actual
execution or contract failures. Use unknown when exposure or run
provenance is insufficient. Where Answer rescues Research with its own
inspection or re-entry, preserve the original defect and the recovery path.
A mixed-role rescue supplies no Luna-only credit.

Use all 40 scheduled first draws per Luna-only arm as the primary
denominator after launch. Publish accepted/attempted and a 95% Wilson
interval per arm, paired improved/regressed counts, and corresponding
per-category denominators and failure counts. Report development,
mixed-role, repeat and synthetic results separately. A 36/40 primary score
reaches the 90% sample target. The interval and paired comparison govern
how much can be inferred. Flag any category with a lower acceptance
count and any baseline-only material success; assess repeat evidence and
diagnosis before judging material regression. Broad claims about a 90%
population rate need stronger evidence than a point estimate.

## Billed run envelope

No paid run is authorized by this document. Use the existing local
credential broker and run only after approval of the exact command,
configuration and spend. The staged design schedules 20 development and
20 reserved mixed-role turns, then 80 primary and 20 repeat Luna-only
turns. Start with two development pairs to verify receipts and estimate
usage before authorizing the remainder. Stop between stages for missing
provider access or if the approved estimate no longer covers the remainder.

Use the safe per-physical-request ledger for input, cached input, output,
role, model and tier. Multiply uncached and cached input and all output
(including reported reasoning tokens within output) by the applicable
Standard rates. Keep cache-write billing separate if the provider charges
for it. Treat missing counters as unknown. Add charged acquisition attempts
by provider and endpoint, using the account's current pricing (including
Exa search mode and returned contents, LinkUp Search/Fetch, and any
other charged dispatch). Account for failures and retries. For a spend
estimate use stage- and role-specific pilot usage, the scheduled turn counts,
and a conservative allowance for high-use turns and failed requests.
Current pricing and exact account access must be verified by the operator.
Request ceilings are context for the bound and do not determine a dollar cap.
