# Ordinary Research / Evidence-first Answer architecture

The ordinary application promotes the accepted clean-room Level-1–5 lineage.
This replaces Research -> Analyst -> Author. There is no production selector,
alternate engine or fallback. `CURRENT.md` distinguishes implementation from
bounded demonstrations and remaining limitations.

## Two semantic contracts

`scryraven.research` has two semantic model contracts. The ordinary recommended
profile uses GPT-6 Luna / high / Fast for Research and GPT-6 Sol / medium / Fast
for Answer. These are reversible `ModelConfig.research` and `ModelConfig.answer`
defaults, not architectural requirements or a model router. Compatible injected
configurations may vary in quality and validation coverage. A bounded latency
comparison kept high after medium missed a controlling Passport identity lead.
The earlier ordinary-route Standard/Fast comparison did not isolate a Fast speed
benefit; a later isolated fixed-packet screen showed a consistent latency benefit
for Sol / medium / Fast and noisier evidence for Luna / high / Fast. Fast may cost
more per token, and there is no runtime cost estimator. Model choices are not
read from environment variables; `.env.example` contains credential placeholders.
No Sol interpretation/decomposition pass precedes Research. Such a pass may be
compared in a separate bounded experiment only if Level-8 or later dogfooding
shows repeated, exact cases of materially recoverable requests with sufficient
conversation context and working acquisition, yet Luna/high misidentifies the
task, loses a user correction, or decomposes the wrong problem. The exact cases
must be preserved. The comparison would test direct Luna Research against one
Sol interpretation/decomposition pass followed by Luna Research; it is not a
production route to prebuild. No tested current case has earned that experiment.

Exa supplies ordinary general Search. Research may select lexical/community/current
discovery through Serper when the needed source class calls for it. LinkUp static
Fetch supplies ordinary external known-URL Read. There is no automatic search
fallback, Read fallback, provider router, model router,
premium escalation, Scout, specialist hierarchy, verifier, or prose polisher.

**Research** owns interpretation of the current user turn, non-evidentiary
conversation context, explicit user task premises and supplied actual Evidence,
a compact revisable understanding, route selection, and a proposal to answer.
Its understanding contains the current interpretation, a small set of scoped
findings with material references, neutral unresolved questions, and the last
route's result. This generated state is
continuity, never Evidence. It is replaced as a whole and is not stored as a
claim database or hypothesis lifecycle.

Research returns either a route of Search/lexical Search/Read/Find requests or a proposal for a
fresh answer with exact material references. The reference list may be empty when
the operation is fully derivable from explicit user premises and needs no external
factual support. User premises may inform task interpretation but do not become
Evidence-backed `established` findings. Its current compact understanding
shape is `interpretation`, bounded `established` findings with exact Evidence
references, `still_needed`, and `last_route_result`; it does not declare an
inference class or requested-versus-narrowed answer scope. The prompt
guides roughly one to three independent requests per route. Results return to the
same Research owner before semantically dependent follow-on requests are chosen.
The executor performs selected requests and reports mechanical outcomes; it makes
no truth, applicability, contradiction, sufficiency, or research-policy decisions.
`ResearchDecision` has no `purpose` field or route-purpose prose requirement.
Executable route intent is expressed by structured Search/Read/Find requests and
the compact working understanding, without a new semantic owner or memory.

