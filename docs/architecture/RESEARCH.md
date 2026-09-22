# Ordinary Research / Evidence-first Answer architecture

The ordinary application promotes the accepted clean-room Level-1–5 lineage.
This replaces Research -> Analyst -> Author. There is no production selector,
alternate engine or fallback. `CURRENT.md` distinguishes implementation from
bounded demonstrations and remaining limitations.

## Two semantic contracts

`scryraven.research` has two semantic model contracts: Research uses GPT-6 Luna
with high reasoning, and Answer uses GPT-6 Sol with medium reasoning. These are
fixed assignments to the existing contracts, with no model routing or escalation.
Exa supplies Search; LinkUp static Fetch supplies ordinary
external known-URL Read. There is no Read fallback, provider router, model router,
premium escalation, Scout, specialist hierarchy, verifier, or prose polisher.

**Research** owns interpretation of the original question and supplied actual
Evidence, a compact revisable understanding, route selection, and a proposal to
answer. Its understanding contains the current interpretation, a small set of
scoped findings with material references, neutral unresolved questions, and the
last route's result. This generated state is continuity, never Evidence. It is
replaced as a whole and is not stored as a claim database or hypothesis lifecycle.

Research returns either a route of Search/Read/Find requests or a proposal for a
fresh answer with exact material references. Its current compact understanding
shape is `interpretation`, bounded `established` findings with exact Evidence
references, `still_needed`, and `last_route_result`; it does not declare an
inference class or requested-versus-narrowed answer scope. The prompt
guides roughly one to three independent requests per route. Results return to the
same Research owner before semantically dependent follow-on requests are chosen.
The executor performs selected requests and reports mechanical outcomes; it makes
no truth, applicability, contradiction, sufficiency, or research-policy decisions.

**Answer** receives the immutable original question, conversation referents,
current date, exact selected Evidence, mechanical acquisition limitations, and
remaining budget. No `answer_cautions`, working understanding, generated factual
warnings, answer draft, or Research verdict crosses this boundary. Controlling
identity, scope, time, conflicts and qualifications travel in the actual selected
material. Answer independently determines what that material justifies, with
supported, partial, or unable posture.
One consequential missing information need may return to Research within the
same run allowance. Only that need returns; the provisional answer is not supplied
as Research authority. Each subsequent answer attempt is again source-first.

Within the same semantic call, `AnswerDecision` places `source_readings` before
the answer: a small selection of literal passages with exact material references.
These are Answer's own reading selections from the supplied sources, including
material scope, identity, chronology, conditions and exceptions. They are not
Research's findings or a claim-to-source justification. The selections are
transient and do not create a claim database, a source-count rule, or a new actor.

Mechanical checks require each reading reference to belong to the supplied
packet and each passage to occur in that exact material. Only whitespace
differences are tolerated; the recorded reading reconstructs the original
substring and offsets without changing words or punctuation. A malformed or
nonmatching reading gets an output correction under the same Answer contract,
deadline and semantic allowance. This proves literal membership, not sufficient
scope or semantic entailment. Citation resolution then follows the completed
answer; there is no subsequent verifier or prose-polishing model.

## Acquisition, custody, and reversible attention

`scryraven.acquisition.AcquisitionLibrary` retains immutable actual
`Evidence` and supplies an inspectable catalog. Search admits source-derived Exa
highlights mechanically; navigation-only metadata is not admitted as source text.
External Read retains LinkUp's readable source representation as fetched Evidence;
local Read reuses actual retained material or constructs an exact view. Find locates
lexical matches in retained material, including highlights, without provider I/O.
A failed search or local match says nothing about factual nonexistence.

Read's target and mode have explicit mechanical meaning:

| Request | Behavior |
| --- | --- |
| Exact material ID with `auto` | Reread that retained item locally, including highlights. |
| `local` | Inspect available retained material without external acquisition. |
| `full` | Reuse the latest retained full parent for the source or acquire full text if absent. |
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

