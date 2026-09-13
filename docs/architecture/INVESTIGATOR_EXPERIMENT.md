# Investigator experiment

Status: approved experimental architecture, mechanically implemented and tested
offline. Ordinary production remains **Research -> Analyst -> Author**. The explicit
developer harness exercises **Investigator -> Author**. There is no replacement
decision, demonstrated live quality, public selector, or Reading Room change.

## Responsibility and loop

Investigator interprets the current target and intellectual operation, directs
acquisition, interprets actual Evidence, synthesizes relationships, revises its
understanding, and decides to continue, clarify, or finish supported/partial/unable.
Authority is claim-specific; source classes do not mechanically decide support.
Obligations arise when a concrete trigger, material answer impact and plausible
useful next action exist. Mechanics check those fields, not their justification.

One loop exposes conversation context, compact state, active exact Evidence, the
last mechanical action result (including its requested action as non-evidentiary
context) and a catalog window. Only the preceding request is retained for this
feedback, not an action history or persistent transcript. One model response updates
state and chooses one action. Mechanics validate references against that input,
apply shelving, execute the action and expose the resulting working set next time.
There are no relevance/shelving calls, semantic summaries, planner/reviewer agents,
graphs, task schedulers, or renewable per-obligation allowances.

The private contracts are `InvestigationState`, `InvestigatorDecision` and
`InvestigatorTerminal`. They do not use Research orientation/actions or Analyst
component assessments. State holds interpreted target/operation, supported notes,
qualifications/conflicts and unresolved obligations. Active refs and remaining
envelopes are supplied separately by mechanics and cannot be overwritten by the
model. State size is bounded without truncation or a summarization service.

## Corpus, state, attention and shelf

- **Retained corpus:** immutable actual acquisitions, using existing `Evidence`
  and the session acquisition collection. Admission is independent of final
  selection. Usable highlights and fetched text survive a successful candidate
  turn even when shelved or unselected; navigation/omission/summary text does not.
- **State:** semantic continuity only. Notes are not Evidence or factual authority.
- **Active set:** exact materials deliberately exposed to the current model call.
  Small acquisitions activate whole when capacity permits. A capacity miss retains
  the entire acquisition and reports that it was not activated. No source is
  evicted or summarized to fit automatically.
- **Shelf/catalog:** body-free ID, source ID, title, URL, acquisition type, parent,
  exact ranges, size, and current-turn exposure/active flags. Catalog windows and
  metadata lookup are bounded. Any known material remains directly addressable,
  including after a lexical miss or outside the current page.

Shelving removes only active membership. Reopening the same ID restores identical
text. The existing `exact_view` produces source-preserving slices of full parents;
the existing disposable `SourceIndex` locates regions without judging relevance.
Offsets are Python character offsets in received extraction, not document pages,
sections, bytes or proof positions. Views retain parent/source identity and never
become independent corroboration. Exact view IDs can be reconstructed from retained
parents across turns; disposable views and indexes are not separate acquisitions.
Repeated local region inspection has no one-expansion rule and performs no refetch.

## Actions and support validation

| Action | Mechanical behavior |
| --- | --- |
| Discover | Existing injected search transport; separate navigation from actual highlights; retain usable text and expose whole items within available attention. |
| Read | Known discovery/material ID plus concrete missing context; reuse a retained full parent locally, otherwise use existing fetch transport. Large parents may require a subsequent exact-range Inspect. |
| Inspect | Local activation, exact parent ranges, lexical region locations or paged catalog changes; no provider I/O. Shelving is also available on each decision. |
| Finish | Integrated synthesis, qualifications/conflicts, unresolved requested portions, posture/stop explanation and one exact supporting material set. |
| Clarify | Concise consequential ambiguity and target difference; an experimental terminal signal only. |

New or changed notes must reference known exact materials exposed in **that model
input**. Unchanged supported notes can survive shelving, but cannot be cited as
material by other notes. Inspection in a response cannot backdate exposure to
support a new finding in that same response. A new terminal comparison, causal
explanation or other synthesis must likewise have its actual supporting material
exposed, regardless of what prior notes say. Finish validates every exact selected
ID against both the input's exposure set and the remaining active set, so a Finish
response cannot shelve its own support. Reactivation must precede that reasoning
call; there is no hidden mechanical support assembly after Finish.

These checks establish identity and exposure, not entailment. Investigator still
judges whether the cited material supplies all necessary definitions, conditions,
qualifications and relationships. Mechanics cannot detect an undeclared semantic
dependency or prove that a conclusion follows from its declared support.

## Author and terminal compatibility

