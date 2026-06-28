# AG-ANALYSIS-GAP-FOLLOWUP-SEARCH-01

Status: Implementation posture note for the proposal-only Analyst gap follow-up
search intent packet.

`FollowupSearchIntentPacket` contains `AnalysisGapSearchProposal` records built
from validated `EvidenceRelativeAnalysisPacket` /
`analyst_report.analysis_gap_proposals`. This is a proposal-only
gap-to-search-intent posture. It is not search authorization, not a query plan,
does not create SearchExecutorHandoff, does not dispatch search, does not create
evidence, and RunKernel/SearchPlanner/SearchExecutorHandoff authorization
remains required before any executable search work exists.

The packet may carry gap lineage, current answer contract ref/digest, bounded
source-class/currentness/query/budget hints, and
`ready_for_authorization_review` as structural review readiness only. It keeps
`authorized`, `query_plan_created`, `search_executor_handoff_created`,
`search_dispatched`, provider/broker/model/retrieval/fetch-read flags,
EvidenceLedger/SemanticObservation/ComponentCoverage flags, citation/source
obligation/Sufficiency/FAP/Author/readiness/product-correctness flags, and
contract mutation flags false.

## Legacy surface audit

- AG-96 followup_* provider/FAP/Author stack: avoided/legacy/passive for this
  phase. It remains historical follow-up provider, evidence intake,
  Sufficiency/FAP, citation, and Author machinery and is not consumed by
  `FollowupSearchIntentPacket`.
- source-class recovery bridges: avoided/legacy/passive. The new packet carries
  source-class and currentness hints only; it does not activate source-class
  recovery or satisfy source obligations.
- component gap recovery runtime: avoided/legacy/passive. This phase does not
  execute component-gap recovery, call adapters, admit EvidenceLedger custody,
  or commit semantic coverage.
- SearchWorkPlan shadow machinery: avoided/legacy/passive. The packet is not a
  SearchWorkPlan, does not create query tasks, and does not feed QueryPlan
  consumption.
- offline SearchExecutor bridge: avoided/legacy/passive. The packet does not
  use the old bridge and does not create offline SearchExecutor observations.
- provider wrappers/retrieval/pipeline orchestrator: avoided/legacy/passive.
  Provider routing, broker contact, retrieval, fetch/read, and
  `core/pipeline_orchestrator.py` remain closed.

later retirement targets include the old AG-96 followup provider/FAP/Author
stack, source-class recovery compatibility bridges, component-gap recovery
runtime coupling, SearchWorkPlan shadow compatibility machinery, and the
offline SearchExecutor bridge once the current RunKernel/SearchPlanner/
SearchExecutorHandoff authorization path has explicit successors for any needed
behavior.
