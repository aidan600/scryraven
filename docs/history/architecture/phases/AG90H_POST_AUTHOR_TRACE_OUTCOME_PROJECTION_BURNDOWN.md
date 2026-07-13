Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG90H_POST_AUTHOR_TRACE_OUTCOME_PROJECTION_BURNDOWN).

# AG-90H Post-Author Trace / Outcome Projection Burndown

Status: historical phase note, demoted by AG-95U.

AG-90H moved post-Author trace/output projection packaging into
`core.post_author_output_projection`. It kept persistence side effects,
provider/search/model calls, citation formatting, final evidence selection, and
Author prose out of the helper.

Current AG-95U routing extends the same module with final source telemetry,
session payload, and stage-ledger handoff packaging. The helper observes
`FinalEvidenceBundle` and `FinalAnswerPacket` state; it does not decide final
evidence, citation policy, or final answer posture.

Historical implementation details are available in git history. Current
maintenance guidance lives in
`docs/history/architecture/phases/AG95U_FINAL_EVIDENCE_AUTHOR_HANDOFF_EXTRACTION.md`.
