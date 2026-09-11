# ScryRaven Product

Status: approved Part B product charter

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
6. produce an answer from supported findings with citations to the acquired material that supports them; and
7. represent unresolved limitations honestly when reasonable bounded research does not establish the answer.

The product must not silently fill an evidentiary gap from unsupported model memory.

## Follow-up research

A follow-up receives a fresh Research -> Analyst -> Author decision over the current
question. Prior conversation helps interpret intent but is not evidence. Actual
previously acquired source material may remain evidence and be reused when relevant;
previous generated answers and Analyst judgments never become factual evidence.
Current findings require current supporting source material. New research occurs
when retained evidence does not establish what the follow-up needs.

## Durable product invariants

- Research is question-directed and may adapt when an initial attempt is inadequate.
- Search ranking, ordering, titles and other metadata guide navigation. Source-derived text returned with search results can support a claim when the received text itself establishes the claim and its materially necessary context.
- Factual answer support comes from source material that ScryRaven has actually received and read. Missing qualifications, applicability or connecting context require further acquisition; provider provenance alone does not establish completeness.
- A model semantically interprets acquired evidence in the context of the user's question, including relevant qualifications, conflicts, and limitations.
- Semantic interpretation may identify an important unresolved information need and cause further research.
- Acquired evidence retains its source identity as analysis and answer writing proceed.
- Answer-relevant findings remain connected to the acquired evidence that supports them.
- Answer writing may operate from a deliberately selected subset of supporting material rather than the complete research corpus.
- Final citations resolve to acquired material that actually supports the cited answer.
- Compact references let the user inspect the selected source material and open its
  original publication, without implying more precise support locations than the
  acquired evidence establishes.
- Deterministic mechanics may preserve identities, move data, validate references, and render citations; they must not substitute mechanical rules for semantic evidence judgment.
- When the available research does not establish an answer, ScryRaven preserves that limitation rather than upgrading uncertainty into unsupported certainty.

## Deferred capabilities

Multi-component research is the immediate next product capability after the first single-component slice works.

That capability should allow one user question to create several research needs, research those needs using the same evidence-grounded behavior, reason across the combined relevant evidence, and produce one coherent answer.

Multi-component scheduling, graphs, parallel execution, specialist systems, persistent research sessions, generalized recovery systems, and other broader capabilities are not part of the first supported promise and should not be prebuilt merely in anticipation of future use.

## Implementation posture

Product behavior governs implementation, not the reverse.

Provider choices, model assignments, prompts, model-call counts, research-loop limits, context representations, local state shapes, and other implementation details may be revised or removed when product evidence supports a better approach.

The prior ScryRaven v1 implementation and historical architecture create no compatibility or preservation obligation for future implementation.
