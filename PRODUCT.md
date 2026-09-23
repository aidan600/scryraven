# ScryRaven Product

Status: approved product charter, including Mainline Semantic Supersession 01

ScryRaven is a research assistant for turning user research questions into useful, evidence-grounded answers.

Its core product behavior is not merely search plus prose. ScryRaven should direct research toward the information a question requires, acquire actual source material, semantically interpret what that material establishes in the context of the user's question, and keep final claims connected to the evidence that supports them.

## First supported product promise

The first supported product slice is a simple, single-component factual research question answerable through public web research.

For that class of question, ScryRaven should:

1. search for promising sources;
2. use search metadata to navigate and assess any returned source text by what that text establishes;
3. directly acquire and read useful source material;
4. semantically interpret the acquired material in the context of the original question;
5. continue research when interpretation reveals an important unresolved information need;
6. produce a fresh Evidence-first answer with citations to the acquired material that supports it; and
7. represent unresolved limitations honestly when reasonable bounded research does not establish the answer.

The product must not silently fill an evidentiary gap from unsupported model memory.

## Follow-up research

A follow-up receives fresh research interpretation and answer decisions over the
current user turn. Conversation is non-evidentiary task context for intent,
discourse, corrections and follow-up meaning. Explicit premises, constraints
and definitions in prior user questions may remain task inputs; user beliefs or
narration are not automatically stipulated premises. Prior assistant text is
discourse context only, never Evidence or a silent premise. A user may explicitly
adopt a prior assistant value as a new scenario premise without making it an
externally verified fact. Actual previously acquired source material may remain
Evidence and be reused when relevant. Current external factual findings require
current supporting source material. New research occurs when external facts are
needed and retained evidence does not establish them.

A research session may be reopened later, preserving its conversation, acquired
Evidence, source identities and historical answer provenance. Reopening changes
lifetime only: previous generated answers remain non-evidentiary, prior Analyst
judgments remain semantic history, and follow-ups receive fresh semantic decisions
over actual acquired Evidence.

## Local Reading Room

The local browser product operates the same research-session application and
durable store as the CLI. It offers a continuous, readable research conversation,
persistent history, follow-up questions, session rename and confirmed permanent
deletion. Compact citations open the exact selected source material saved with
that historical answer, alongside publication identity and its original URL.
Citation numbering belongs to each answer. Later acquisitions must not change
historical inspection. The answer is the primary reading surface; evidence is
available in depth when requested. Working states and research limitations remain
honest, and the interface remains usable at narrow browser widths.

## Durable product invariants

- Research is question-directed and may adapt when an initial attempt is inadequate.
- Search ranking, ordering, titles and other metadata guide navigation. Source-derived text returned with search results can support a claim when the received text itself establishes the claim and its materially necessary context.
- External factual answer support comes from source material that ScryRaven has actually received and read. Missing qualifications, applicability or connecting context require further acquisition; provider provenance alone does not establish completeness.
- Explicit premises and constraints supplied by the user may define a hypothetical or conditional task. A conclusion derived solely from those premises may be answered without an Evidence citation when its conditional basis is clear. User premises remain non-Evidence task inputs, not externally verified facts, and must not be supplemented with missing external facts from model memory.
- Conversation helps interpret the user's task and corrections; a statement of belief or narration does not by itself stipulate a hypothetical premise. Prior assistant answers cannot become a premise without explicit user adoption.
- A model semantically interprets acquired evidence in the context of the user's question, including relevant qualifications, conflicts, and limitations.
- Semantic interpretation may identify an important unresolved information need and cause further research.
- Acquired evidence retains its source identity as analysis and answer writing proceed.
- Answer-relevant external factual findings remain connected to the acquired evidence that supports them.
- Answer writing may operate from a deliberately selected subset of supporting material rather than the complete research corpus.
- Final citations resolve to acquired material that actually supports the cited answer.
- Compact references let the user inspect the selected source material and open its
  original publication, without implying more precise support locations than the
  acquired evidence establishes.
- Deterministic mechanics may preserve identities, move data, validate references, and render citations; they must not substitute mechanical rules for semantic evidence judgment.
- When the available research does not establish an answer, ScryRaven preserves that limitation rather than upgrading uncertainty into unsupported certainty.

## Ordinary research architecture

The ordinary product promotes the demonstrated clean-room Research/Answer
architecture, including questions with multiple interacting components and
evidence-directed acquisition dependencies. The former Research -> Analyst ->
Author semantic path is superseded, with no alternate path or fallback.
One Research decision-maker interprets the original request and actual material,
revises a compact working understanding, chooses acquisition, and proposes stopping.
A mechanical executor performs Search, Read and local Find. A fresh Answer call
independently determines what the supplied sources or explicit user premises
justify. These are two semantic contracts; no verifier, Scout, specialist hierarchy
or model router is part of this design. Current fixed model assignments are
recorded in `CURRENT.md`; Exa supplies Search.

Actual Evidence remains immutable and locally rereadable. Generated understanding,
past answers and candidate hypotheses are not Evidence. Currentness means applicable
entity, role, conditions and time, rather than the newest publication. Source needs
depend on the requested operation. Budget exhaustion and failed searches establish
neither support nor nonexistence. A useful honest partial or unable answer is valid.

The CLI, durable sessions and Reading Room share this ordinary architecture.
Historical Analyst judgments remain inspectable semantic records only; new turns
must not fabricate Analyst objects or use historical judgments as factual authority.
Research chooses when the Evidence packet is ready, including when an operation
needs no external factual support; Answer independently decides what the
original/current request, explicit user premises and actual selected sources
justify. Research's generated verdict, notes or draft must not bind Answer.

Bounded Levels 1–5 demonstrations are development evidence, not a universal
reliability claim. Level 6 revision/recovery under superseding Evidence is not
established. The earlier Investigator and architecture-lab lineages are stopped
development history.

That capability should allow one user question to create several research needs, research those needs using the same evidence-grounded behavior, reason across the combined relevant evidence, and produce one coherent answer.

Multi-component scheduling, graphs, parallel execution, specialist systems, generalized recovery systems, and other broader capabilities are not part of the first supported promise and should not be prebuilt merely in anticipation of future use.

## Implementation posture

Product behavior governs implementation, not the reverse.

Provider choices, model assignments, prompts, model-call counts, research-loop limits, context representations, local state shapes, and other implementation details may be revised or removed when product evidence supports a better approach.

The prior ScryRaven v1 implementation and historical architecture create no compatibility or preservation obligation for future implementation.
