from __future__ import annotations

from dataclasses import dataclass

NEXT_EXTRACTION_PHASE = "AG-76C-FE"
NEXT_EXTRACTION_RECOMMENDATION = (
    "AG-76C-FE - Final Evidence Bundle / Source-ID Assignment Replacement Extraction"
)

FINAL_EVIDENCE_BUNDLE_DECISION = "final_evidence_bundle_construction"
SOURCE_ID_ASSIGNMENT_DECISION = "source_id_assignment"

PROTECTED_FINAL_EVIDENCE_SURFACES: tuple[str, ...] = (
    "final_answer_prose",
    "Author_behavior",
    "citation_formatting",
    "citation_selection",
    "final_evidence_selection_behavior",
    "provider_routing",
    "provider_selection",
    "provider_depth",
    "query_generation",
    "source_class_classifier_semantics",
    "candidate_fit_semantics",
)


@dataclass(frozen=True)
class PipelineDecisionRegistryEntry:
    decision_name: str
    current_location: str
    current_owner: str
    target_owner: str
    executor_helper: str
    observer_export_surface: str
    protected_surface_risk: tuple[str, ...]
    current_test_coverage: tuple[str, ...]
    deletion_or_extraction_status: str
    next_action: str
    priority: str


@dataclass(frozen=True)
class FinalEvidenceOwnershipResponsibility:
    responsibility: str
    decision_owner: str
    mechanical_builder: str
    observer_export_surface: str
    author_citation_consumer: str
    remaining_orchestrator_handoff: str


@dataclass(frozen=True)
class FinalEvidenceReplacementContract:
    old_responsibility: str
    replacement_owner_module: str
    input_contract: tuple[str, ...]
    output_contract: tuple[str, ...]
    source_id_assignment_responsibilities: tuple[str, ...]
    final_evidence_ordering_responsibilities: tuple[str, ...]
    identity_preservation_requirements: tuple[str, ...]
    author_handoff_boundary: str
    trace_export_observer_boundary: str
    required_parity_tests: tuple[str, ...]
    protected_surfaces: tuple[str, ...]
    deletion_plan: tuple[str, ...]