Stopping belongs to Research's evidence-based judgment: answer at a useful honest
scope when no consequential unresolved need justifies further obtainable material
at its expected cost. The source-first Answer contract independently determines
the supported scope. Neither source counts nor budget consumption establishes
sufficiency.

The architecture has not demonstrated reliable aggregate or open-world sufficiency:
selected source themes can still be promoted beyond what the evidence warrants.
That semantic limitation is not repaired by a runtime restriction or an additional
decision-maker; the rejected scope-contract experiment remains historical evidence,
not active design.

`RunLimits` initially allows 12 semantic attempts, 16 external acquisition attempts,
120 seconds, and 128,000 characters of current Evidence attention. These are
operational settings. Local inspection uses no external allowance, while malformed
or corrected model attempts consume the same semantic allowance. Transport
timeouts use the remaining run deadline. The loop reserves an answer attempt
where time and allowance permit; if no source-grounded answer can be completed,
it returns an explicit operational unable result rather than synthesizing from
generated notes. A limit is not evidence of support or nonexistence.

## Result, session, and presentation boundaries

`scryraven.results.CompletedAnswer` contains the public answer, posture, stop
reason, retained acquisitions, selected exact material, citations, citation-use
spans, and safe run trace. It has no Analyst-shaped interpretation object.
Citation mechanics validate selected material against immutable acquisitions or
exact parent slices, reject unknown/unselected aliases and unresolved answer
links, and assign compact source numbers. Historical citation snapshots contain
the exact selected material, including versions and views. Identity validation is
not semantic entailment checking.

`ResearchSession` receives this native result from the ordinary Research loop. Every `ask` starts fresh Research understanding and attention over the
retained acquisition library. Prior questions and answers are conversation
context, never Evidence. Only successful completed results commit session state;
failures leave the previous in-memory and durable snapshot unchanged. A partial
or unable completed answer can be retained honestly.

Durable `SessionTurn` records allow `analysis=None` for a source-first answer;
legacy Analyst-bearing turns retain their actual saved Analysis. No fake
Analysis is manufactured. The existing SQLite schema and atomic revision-checked
commit boundary remain, with neutral-turn validation alongside legacy validation.
Run traces, working understanding, indexes, observer records and provider state
are not session persistence fields. Reopening preserves actual Evidence and
historical answer provenance without making past generated text evidentiary.

Ordinary `run`, `ResearchSession.ask`, the CLI (isolated, ephemeral and durable),
and Reading Room all invoke this same loop. There is no `--v2` selector.
Shared terminal/HTML presentation consumes `CompletedAnswer` and saved
`SessionTurn` directly, with no manufactured Analyst result. The only historical
Analysis code is decode-only schema/reference validation in `scryraven.historical`.
Historical judgments are excluded from new model packets. The stopped Investigator
executable harness and its Author adapter are retired to their preserved Git lineage.

The model transport keeps exact JSON content and explicit prompt-cache boundaries
for instructions, growing conversation history and stable Research turn context.
Research and Answer have separate cache families; mutable Evidence and corrections
remain outside those stable boundaries. Transport, Exa policy and the credential
broker remain mechanical infrastructure, with no semantic decision authority.

## Safe development observations

An optional observer receives normalized public events: bounded structured
decisions, field-specific rejected-decision diagnostics, selected requests and
acquisition outcomes, budget facts, exact acquired/exposed public material,
verified literal answer-reading selections, and exposure IDs, lengths and hashes. It never
receives raw provider responses or hidden reasoning. The small returned trace
excludes source bodies; exact bodies can be captured separately through the
observer when an authorized development observation needs them.

`scripts/v2_campaign.py` remains a development-only observation caller (its name
identifies historical campaign files). It calls the ordinary session application
with explicit Luna/medium configuration and no engine override. It supplies only the frozen selected
question, never the rubric, expected identities, known URLs or a scripted route.
JSON lines go through the existing doorman's sanitized output boundary. The
doorman handles credentials and process plumbing only. Useful exact public
failures and controls may be captured as development candidates in ignored
`local-evals/` under `docs/operator/LOCAL_EVALUATION_CORPUS.md`; the runtime does
not depend on that corpus.