**Answer** receives the immutable current user turn, conversation context,
current date, exact selected Evidence, mechanical acquisition limitations, and
remaining budget. No `answer_cautions`, working understanding, generated factual
warnings, answer draft, or Research verdict crosses this boundary. Controlling
identity, scope, time, conflicts and qualifications travel in the actual selected
material. Conversation resolves intent, discourse, corrections and follow-up
meaning. Prior user questions may carry explicit task premises into a follow-up;
user beliefs and narration are not automatically stipulated premises. Prior
assistant answers are discourse context only and cannot silently become task
premises. A user may explicitly adopt a prior assistant value as a new scenario
premise without verifying that value externally. Answer determines what selected
Evidence or user-supplied premises justify, with supported, partial, or unable
posture.
Its composition instructions develop materially consequential relationships
without displacing other qualifications needed to understand the result. A
quantitative relationship states how its inputs determine the result; a comparison
keeps the meaning and observed or modeled character of each supplied quantity
visible. A partial answer explains what missing inputs would resolve and what
incompatibilities would remain. These are instructions to the existing Answer
owner, not a required outline, additional field, semantic actor or validation gate.
Simple lookups stay direct and compact.
One consequential missing information need from a validated Answer may return to
Research within the same run allowance. Only that need returns; the provisional
answer is not supplied as Research authority. Materially changed selected Evidence
starts a fresh Answer-stage allowance; unchanged selection retains no-progress
protection.

Within the same semantic call, `AnswerDecision` declares `support_basis` as
`evidence`, `user_premises`, or `none` and places `source_readings` before the
answer. An evidence-based answer makes a small selection of literal passages
with exact material references. These are Answer's own reading selections from
the supplied sources, including material scope, identity, chronology, conditions
and exceptions. They are not Research's findings or a claim-to-source
justification. Selection supports the consequential relationships and qualifications
needed for the complete synthesis, beyond support for a headline alone.
The selections are transient and do not create a claim database,
a source-count rule, or a new actor.

Mechanical checks require each reading reference to belong to the supplied
packet and each passage to occur in that exact material. Only whitespace
differences are tolerated; the recorded reading reconstructs the original
substring and offsets without changing words or punctuation. A malformed or
nonmatching reading may get one output correction under the same Answer contract,
deadline and semantic allowance. Every invalid Answer category shares that single
correction for an unchanged selected packet. The packet's total Answer-stage
allowance is 120 seconds, and each real OpenAI call is timed within the remaining
stage, whole-run and per-call limits. An invalid corrected Answer or exhausted
stage allowance terminates with a fixed operational inability message, no rejected
prose, citations or selected supporting Evidence, and no Research reentry on that
packet. The safe trace records `answer_validation_exhausted`; durable sessions keep
their existing result shape. A source-bearing Answer that omits required
citation aliases receives a fixed correction under that same allowance before
acceptance; rejected prose is not fed back. Supported and partial `evidence`
answers also require at least one validated reading, with a reading from selected
material in every canonical source group they cite. A targeted view counts for
its canonical source group. Additional readings from uncited selected sources
are allowed. Missing required readings receive fixed corrections under the
existing Answer allowance; exhaustion retains the operational inability fallback.
Evidence `unable` answers are exempt. For `user_premises`, the Evidence
packet and `source_readings` must both be empty, and a supported or partial answer
may derive solely from explicit user premises without a citation. This does not
verify those premises externally or permit model memory to fill an omitted fact.
An answer that mixes user premises with external factual support uses `evidence`
and cites external claims. The `none` basis has unable posture and no supported
conclusion. Mechanical checks prove literal membership or basis shape, not
sufficient scope or semantic entailment. Final citation resolution and rendering
follow the accepted Answer; there is no subsequent verifier or prose-polishing
model.

The same Answer semantic owner may call a bounded deterministic local arithmetic
calculator while preparing an `AnswerDecision`. It may use numeric values from
selected Evidence, explicit user premises, and prior results from that Answer
attempt. A tool result returns to that Answer role; dependent calls can follow.
The local parser accepts bounded arithmetic expressions only. It computes exact
rational values from decimal literals, returning terminating decimals or
parenthesized exact ratios that can be reused in later expressions.
The calculator interprets neither sources nor provenance and creates no Evidence
item or alias. Results are derived computation. Externally factual quantitative
claims still cite the selected material establishing their inputs, and arithmetic
cannot supply an absent contingent external premise. Research has no calculator
tool. A calculator stop and its model continuation remain inside one Answer
semantic attempt, without using the one validation correction. Each underlying
Responses request still obeys its timeout and the remaining Answer-stage and
whole-run deadlines. Reported per-request usage is aggregated for that semantic
attempt; a missing continuation counter leaves a marked partial aggregate.