PIPELINE_DECISION_REGISTRY: tuple[PipelineDecisionRegistryEntry, ...] = (
    PipelineDecisionRegistryEntry(
        decision_name=FINAL_EVIDENCE_BUNDLE_DECISION,
        current_location=(
            "core/pipeline_orchestrator.py lines 5341-5370, 5941-5971, "
            "6138-6171, and 6299-6317"
        ),
        current_owner="pipeline_orchestrator.py local final_top_evidence assembly",
        target_owner="core.final_evidence_bundle_builder",
        executor_helper="core.final_evidence_bundle_builder.build_final_evidence_bundle",
        observer_export_surface=(
            "core.runtime_trace_projection_assembly and "
            "core.official_canonical_recovery_visibility_export observe only"
        ),
        protected_surface_risk=PROTECTED_FINAL_EVIDENCE_SURFACES,
        current_test_coverage=(
            "tests/test_source_class_recovery_trace.py source_id parity",
            "tests/test_ag74b_controller_authority_disposition.py ledger parity",
            "tests/test_ag74c_ledger_gated_visibility_consumer_subordination.py export parity",
            "tests/test_answer_contract_runtime_handoff.py handoff parity",
            "tests/test_ag75c_local_authority_gate_retirement.py recovered visibility parity",
        ),
        deletion_or_extraction_status="blueprint_only_ag76b_extract_next",
        next_action=NEXT_EXTRACTION_RECOMMENDATION,
        priority="P0",
    ),
    PipelineDecisionRegistryEntry(
        decision_name=SOURCE_ID_ASSIGNMENT_DECISION,
        current_location=(
            "core/pipeline_orchestrator.py local unique_source_urls / "
            "ordered_sources / source_id loops"
        ),
        current_owner="pipeline_orchestrator.py URL-to-integer source ID loop",
        target_owner="core.final_evidence_bundle_builder",
        executor_helper="core.final_evidence_bundle_builder.assign_stable_source_ids",
        observer_export_surface=(
            "final answer source telemetry and source-class observability consume assigned IDs"
        ),
        protected_surface_risk=(
            "Author_behavior",
            "citation_formatting",
            "citation_selection",
            "source_identity_preservation",
        ),
        current_test_coverage=(
            "tests/test_source_class_recovery_trace.py::"
            "test_source_class_recovery_inserts_recovered_source_into_final_evidence",
            "tests/test_pre_analyst_gate.py source-binding diagnostics",
        ),
        deletion_or_extraction_status="blueprint_only_ag76b_extract_next",
        next_action=NEXT_EXTRACTION_RECOMMENDATION,
        priority="P0",
    ),
    PipelineDecisionRegistryEntry(
        decision_name="author_evidence_handoff",
        current_location="core/pipeline_orchestrator.py author_evidence / author_evidence_block assembly",
        current_owner="pipeline_orchestrator.py",
        target_owner="core.final_evidence_bundle_builder packages; Author consumes",
        executor_helper="core.final_evidence_bundle_builder.build_author_evidence_block",
        observer_export_surface="ControllerEvidenceLedger and runtime trace projections observe handoff outcomes",
        protected_surface_risk=("Author_behavior", "citation_formatting", "final_answer_prose"),
        current_test_coverage=("existing final answer/citation parity tests",),
        deletion_or_extraction_status="mapped_for_ag76c_fe",
        next_action="Move packaging only; do not change Author prompt semantics.",
        priority="P0",
    ),
    PipelineDecisionRegistryEntry(
        decision_name="final_source_telemetry",
        current_location=(
            "core/pipeline_orchestrator.py final_answer_source_telemetry, "
            "source_survival_* counts, and record_final_evidence_snapshot"
        ),
        current_owner="pipeline_orchestrator.py writes observed telemetry",
        target_owner="observer/export surfaces after final bundle output",
        executor_helper="trace/projection/export attachment helpers",
        observer_export_surface=(
            "runtime_trace_projection_assembly, official_canonical_recovery_visibility_export, "
            "evidence_registry_mirror"
        ),
        protected_surface_risk=("citation_selection", "final_answer_prose", "trace_schema_churn"),
        current_test_coverage=(
            "tests/test_runtime_trace_projection_assembly_ag46c.py",
            "tests/test_official_canonical_recovery_visibility_export_ag50c.py",
        ),
        deletion_or_extraction_status="observer_boundary_defined",
        next_action="Keep telemetry observer-only when final bundle builder lands.",
        priority="P1",
    ),
    PipelineDecisionRegistryEntry(
        decision_name="recovered_evidence_visibility_boundary",
        current_location="core/recovered_evidence_visibility.py",
        current_owner="ControllerRecoveryDecision plus recovered evidence visibility helper",
        target_owner="Controller-approved candidate stream and final evidence builder input",
        executor_helper="apply_controller_recovered_evidence_visibility",
        observer_export_surface="AuthorityLifecycle candidate fit and ControllerEvidenceLedger",
        protected_surface_risk=("candidate_fit_semantics", "final_evidence_selection_behavior"),
        current_test_coverage=("tests/test_ag75c_local_authority_gate_retirement.py",),
        deletion_or_extraction_status="moved_out_of_orchestrator_ag75c",
        next_action="Treat as an input to AG-76C-FE, not a behavior rewrite.",
        priority="P1",
    ),
    PipelineDecisionRegistryEntry(
        decision_name="provider_search_allocation_execution",
        current_location=(
            "core/controller_provider_search_allocation.py and "
            "core/source_class_recovery_runner.py"
        ),
        current_owner="ControllerRecoveryDecision",
        target_owner="ControllerRecoveryDecision with bounded runner execution",
        executor_helper="source_class_recovery_runner",
        observer_export_surface="allocation custody and visibility export projections",
        protected_surface_risk=("provider_routing", "provider_selection", "provider_depth"),
        current_test_coverage=(
            "tests/test_ag75a_controller_provider_search_allocation_gate.py",
            "tests/test_ag75a_y_allocation_result_candidate_custody.py",
        ),
        deletion_or_extraction_status="already_controller_authorized",
        next_action="No AG-76B change.",
        priority="P2",
    ),
    PipelineDecisionRegistryEntry(
        decision_name="candidate_custody_disposition",
        current_location=(
            "core/allocation_result_candidate_custody.py and "
            "core/allocation_candidate_selection_activation.py"
        ),
        current_owner="ControllerEvidenceLedger and allocation custody projection",
        target_owner="ControllerEvidenceLedger custody with builder input stream",
        executor_helper="allocation_result_candidates_for_existing_selection_corridor",
        observer_export_surface="runtime trace projection and official/canonical visibility export",
        protected_surface_risk=("candidate_fit_semantics", "source_class_classifier_semantics"),
        current_test_coverage=(
            "tests/test_ag75a_y_allocation_result_candidate_custody.py",
            "tests/test_ag75a_z_allocation_candidate_selection_activation.py",
        ),
        deletion_or_extraction_status="subordinate_candidate_stream",
        next_action="Feed AG-76C-FE as already-custodied candidate input only.",
        priority="P1",
    ),
    PipelineDecisionRegistryEntry(
        decision_name="recovery_retry_stop_provider_review_decision",
        current_location="core/controller_recovery_decision.py",
        current_owner="ControllerRecoveryDecision",
        target_owner="ControllerRecoveryDecision",
        executor_helper="source_class_recovery_runner executes approved actions",
        observer_export_surface="runtime trace projection assembly",
        protected_surface_risk=("provider_routing", "query_generation", "follow_up_behavior"),
        current_test_coverage=(
            "tests/test_ag74d_controller_recovery_retry_stop_loop.py",
            "tests/test_ag74f_recovery_runner_extraction.py",
        ),
        deletion_or_extraction_status="controller_owned",
        next_action="No AG-76B change.",
        priority="P2",
    ),
    PipelineDecisionRegistryEntry(
        decision_name="trace_projection_export_attachment",
        current_location=(
            "core/runtime_trace_projection_assembly.py and "
            "core/official_canonical_recovery_visibility_export.py"
        ),
        current_owner="observer/export only",
        target_owner="observer/export only",
        executor_helper="attach_passive_runtime_projection_traces",
        observer_export_surface="execution trace, official/canonical export, diagnostics",
        protected_surface_risk=("trace_schema_churn", "citation_selection"),
        current_test_coverage=(
            "tests/test_runtime_trace_projection_assembly_ag46c.py",
            "tests/test_ag74c_ledger_gated_visibility_consumer_subordination.py",
        ),
        deletion_or_extraction_status="must_remain_passive",
        next_action="Add AG-76C-FE parity assertions after builder extraction.",
        priority="P1",
    ),
    PipelineDecisionRegistryEntry(
        decision_name="answer_contract_obligation_handoff",
        current_location="core/answer_contract_runtime_handoff.py",
        current_owner="AnswerContract",
        target_owner="AnswerContract for obligations; final builder consumes fulfilled state only",
        executor_helper="build_runtime_answer_contract_handoff",
        observer_export_surface="ControllerEvidenceLedger AnswerContractUpdated events",
        protected_surface_risk=("prompt_behavior", "citation_selection", "final_answer_prose"),
        current_test_coverage=("tests/test_answer_contract_runtime_handoff.py",),
        deletion_or_extraction_status="input_state_not_selector",
        next_action="Do not make final evidence builder decide obligations.",
        priority="P1",
    ),
)


