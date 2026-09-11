# Proposed retained-context PRODUCT validation

Execution is not authorized by the implementation work item. No live calls have
been made for this capability. This packet is for review and later human approval.

Proposed envelope: one ordinary process, one ResearchSession, at most three public
questions, with unchanged per-turn production limits. Stop on an execution failure;
do not repeat the session, repair and rerun, or check sources independently without
further authorization. Do not optimize prompts or caching during the observation.

Suggested questions (selection has not been checked against live sources):

1. According to the BIPM SI Brochure, what are the name, symbol and power of ten of
   the largest SI prefix? Read the prefix table's source context.
2. And what are those for the smallest prefix in that same table?
3. According to NASA, what is Mars's orbital period in Earth days?

The first two questions offer two facts from one source; the third requires
different information. The outcome is inconclusive for reuse if the actual
first-turn material lacks the second fact. Do not insert a fixture, seed the corpus,
force a Research selection, or treat a previous answer as source material.

Use the existing credential broker with a small caller that only constructs the
documented public ResearchSession, calls `ask` sequentially, and prints each Result
with the existing renderer and safe diagnostic fields. The broker closes stdin,
so interactive `--session` cannot accept later questions through it. All Research,
Analyst, Author and provider work must use ordinary production functions. Keep
sanitized review outputs outside the repository; do not serialize session state.

Record the exact tested revision, public questions/answers, selected Evidence,
citations/CitationUse and safe traces. Decide:

- Did turn 2 receive fresh Research and Analyst calls, retain the canonical source
  identity, and answer from actual retained material with zero new search/fetch?
- If turn 2 needed more context, did it preserve the highlights/full-parent
  distinction and accurately disclose the extra acquisition?
- Did turn 3 make new acquisitions when needed and allocate noncolliding identities?
- Do all answer-local references resolve to the current supporting material and
  original publication, with qualifications and limitations preserved?

Preserve useful sanitized evaluation evidence according to
`LOCAL_EVALUATION_CORPUS.md` if appropriate. Do not publish local-evals. Report
observed limitations without claiming universal relevance, fidelity or reliability.
