Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG91K_FINAL_ANSWER_PACKET_AUTHOR_EXECUTOR_UNDER_RUNKERNEL).

# AG-91K FinalAnswerPacket / AuthorExecutor Under RunKernel

Status: historical phase note, demoted by AG-95U.

AG-91K put final packet preparation and Author execution under RunKernel
authorization. `FinalAnswerPacket` owns citation eligibility, missing
obligations, mandatory caveats, prohibited upgrades, readiness, and the
packet-derived Author payload. `AuthorExecutor` writes final prose from that
payload and does not decide evidence sufficiency or citation policy.

Current AG-95U routing:

- packet preparation is consumed through
  `prepare_final_answer_packet_author_handoff_from_scope`;
- Author execution is consumed through `execute_author_handoff_from_scope`;
- post-Author projections validate against RunKernel packet state where
  available.

Historical implementation details are available in git history. Current
maintenance guidance lives in
`docs/history/architecture/phases/AG95U_FINAL_EVIDENCE_AUTHOR_HANDOFF_EXTRACTION.md`.