FINAL_EVIDENCE_OWNERSHIP_BLUEPRINT: tuple[FinalEvidenceOwnershipResponsibility, ...] = (
    FinalEvidenceOwnershipResponsibility(
        responsibility="Final evidence source collection",
        decision_owner="ControllerEvidenceLedger and Controller-approved recovery/allocation state",
        mechanical_builder="core.final_evidence_bundle_builder",
        observer_export_surface="runtime trace projection assembly",
        author_citation_consumer="Author receives packaged evidence only",
        remaining_orchestrator_handoff="pass all_passages and controller lifecycle state",
    ),
    FinalEvidenceOwnershipResponsibility(
        responsibility="Final evidence ordering",
        decision_owner="existing filter_top_evidence ordering contract until separately licensed",
        mechanical_builder="core.final_evidence_bundle_builder preserves current order",
        observer_export_surface="record_final_evidence_snapshot observes final order",
        author_citation_consumer="Author/citation consume stable ordered bundle",
        remaining_orchestrator_handoff="provide top_chunks, max_domain_chunks, and complexity-derived cap",
    ),
    FinalEvidenceOwnershipResponsibility(
        responsibility="Recovered/Controller-selected evidence insertion",
        decision_owner="ControllerRecoveryDecision and recovered evidence visibility helper",
        mechanical_builder="core.final_evidence_bundle_builder calls existing helper",
        observer_export_surface="AuthorityLifecycle candidate fit and ControllerEvidenceLedger",
        author_citation_consumer="Author sees only final packaged result",
        remaining_orchestrator_handoff="provide active_source_class_recovery_lifecycle",
    ),
    FinalEvidenceOwnershipResponsibility(
        responsibility="Source identity preservation",
        decision_owner="final evidence identity registry contract",
        mechanical_builder="core.final_evidence_bundle_builder",
        observer_export_surface="final source telemetry observes URL/source_id mapping",
        author_citation_consumer="citation surfaces rely on preserved source_id values",
        remaining_orchestrator_handoff="receive immutable mapping output",
    ),
    FinalEvidenceOwnershipResponsibility(
        responsibility="Source ID assignment",
        decision_owner="final evidence identity registry contract",
        mechanical_builder="core.final_evidence_bundle_builder.assign_stable_source_ids",
        observer_export_surface="final answer source telemetry",
        author_citation_consumer="Author evidence block and Sources list consume assigned IDs",
        remaining_orchestrator_handoff="no local unique_source_urls loop after AG-76C-FE",
    ),
    FinalEvidenceOwnershipResponsibility(
        responsibility="Stable source ordering",
        decision_owner="final evidence identity registry contract",
        mechanical_builder="core.final_evidence_bundle_builder",
        observer_export_surface="source-class observability telemetry",
        author_citation_consumer="ordered Sources list preserves first URL occurrence",
        remaining_orchestrator_handoff="consume ordered_sources output",
    ),
    FinalEvidenceOwnershipResponsibility(
        responsibility="Author evidence block packaging",
        decision_owner="AnswerContract and existing Author prompt contract for consumption",
        mechanical_builder="core.final_evidence_bundle_builder",
        observer_export_surface="Author handoff telemetry observes only",
        author_citation_consumer="Author prompt consumes packaged block unchanged",
        remaining_orchestrator_handoff="splice returned block into existing prompt position",
    ),
    FinalEvidenceOwnershipResponsibility(
        responsibility="Final source telemetry",
        decision_owner="ControllerEvidenceLedger custody for interpretation",
        mechanical_builder="trace/projection/export helpers",
        observer_export_surface="official/canonical visibility export and final answer source telemetry",
        author_citation_consumer="No Author decision ownership",
        remaining_orchestrator_handoff="pass final bundle output to existing observers",
    ),
    FinalEvidenceOwnershipResponsibility(
        responsibility="Citation eligibility inputs",
        decision_owner="AnswerContract and ControllerEvidenceLedger",
        mechanical_builder="core.final_evidence_bundle_builder exposes source identity inputs",
        observer_export_surface="official/canonical visibility export",
        author_citation_consumer="citation selection remains closed",
        remaining_orchestrator_handoff="do not decide citation eligibility locally",
    ),
    FinalEvidenceOwnershipResponsibility(
        responsibility="Trace/export observation",
        decision_owner="ControllerEvidenceLedger for custody interpretation",
        mechanical_builder="runtime trace projection assembly",
        observer_export_surface="execution trace and export packets",
        author_citation_consumer="No Author/citation behavior ownership",
        remaining_orchestrator_handoff="call existing observer helpers with builder output",
    ),
    FinalEvidenceOwnershipResponsibility(
        responsibility="ControllerEvidenceLedger references",
        decision_owner="ControllerEvidenceLedger",
        mechanical_builder="builder passes observable final evidence records",
        observer_export_surface="ledger trace and official/canonical export",
        author_citation_consumer="No direct consumer behavior change",
        remaining_orchestrator_handoff="preserve ledger attachment points",
    ),
    FinalEvidenceOwnershipResponsibility(
        responsibility="AnswerContract obligation/posture references",
        decision_owner="AnswerContract",
        mechanical_builder="builder reads obligation state as input only",
        observer_export_surface="AnswerContract runtime handoff trace",
        author_citation_consumer="Author prompt posture remains unchanged",
        remaining_orchestrator_handoff="continue existing handoff calls",
    ),
)