## Acquisition, custody, and reversible attention

`scryraven.acquisition.AcquisitionLibrary` retains immutable actual
`Evidence` and supplies an inspectable catalog. Ordinary Search admits source-derived Exa
highlights mechanically. Serper lexical search supplies navigation candidates only:
its snippets never become Evidence. Research can Read an observed candidate URL
through LinkUp to acquire actual source material. Navigation-only metadata is not
admitted as source text.
External Read retains LinkUp's readable source representation as fetched Evidence;
local Read reuses actual retained material or constructs an exact view. A historical
targeted-view ID can be rebuilt from its retained full parent without provider I/O;
the view itself need not persist globally. Direct IDs follow the existing bounded
targeted-view size; longer spans use an explicit parent range that splits into
bounded views. Find locates lexical matches in retained
material, including highlights, without provider I/O. Unscoped Find ranks regions
from actual retained acquisitions on one corpus-wide lexical scale; scoped Find
keeps its source-specific inspection behavior. Ranking is navigation, not a
judgment of relevance or support.
A failed search or local match says nothing about factual nonexistence.

Acquisition retains fixed safe `exa_configuration_missing`,
`serper_configuration_missing`, `linkup_configuration_missing`, and
`linkup_material_unavailable` failures. Unknown Search and Read exceptions retain
generic safe failure codes. A single provider failure does not force a turn-wide
fail-fast decision; Research judges the acquisition result.

Read's target and mode have explicit mechanical meaning:

| Request | Behavior |
| --- | --- |
| Exact material ID with `auto` | Reread that retained item locally, including highlights. |
| `local` | Inspect available retained material without external acquisition. |
| `full` | Reuse the latest retained full parent for the source or acquire full text if absent. Large parents yield bounded exact views, so one Read need not expose the whole body. |
| Candidate ID or observed URL with `auto` | Reuse an available full parent or acquire source text. |
| `refresh` | Attempt another full-text acquisition while preserving earlier versions. |

An exact targeted-view ID preserves that view when reread, including when a focus
is supplied; focus does not silently replace an addressed view with a different
parent packet. A different range, parent Read, or Find requests other material.
Explicit character ranges identify exact slices of retained full text. Large
parents can provide focused exact views using the existing disposable
`SourceIndex`; repeated inspection is allowed. A refresh returning identical
material may reuse its immutable record. Different received versions preserve
their own material IDs and share the source identity allocated to the same URL.
Find merges overlapping hit regions only within the same immutable parent,
preserving all matched text while reducing duplicate reading context.
Read returns a mechanical receipt for the material actually returned: parent
length, exact ranges, returned characters and whether the entire parent body was
in that packet. Focused large-parent Reads also distinguish lexical hits from
dispersed fallback after a lexical miss. The receipt does not establish what
Research understood or whether the source contains an answer. Research can use
Find, another focus or an exact range to inspect more of a large parent.
Target URLs must be supplied by the user, returned through acquisition, or found
as explicit links in exposed material. These mechanics validate addressability
and custody, not semantic relevance.

Three distinctions remain separate:

- Acquired: exact actual material exists in retained custody.
- Exposed: exact material was supplied to a particular model call.
- Assessed: the model accounted for what it means; this is a semantic judgment,
  not something the exposure receipt proves.

Each reading packet prioritizes newly requested material. Research can keep
controlling premises and live contradictions in attention, shelve finished
material, and reactivate retained items through local Read/Find. If requested
material remains undelivered, the loop delivers it before accepting another
external route or an answer proposal. Shelving never deletes acquired Evidence.
Catalogs and indexes are transient navigation, not persisted product truth.

## Completion and resource limits

Stopping belongs to Research's task and evidence judgment: answer at a useful honest
scope when no consequential unresolved need justifies further obtainable material
at its expected cost. The Answer contract independently determines the supported
scope from selected Evidence or explicit user premises. Neither source counts nor
budget consumption establishes sufficiency.

