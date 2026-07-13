Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96_PROJECT_SOURCE_REFRESH_PACKET).

# AG-96 Project Source Refresh Packet

## Status

This is a repo-visible refresh packet for maintaining external project-source
material. It is not itself a ChatGPT Project Source file and does not assume
that any ChatGPT Project Source is present in this repository.

Post-#342 checkpoint note: this AG-96 packet is historical AG-96 maintenance
context. The current semantic-coverage Project Source refresh packet is in
`docs/architecture/AG_DOC_SEMANTIC_COVERAGE_CHECKPOINT_01.md`, and the current
next implementation gate is
`AG-SEMANTIC-OBSERVATION-ADMISSION-BRIDGE-01`.

## Mechanical Replacement Notes

SourceDoc02:

- Replace stale AG-96C wording with the current passive `SearchWorkPlan` shadow
  state.
- State that QueryPlan, provider/search behavior, citation behavior, final
  answers, and mode policy remain unchanged and unconsumed by the shadow
  projection.
- Link or refer to `docs/history/architecture/phases/AG96_CURRENT_STATE_AND_NEXT_CHOICES.md`
  and `docs/history/architecture/phases/AG96C8_RUNTIME_SHADOW_SEARCHWORKPLAN_CALLSITE.md` when
  repo-visible citations are needed.

SourceDoc04:

- Refresh the AG-96I3 lane as scout/read diagnostics: query shaping, freshness
  policy, Serper scout observation, scout-to-acquisition handoff, and offline
  read-observation verification.
- Keep durable doctrine generic: scout candidates are verification candidates,
  read observations are supplied sanitized inputs, and verified observations are
  still not final evidence.
- Avoid source-specific official/current doctrine; examples belong only as
  fixture provenance or historical triggers.

SourceDoc06:

- Add compact prompt discipline: future Codex prompts should be one phase brief,
  with standing workflow and boundary rules delegated to repo docs.
- Phase prompts should list only phase-specific goal, read files, scope, tests,
  validation, stop conditions, and final-bundle requirements.
- Do not claim ChatGPT Project Sources are repo files unless their contents are
  committed or explicitly provided in the prompt.

## SourceDoc05 Roadmap Questions

- Should the next AG-96I3 implementation prioritize the sanitized
  read-observation adapter for handoff candidates?
- When should EvidenceLedger admission-review diagnostics begin, and what
  custody fields must be stable first?
- Should AG-96C remain passive until a separate QueryPlan consumption phase, or
  should the roadmap schedule that activation explicitly?
- Which roadmap items are product priorities versus architecture debt records?
- Which source-quality validation loops require user-owned live validation or
  external project-source updates before implementation?
