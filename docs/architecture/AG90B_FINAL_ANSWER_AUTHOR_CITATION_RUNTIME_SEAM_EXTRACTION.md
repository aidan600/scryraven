# AG-90B Final Answer / Author / Citation Runtime Seam

Status: historical phase note, demoted by AG-95U.

AG-90B introduced `core.final_answer_runtime_assembly` as the compatibility
shell for pre-Author packet/payload assembly and post-Author citation/source
handoff assembly. It preserved Author prose, citation formatting, provider
selection, final evidence selection, and query/search behavior.

Current AG-95U routing:

- packet preparation is wrapped by
  `prepare_final_answer_packet_author_handoff_from_scope`;
- post-Author citation/source compatibility remains packet-derived through
  `final_answer_runtime_assembly`;
- the orchestrator no longer locally authorizes, executes, or reduces packet
  preparation.

Historical implementation details are available in git history. Current
maintenance guidance lives in
`docs/architecture/AG95U_FINAL_EVIDENCE_AUTHOR_HANDOFF_EXTRACTION.md`.