Bounded Level-7 evaluation demonstrated useful aggregate and open-world synthesis
when suitable heterogeneous Evidence reached Answer. It showed restraint against
promoting small self-selected samples into population claims and appropriate use
of representative survey evidence. General open-world reliability remains unproved,
and source-access failures can prevent a fair semantic test. Lexical/community
discovery can identify a relevant URL that ordinary supported Read cannot
materialize; navigation does not become Evidence merely because the source is
relevant. The rejected scope-contract experiment remains historical evidence,
not active design.

Behavior-first Level-8 evaluation demonstrated bounded dynamic multi-component
research across seven completed families, including selective revision and
multi-turn scenario-premise handling. It did not establish arbitrary-length
continuity or general reliability.

`RunLimits` ordinarily allows 12 semantic attempts, 16 external acquisition attempts,
a 300-second hard run ceiling, and 128,000 characters of current Evidence attention.
After Evidence exists, the loop reserves 180 seconds for terminal Answer; each model
call remains capped at 120 seconds. The longer run ceiling is diagnostic and
completion headroom, not an acceptable product-latency target. Local inspection
uses no external allowance, while malformed
or corrected model attempts consume the same semantic allowance. Transport
timeouts use the remaining run deadline. The loop reserves an answer attempt
where time and allowance permit; if no supported answer can be completed,
it returns an explicit operational unable result rather than synthesizing from
generated notes. A limit is not evidence of support or nonexistence.

When Research reaches its operating bound, presentation discloses that fact even
if the independent Answer supports its conclusion. The bound does not mechanically
change Answer posture.
Safe run traces include monotonic elapsed time, body-free conversation and
retained-library size counts at turn start, Research catalog and active Evidence
character counts at model start, and model return and failure events. Incomplete
provider responses retain only fixed `content_filter` and
`max_output_tokens` classifications; missing, malformed or unknown reasons remain
generic. No raw provider reason or response payload enters the trace.

## Result, session, and presentation boundaries

`scryraven.results.CompletedAnswer` contains the public answer, posture, stop
reason, retained acquisitions, selected exact material, citations, citation-use
spans, and safe run trace. It has no Analyst-shaped interpretation object.
Citation mechanics validate selected material against immutable acquisitions or
exact parent slices, reject unknown/unselected aliases and unresolved answer
links, and assign compact source numbers. Historical citation snapshots contain
the exact selected material, including versions and views. Identity validation is
not semantic entailment checking.

`ResearchSession` receives this native result from the ordinary Research loop.
Every `ask` starts fresh Research understanding and attention over the retained
acquisition library. Research receives the full prior question and answer text
plus citation provenance derived from immutable saved turns. The provenance
identifies the exact source and material each earlier answer cited, including
targeted views, without claiming that the earlier answer was correct. On the
first Research call of a follow-up, the exact actual material cited by the
immediately preceding completed answer is also exposed when it fits the existing
attention limit. A targeted view is reconstructed from its retained full parent;
no new acquisition or persistent memory is created. No other historical material
is automatically exposed. Research may use, shelve or supplement this Evidence.
Answer continues to receive ordinary conversation without historical provenance
aliases and sees only Evidence freshly selected for the current answer. Prior user
questions may supply explicit premises as task context; prior assistant answers
are never Evidence. Only successful completed results commit session state;
failures leave the previous in-memory and durable snapshot unchanged. A partial
or unable completed answer can be retained honestly.

Durable `SessionTurn` records allow `analysis=None` for a source-first answer;
legacy Analyst-bearing turns retain their actual saved Analysis. No fake
Analysis is manufactured. The existing SQLite schema and atomic revision-checked
commit boundary remain, with neutral-turn validation alongside legacy validation.
Run traces, working understanding, indexes, observer records and provider state
are not session persistence fields. Reopening preserves actual Evidence and
historical answer provenance without making past generated text evidentiary.
All prior questions and answers are replayed verbatim for every Research call and
for Answer. Long-session performance remains unproved. There is no
context-compaction lifecycle in the ordinary product.

