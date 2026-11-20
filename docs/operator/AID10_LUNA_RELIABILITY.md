# AID-10 Luna harness reliability

The experiment is prepared for offline use. Live acceptance is inconclusive.
There are zero live development, diagnostic or reserved turns, zero independently
judged answers, and no measured baseline or candidate pass rate. Neither model
availability on the billed account nor provider receipt behavior has been
verified live. The candidate is a testable prompt change, with no demonstrated
quality gain yet.

[The frozen protocol](AID10_LUNA_RELIABILITY_PROTOCOL.md) identifies the base
revision, case digest, locked roles, Standard-tier envelope and acceptance
criteria. The actual manifest stays in the ignored local corpus.

## Control and candidate

Both arms use the same ordinary `ResearchSession.ask` path, production
`OpenAIModel` Responses transport, continuation tools, budgets, and citation
validation. Control uses the prompts and execution path at
`8ecf38816a0aea2f146c5af0b600e28decc2a66f`. The experimental command
only rewrites prompts within a single serial turn and restores the originals
on exit. Shipped model selection and routing are unchanged.

The candidate asks Research to link each material part to an exact original
and keep controlling conditions and unresolved parts in the handoff.
With Luna also writing Answer, the candidate adds a final coverage and
citation-scope check using the existing Read and Research tools. Sol Answer
uses the control prompt in both diagnostic arms. These additions address
the earlier observed loss of a requested qualification despite source
availability and premature return on an adjacent topic. They do not require
an extra semantic actor, a new output field, a minimum number of sources or
a fixed answer template.

Prior evidence constrains the hypotheses. `CURRENT.md` records bounded
Luna/high Research trajectories with stronger Answer, an unexercised
Elytra transition, a partial Passport trajectory at medium, and a limited
direct-Answer screen. Answer Coverage Retention preserved both sides of the
MD-80 comparison and its load-factor relationship in two promoted draws,
after an earlier repeat dropped a material distinction. The promoted
screen was Sol Answer on frozen materials. In the separate dual-Read
observation, an MD-81 units qualification still went missing with the
complete original available to Answer. These observations motivate
separate diagnosis of Research acquisition, handoff and Answer fidelity.
They supply no Luna-only denominator.

## Run and review

From the repository root, use the following broker target for two
development pairs after separate authorization.

```sh
-m scripts.aid10_luna --manifest local-evals/runs/aid-10-freeze/cases.json --phase diagnostic-development --start 0 --count 2 --authorized-standard-run
```

This is the exact Python argv after the broker separator when using
`--target-current-python`. The approval flag attests to separately granted
run and spend approval. Follow the
[broker operator flow](BROKERED_COMMAND_SESSION_OPERATOR_FLOW.md) for absolute
outside-checkout stdout/stderr/status paths. The broker provides existing
credentials. Never use a production endpoint or an alternate credential
path. The runner writes one JSON object per line, with a block header,
started/finished records per turn, then a block close. Retain sanitized
stdout in the ignored corpus. Preserve started records after interruption.
Run subsequent blocks only after the registered stage checks and
approval. The four phase names are `diagnostic-development`,
`diagnostic-reserved`, `luna-reserved`, and `luna-repeat`.

The ledger captures safe normalized per-physical-request model usage and
acquisition timings/receipts. The normalized Research decisions,
acquisition/exposure snapshots, Answer library results and continuation
handoffs let a reviewer locate the first point at which a decisive source
was missed, dropped or misused. The runner also saves the exact citation
snapshot and offsets used for scoring. Treat logs as corpus material.
Whole-turn or model-call timeout, unsupported posture, receipt mismatch
or model substitution remain failures in their original slots. A stop
for incompatible configuration prevents further dispatch in that block.

Once a phase's pairs have begun, prepare the review packet from its
sanitized block logs. Reviewers receive only the shuffled packet and the
independently verified primary-source checks. Keep the private key and run
logs with the coordinator until adjudication.

```sh
python -m scripts.aid10_luna_review blind --manifest local-evals/runs/aid-10-freeze/cases.json --phase diagnostic-development --logs <block.logs> --packet <blind.json> --key <private.json>
python -m scripts.aid10_luna_review score --key <private.json> --reviews <reviewer-one.json> <reviewer-two.json> --ownership <ownership.json> --report <report.json>
```

Each review file has a distinct `reviewer` string and a `verdicts` object
keyed by opaque `review_id`. A verdict has `acceptable` (boolean),
`defects` (empty for acceptable, otherwise one or more of
`unsupported_claim`, `citation`, `omission`, `lookalike`,
`unwarranted_certainty`, `inference_or_calculation`, `other_material`),
and a `rationale` citing the decisive material. Add a third independent,
blind review file covering exactly the disputed IDs when the first two
disagree on acceptability or defects. The optional ownership file maps
failed review IDs to `owner` and `evidence` strings. Use a supported owner
from the review module and reference the concrete run event, packet, or
citation which locates the failure. Unknown attribution remains visible.
Record Sol recoveries separately by inspecting the mixed-role handoff even
when the final mixed-role answer passed.

Report the primary and repeat phases separately, comparing the repeat
rows to the corresponding primary row by case ID and arm. The mixed-role
phase cannot contribute to the Luna-only endpoint. Use the confidence
interval and paired discordance in the context of the designed sample. A
frozen manifest with intended source targets is not an independently
verified source key until the protocol's preflight is complete.

## Verification and limits

The frozen case checksum, block sizes and pairing were verified locally.
The 263 focused offline checks covered the opt-in harness, initial and delegated
Research, native Answer continuation, requested model and reasoning, citation
custody, model/tier receipts, exclusions and blinded review bookkeeping. Test
payloads and provider responses were scripted. No model or acquisition provider
was called.

The full Linux suite reported 1,567 passed, 207 skipped and 18 failures in
`test_answer_research_transport.py` and `test_api_request_deadline.py`.
The same 18 failures reproduced against an archive of the exact branch base.
The failures were Windows vault initialization and assertions requiring exact
timeout equality after elapsed setup time. Optional browser checks skipped in
this environment. Ruff lint, scoped pre-commit checks and Git whitespace checks
passed. `CURRENT.md` remains the record of the shipped runtime.