`compatibility.terminal_analysis` is the sole projection into legacy `Analysis`.
The terminal declares one integrated analysis with one exact total support set,
not individual sentence-to-passage mappings. Synthesis and labelled qualifications
and conflicts become one finding without rewriting their text. Interpreted target
and intellectual operation become the coverage target; each unresolved portion
keeps its text and limitation. The stop explanation is preserved exactly.
Canonical source references occupy legacy support fields, while the identical
exact material set is preserved in `Result.selected_evidence` and historical
citation snapshots. This retains the declared source-level support semantics.
It does not claim per-sentence proof precision.

The unchanged Author prompt and the shared `_author_result` consumer handle prose,
citations and results. Author cannot invent comparisons, causal conclusions,
criteria, facts or conflict resolutions that Investigator did not establish.
`supported` maps to the existing supported result; partial/unable map to existing
non-established closure, retaining the detailed candidate stop reason in Analysis.
This adapter is terminal-only and does not drive the candidate loop. A future
terminal requiring independently attributed per-finding exact proof mappings or
another unsupported durable semantic shape requires an explicit compatibility
decision; this phase does not silently introduce such a shape or a schema change.

## Sessions and transport

`ResearchSession` accepts one optional callable engine. Omission still calls the
existing production engine. `research.run` and ordinary CLI/Reading Room defaults
are unchanged. Candidate harnesses explicitly inject `InvestigatorEngine` and all
I/O. No registry, provider router, alternate database, or stored engine mode exists.

Successful candidate Results use the existing atomic session commit. Failed model,
action, citation or commit paths leave completed memory and durable state intact.
Clarify raises `ClarificationRequired` before commit; isolated harness calls return
its `Clarify` signal. There is no waiting/suspended state or completed clarification
turn. A durable session created before clarification can remain an ordinary empty
session; no special lifecycle is added.

Each follow-up starts with no Investigator state, verdict, priorities, active set,
or exposure history. Prior question/answer pairs help interpret intent only. The
candidate does not receive prior Analysis/semantic history. Retained acquisitions
and canonical identities remain available, and historical answer snapshots remain
exact. Candidate execution must be reinjected after reopen; opening normally uses
production. Indexes, windows, attention membership, intermediate state and reasoning
transcripts never enter the existing version-1 session schema.

The minimal model binding uses the existing stateless structured-output transport
and internal FAST assignment, without a new provider/role configuration. Instructions
and schema define a cache family; applicable conversation remains the stable prefix.
Changing state, active Evidence, mechanical results and catalog remain current
input. All active text survives lossless JSON serialization; retained shelved bodies
are never inserted into a cache prefix. `store=False` and explicit cache behavior
remain unchanged. The assembled input safety guard rejects oversized input rather
than silently dropping active material. No prompt-quality claim is made.

## Experimental knobs and executable harness

`ExperimentalLimits` defaults to 16 nonterminal cycles, 16 external acquisition
attempts and 128,000 active Evidence characters. Catalog/region page sizes and
state/model-input character guards are also configurable development knobs. These
values are not durable product semantics or sufficiency thresholds.

Local inspections and reused full reads consume cycles, not external allowance.
Failed external attempts consume allowance. New obligations cannot replenish either
counter. Spending the last external attempt permits local work and a warranted
Finish; requesting another external acquisition exhausts the investigation. At
cycle exhaustion or a denied acquisition there is one bounded terminal-only model
step, accepting partial/unable or Clarify. No action executes or budget renews there.
A nonterminal/supported response there produces explicit unable closure without
promoting semantic notes or treating missing evidence as nonexistence. Needed final
support must be assembled within the normal local cycle allowance.

Run the deterministic synthetic demonstration:

```text
python -m scryraven.experimental.harness
```

For scripted isolated or session tests, construct `CandidateHarness` with explicit
model/search/fetch callables and optional limits. It exposes `run`, `session`,
`create(store=...)` and `open(id, store=...)`. Durable experiments must use an explicit
disposable database path. `ScriptedModel` supplies deterministic responses while
the actual loop, adapter, Author and citation/session consumers execute normally.

## Evaluation and unresolved decisions

`tests/test_investigator.py` proves admission without selection, reversible shelving,
exact repeated views, canonical identity, catalog reachability, current exposure
checks, terminal support, unchanged Author material, citation grouping, fresh
follow-ups, process reopen, historical snapshots, failed-turn rollback/conflicts,
Clarify, independent configurable envelopes, and lossless fake-transport input.
Existing run/session/CLI/Reading Room and cache/transport regressions protect the
ordinary path. All Phase 2 execution is offline with synthetic data; no real session
database, private evaluation corpus, live OpenAI or Exa is used.

The evaluation sequence is mechanical proof, separately authorized varied behavioral
evaluation, then a human decision about production replacement. Live quality,
question fidelity, semantic support completeness, attention choices, suitable knob
values and Investigator superiority remain unproved. Durable clarification/UI
integration and any incompatible future terminal semantics remain separate
decisions. Phase 2 does not perform that behavioral evaluation or replacement.