Ordinary `run`, `ResearchSession.ask`, the CLI (isolated, ephemeral and durable),
and Reading Room all invoke this same loop. There is no `--v2` selector.
Shared terminal/HTML presentation consumes `CompletedAnswer` and saved
`SessionTurn` directly, with no manufactured Analyst result. The only historical
Analysis code is decode-only schema/reference validation in `scryraven.historical`.
Historical judgments are excluded from new model packets. The stopped Investigator
executable harness and its Author adapter are retired to their preserved Git lineage.

The Reading Room and CLI disclose that no external sources were used for
completed source-free supported/partial answers. Presentation derives this from
posture and empty citations, which do not establish a user-premise basis; it
adds no persisted premise state.

The model transport keeps exact JSON content and explicit prompt-cache boundaries
for instructions, growing conversation history and stable Research turn context.
Research and Answer have separate cache families; mutable Evidence and corrections
remain outside those stable boundaries. Transport, Exa policy and the credential
broker remain mechanical infrastructure, with no semantic decision authority.

For Research, the stable packet prefix remains `conversation_context`,
`current_date`, `phase`, `question`, followed by the existing Research-context
cache breakpoint. Present volatile fields serialize in this deliberate order:
`working_understanding`, `catalog`, `last_route`, `evidence`,
`answer_missing_information`, `pending_delivery`, `budget`, and
`output_correction` last. Any other material fields survive unchanged in
deterministic order before a present correction. Placing previous generated
understanding and navigation before the latest route and Evidence presents
current source material near the decision edge. Both Research and Answer place
known identifying metadata, then deterministic unknown metadata, before exact
`content` inside each Evidence item. The parsed object, exact text, IDs,
Evidence membership and array ordering remain unchanged. Answer's top-level
packet order and cache boundaries remain unchanged. This is presentation order,
not an attention, retention, acquisition or Answer-policy change. No quality or
latency benefit has been established. Removing
`purpose` changes the Research schema and can change its cache-family identity;
no compatibility family or persistent generated state is added. The growing
conversation boundary, stable Research-context breakpoint and separate Answer
family remain intact.

## Safe development observations

An optional observer receives normalized public events: bounded structured
decisions, field-specific rejected-decision diagnostics, selected requests and
acquisition outcomes, budget facts, exact acquired/exposed public material,
verified literal answer-reading selections, and exposure IDs, lengths and hashes. It never
receives raw provider responses or hidden reasoning. The small returned trace
excludes source bodies; exact bodies can be captured separately through the
observer when an authorized development observation needs them. A rejected
literal passage also generates an observer-only `source_body=True` event with
its attempted text, reading coordinates, and selected Evidence content hash and
length. The ordinary trace, body-free dogfood diagnostics, durable sessions and
public presentation do not receive that rejected text. Successful readings do
not generate rejected-reading detail events. The literal matcher is unchanged.

Reading Room's optional `--forensic-log PATH` writes the ordinary observer stream
to a distinct local JSONL file for development review. Its source-bearing events
can reconstruct acquired/exposed material, Research selections, Answer readings,
rejections, timing and available model telemetry. Each line includes the session,
attempted turn, process run and event sequence. It receives no raw provider
payloads or hidden reasoning, and it feeds nothing back into the engine, session
or presentation. The ordinary DogfoodLog remains body-free. Startup rejects
aliases between both logs and the session database; later forensic write failure
disables only that observer sink.

`scripts/v2_campaign.py` remains a development-only observation caller (its name
identifies historical campaign files). It calls the ordinary session application
with explicit Luna/medium configuration and no engine override. It supplies only the frozen selected
question, never the rubric, expected identities, known URLs or a scripted route.
JSON lines go through the existing doorman's sanitized output boundary. The
doorman handles credentials and process plumbing only. Useful exact public
failures and controls may be captured as development candidates in ignored
`local-evals/` under `docs/operator/LOCAL_EVALUATION_CORPUS.md`; the runtime does
not depend on that corpus.