FINAL_EVIDENCE_REPLACEMENT_CONTRACT = FinalEvidenceReplacementContract(
    old_responsibility=(
        "Replace the pipeline_orchestrator.py final_top_evidence construction, "
        "recovered evidence insertion handoff, source ID assignment, ordered "
        "source list creation, final/Author evidence block packaging, and "
        "observer handoff preparation currently repeated around lines 5341-5370, "
        "5941-5971, 6138-6171, and 6299-6317."
    ),
    replacement_owner_module="core.final_evidence_bundle_builder",
    input_contract=(
        "all_passages sorted by existing score semantics",
        "top_chunks",
        "max_domain_chunks derived from complexity",
        "deps.filter_top_evidence callable",
        "deps.is_plausible_domain callable",
        "active_source_class_recovery_lifecycle",
        "current_date",
        "query",
        "precision_count for Author evidence slicing",
    ),
    output_contract=(
        "final_top_evidence with stable source_id fields assigned",
        "unique_source_urls mapping URL to integer source ID",
        "ordered_sources list preserving first plausible URL occurrence",
        "evidence_block text matching existing formatting",
        "cached_prefix seed matching existing formatting",
        "author_evidence slice",
        "author_evidence_block text matching existing formatting",
        "trace/export observer payload inputs",
    ),
    source_id_assignment_responsibilities=(
        "assign the first integer ID when a URL first appears in final_top_evidence",
        "reuse the same integer ID for duplicate URLs",
        "write source_id on each final evidence passage exactly as current behavior does",
        "include only plausible domains in ordered_sources while preserving IDs for all URLs",
    ),
    final_evidence_ordering_responsibilities=(
        "preserve all existing filtering and score ordering semantics",
        "preserve recovered evidence reserve/replace results from the existing helper",
        "preserve Author precision slicing after final_top_evidence is complete",
    ),
    identity_preservation_requirements=(
        "do not renumber after Author evidence slicing",
        "do not change URL/title/text values",
        "do not change citation syntax or citation selection inputs",
        "keep source_id values stable across evidence_block, ordered_sources, and telemetry",
    ),
    author_handoff_boundary=(
        "The replacement packages evidence strings; Author prompt placement, system prompt, "
        "model call, citation formatting, and final answer prose remain closed consumers."
    ),
    trace_export_observer_boundary=(
        "Projection/export helpers observe final bundle outputs and ledger custody; they do "
        "not select final evidence, assign IDs, or change citation behavior."
    ),
    required_parity_tests=(
        "source ID parity for unique and duplicate URLs",
        "ordered_sources parity for plausible and implausible domains",
        "evidence_block and cached_prefix exact text parity",
        "author_evidence precision slicing parity",
        "supplemental/remediation rebuild parity for refreshed all_passages",
        "record_final_evidence_snapshot payload parity",
        "final answer source telemetry parity",
        "runtime trace projection/export parity",
        "static guard that pipeline_orchestrator.py no longer owns source ID loops after extraction",
    ),
    protected_surfaces=PROTECTED_FINAL_EVIDENCE_SURFACES,
    deletion_plan=(
        "Introduce core.final_evidence_bundle_builder with exact parity tests.",
        "Replace the three local final_top_evidence/source-ID rebuild blocks with one builder handoff.",
        "Replace the Author evidence slicing/block assembly with builder output.",
        "Keep Author prompt placement, citation behavior, final answer behavior, and provider/search behavior unchanged.",
        "Delete local unique_source_urls/ordered_sources/next_source_id loops from pipeline_orchestrator.py.",
    ),
)


def registry_entry(decision_name: str) -> PipelineDecisionRegistryEntry:
    for entry in PIPELINE_DECISION_REGISTRY:
        if entry.decision_name == decision_name:
            return entry
    raise KeyError(decision_name)


__all__ = [
    "FINAL_EVIDENCE_BUNDLE_DECISION",
    "FINAL_EVIDENCE_OWNERSHIP_BLUEPRINT",
    "FINAL_EVIDENCE_REPLACEMENT_CONTRACT",
    "NEXT_EXTRACTION_PHASE",
    "NEXT_EXTRACTION_RECOMMENDATION",
    "PIPELINE_DECISION_REGISTRY",
    "PROTECTED_FINAL_EVIDENCE_SURFACES",
    "SOURCE_ID_ASSIGNMENT_DECISION",
    "FinalEvidenceOwnershipResponsibility",
    "FinalEvidenceReplacementContract",
    "PipelineDecisionRegistryEntry",
    "registry_entry",
]
