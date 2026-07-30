"""Strict owner-specific authorization and policy identity contracts.

This module contains no provider defaults, no broker access, and no execution
logic.  It turns an explicit future live addendum into typed, deterministic
authority and rejects every missing, unknown, or mismatched condition.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.evaluation.model_origination_evaluation_reporting import (
    EVALUATION_REPORT_SCHEMA_VERSION,
)
from scripts.evaluation.model_origination_experiment_authority import (
    EXPERIMENT_AUTHORITY_SCHEMA_VERSION,
)
from scripts.evaluation.search_planner_mechanical_validation import (
    MECHANICAL_VALIDATOR_SCHEMA_VERSION,
)
from scripts.evaluation.search_planner_product_boundary_observer import (
    CANONICAL_PRODUCT_BOUNDARY_VERSION,
)
from scripts.evaluation.search_planner_prompt_variant import (
    PROMPT_VARIANT_CONTRACT_VERSION,
    PromptVariantSpecification,
)
from scripts.evaluation.search_planner_semantic_judgment import (
    SEMANTIC_JUDGMENT_CONTRACT_VERSION,
    EssentialRequirement,
)

OWNER_SPECIFIC_AUTHORIZATION_SCHEMA_VERSION = (
    "search_planner_owner_specific_live_authorization_v1"
)
SCENARIO_PACKET_SCHEMA_VERSION = (
    "search_planner_owner_specific_scenario_packet_v1"
)
SEMANTIC_REQUIREMENT_PACKET_SCHEMA_VERSION = (
    "search_planner_semantic_requirement_packet_v1"
)
CANONICAL_POLICY_PACKET_SCHEMA_VERSION = (
    "search_planner_owner_specific_policy_packet_v1"
)
POLICY_CANONICALIZATION_VERSION = (
    "canonical_json_utf8_sorted_keys_no_whitespace_v1"
)
TRIAL_SCHEDULE_SCHEMA_VERSION = (
    "search_planner_owner_specific_trial_schedule_v1"
)
OWNER_SPECIFIC_ORCHESTRATOR_VERSION = (
    "search_planner_owner_specific_orchestrator_v1"
)
SEMANTIC_EXECUTION_OBSERVATION_VERSION = (
    "search_planner_semantic_judge_execution_observation_v1"
)
BLINDING_POLICY_IDENTITY = (
    "independent_blinded_primary_adversarial_v1"
)
OUTCOME_METRIC = "semantic_met_binary_v1"
STOCHASTIC_ATTRIBUTION_CEILING = "ASSOCIATION_ONLY"
EVALUATION_KIND = "search_planner_owner_specific_prompt_comparison"
RETENTION_POSTURE = "sanitized_only"
PLANNER_ROLE = "search_planner"
SEMANTIC_JUDGE_ROLE = "search_planner_semantic_judge"
GENERIC_BROKER_TRANSPORT_FACTORY_SPEC = (
    "scripts.evaluation.brokered_model_origination_transport:"
    "create_brokered_model_route_transport"
)

_DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")
_GIT_SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
_MODE_VALUES = frozenset({"Fast", "Balanced", "Deep"})
_REQUIREMENT_KINDS = frozenset(
    {"FACT", "RELATIONSHIP", "AUTHORITY", "ANSWER_CAPABILITY", "OTHER"}
)
_FORBIDDEN_AUTHORIZATION_KEYS = frozenset(
    {
        "api_key",
        "authorization_header",
        "broker_session_token",
        "chain_of_thought",
        "credential",
        "credentials",
        "full_prompt",
        "model_response",
        "private_log",
        "provider_payload",
        "raw_model_output",
        "raw_model_response",
        "raw_planner_input",
        "raw_prompt",
        "raw_provider_payload",
        "reasoning_trace",
        "secret",
        "session_token",
        "token_value",
        "user_query_text",
    }
)
_FORBIDDEN_SCENARIO_KEYS = frozenset(
    {
        "answer_key",
        "expected_answer",
        "expected_component_ids",
        "fixture_aliases",
        "model_response",
        "planner_response",
        "raw_model_output",
        "teacher_answer",
        "teacher_ids",
        "teacher_labels",
        "teacher_payload",
    }
)


class OwnerSpecificAuthorizationError(ValueError):
    """Raised before transport creation for an unlawful addendum or packet."""


def canonical_json_bytes(value: Any) -> bytes:
    """Return the repository-owned deterministic policy encoding."""

    try:
        rendered = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise OwnerSpecificAuthorizationError(
            "canonical material is not finite JSON"
        ) from exc
    return rendered.encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return sha256(canonical_json_bytes(value)).hexdigest()


def text_sha256(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def load_json_object(path: Path) -> dict[str, Any]:
    """Read one strict JSON object and reject JSON's non-finite extensions."""

    def reject_constant(value: str) -> None:
        raise OwnerSpecificAuthorizationError(
            f"non-finite JSON value is forbidden: {value}"
        )

    try:
        parsed = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=reject_constant,
        )
    except OwnerSpecificAuthorizationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OwnerSpecificAuthorizationError(
            f"could not read one strict JSON object: {type(exc).__name__}"
        ) from exc
    if not isinstance(parsed, Mapping):
        raise OwnerSpecificAuthorizationError(
            "authorization input must be one JSON object"
        )
    return dict(parsed)


def normalize_repository_relative_path(
    value: str,
    *,
    label: str,
    repository_root: Path,
    require_output_local: bool = False,
) -> str:
    text = _strict_text(value, label, maximum=1000)
    root = repository_root.resolve()
    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        relative = candidate.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise OwnerSpecificAuthorizationError(
            f"{label} must remain inside the repository"
        ) from exc
    normalized = relative.as_posix()
    if not normalized or normalized == ".":
        raise OwnerSpecificAuthorizationError(
            f"{label} must identify one repository file"
        )
    if require_output_local and not normalized.startswith("output/local/"):
        raise OwnerSpecificAuthorizationError(
            f"{label} must remain under output/local"
        )
    return normalized


@dataclass(frozen=True, slots=True)
class ScenarioPacketIdentity:
    schema_version: str
    scenario_id: str
    scenario_packet_path: str
    scenario_packet_sha256: str

    def __post_init__(self) -> None:
        if self.schema_version != SCENARIO_PACKET_SCHEMA_VERSION:
            raise OwnerSpecificAuthorizationError(
                "scenario identity schema version is unsupported"
            )
        _strict_text(self.scenario_id, "scenario_id", maximum=160)
        _strict_text(
            self.scenario_packet_path,
            "scenario_packet_path",
            maximum=1000,
        )
        _strict_digest(
            self.scenario_packet_sha256,
            "scenario_packet_sha256",
        )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> "ScenarioPacketIdentity":
        raw = _exact_mapping(
            value,
            (
                "schema_version",
                "scenario_id",
                "scenario_packet_path",
                "scenario_packet_sha256",
            ),
            "scenario_packet_identity",
        )
        return cls(
            schema_version=_strict_text(
                raw["schema_version"],
                "scenario identity schema_version",
            ),
            scenario_id=_strict_text(raw["scenario_id"], "scenario_id"),
            scenario_packet_path=_strict_text(
                raw["scenario_packet_path"],
                "scenario_packet_path",
            ),
            scenario_packet_sha256=_strict_digest(
                raw["scenario_packet_sha256"],
                "scenario_packet_sha256",
            ),
        )

    def to_packet(self) -> dict[str, Any]:
        self.__post_init__()
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EvaluationIdentityAuthorization:
    schema_version: str
    reference: str
    repository_sha: str
    scenario_id: str
    evaluation_kind: str
    decision: str
    stop_condition: str
    output_packet_path: str
    retention_posture: str
    live_addendum_path: str
    scenario_packet_path: str
    transport_factory_spec: str
    canonical_operator_command: str = field(repr=False)
    canonical_operator_command_digest: str

    def __post_init__(self) -> None:
        if self.schema_version != OWNER_SPECIFIC_AUTHORIZATION_SCHEMA_VERSION:
            raise OwnerSpecificAuthorizationError(
                "evaluation identity schema version is unsupported"
            )
        if not _GIT_SHA_PATTERN.fullmatch(self.repository_sha):
            raise OwnerSpecificAuthorizationError(
                "repository_sha must be one lowercase Git object ID"
            )
        for label, value, maximum in (
            ("reference", self.reference, 240),
            ("scenario_id", self.scenario_id, 160),
            ("decision", self.decision, 160),
            ("stop_condition", self.stop_condition, 500),
            ("output_packet_path", self.output_packet_path, 1000),
            ("live_addendum_path", self.live_addendum_path, 1000),
            ("scenario_packet_path", self.scenario_packet_path, 1000),
            ("transport_factory_spec", self.transport_factory_spec, 500),
            (
                "canonical_operator_command",
                self.canonical_operator_command,
                10000,
            ),
        ):
            _strict_text(value, label, maximum=maximum)
        if self.evaluation_kind != EVALUATION_KIND:
            raise OwnerSpecificAuthorizationError(
                "evaluation kind is unsupported"
            )
        if self.retention_posture != RETENTION_POSTURE:
            raise OwnerSpecificAuthorizationError(
                "evaluation retention posture must be sanitized_only"
            )
        if self.transport_factory_spec != GENERIC_BROKER_TRANSPORT_FACTORY_SPEC:
            raise OwnerSpecificAuthorizationError(
                "owner-specific execute must select the generic loopback broker"
            )
        _strict_digest(
            self.canonical_operator_command_digest,
            "canonical_operator_command_digest",
        )
        if self.canonical_operator_command_digest != text_sha256(
            self.canonical_operator_command
        ):
            raise OwnerSpecificAuthorizationError(
                "canonical command digest does not cover the exact command"
            )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> "EvaluationIdentityAuthorization":
        names = (
            "schema_version",
            "reference",
            "repository_sha",
            "scenario_id",
            "evaluation_kind",
            "decision",
            "stop_condition",
            "output_packet_path",
            "retention_posture",
            "live_addendum_path",
            "scenario_packet_path",
            "transport_factory_spec",
            "canonical_operator_command",
            "canonical_operator_command_digest",
        )
        raw = _exact_mapping(value, names, "evaluation_identity")
        return cls(
            **{
                name: _strict_text(
                    raw[name],
                    f"evaluation_identity.{name}",
                    maximum=10000,
                )
                for name in names
            }
        )

    def to_packet(self) -> dict[str, Any]:
        self.__post_init__()
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TrialScheduleEntry:
    trial_id: str
    arm_id: str
    planner_call_id: str
    primary_judge_call_id: str
    adversarial_judge_call_id: str

    def __post_init__(self) -> None:
        for label, value in asdict(self).items():
            _strict_text(value, label, maximum=160)

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> "TrialScheduleEntry":
        names = (
            "trial_id",
            "arm_id",
            "planner_call_id",
            "primary_judge_call_id",
            "adversarial_judge_call_id",
        )
        raw = _exact_mapping(value, names, "trial_schedule_entry")
        return cls(
            **{
                name: _strict_text(
                    raw[name],
                    f"trial_schedule_entry.{name}",
                )
                for name in names
            }
        )


@dataclass(frozen=True, slots=True)
class PromptExperimentAuthorization:
    trial_schedule_schema_version: str
    control_arm_id: str
    variant_arm_id: str
    trial_schedule: tuple[TrialScheduleEntry, ...]
    required_observations_per_arm: int
    design_kind: str
    sampling_policy: str
    randomized_order: bool
    blinded_judging: bool
    outcome_metric: str
    experiment_policy_identity: str
    blinding_policy_identity: str
    stochastic_attribution_ceiling: str
    prompt_variant_specification: PromptVariantSpecification

    def __post_init__(self) -> None:
        if self.trial_schedule_schema_version != TRIAL_SCHEDULE_SCHEMA_VERSION:
            raise OwnerSpecificAuthorizationError(
                "trial schedule schema version is unsupported"
            )
        if self.control_arm_id != self.prompt_variant_specification.control_arm_id:
            raise OwnerSpecificAuthorizationError(
                "control arm differs from the prompt-variant specification"
            )
        if self.variant_arm_id != self.prompt_variant_specification.variant_arm_id:
            raise OwnerSpecificAuthorizationError(
                "variant arm differs from the prompt-variant specification"
            )
        if not self.trial_schedule:
            raise OwnerSpecificAuthorizationError(
                "trial schedule must be nonempty"
            )
        _strict_int(
            self.required_observations_per_arm,
            "required_observations_per_arm",
            minimum=1,
            maximum=100,
        )
        expected_design = (
            "SINGLE_PAIR"
            if self.required_observations_per_arm == 1
            else "RANDOMIZED_REPEATED"
        )
        if self.design_kind != expected_design:
            raise OwnerSpecificAuthorizationError(
                "experiment design kind differs from the schedule size"
            )
        _strict_text(
            self.sampling_policy,
            "sampling_policy",
            maximum=500,
        )
        if not isinstance(self.randomized_order, bool):
            raise OwnerSpecificAuthorizationError(
                "randomized_order must be boolean"
            )
        if self.blinded_judging is not True:
            raise OwnerSpecificAuthorizationError(
                "owner-specific semantic judging must be blinded"
            )
        if (
            self.required_observations_per_arm > 1
            and not self.randomized_order
        ):
            raise OwnerSpecificAuthorizationError(
                "repeated stochastic schedules must be pre-randomized"
            )
        if self.outcome_metric != OUTCOME_METRIC:
            raise OwnerSpecificAuthorizationError(
                "outcome metric is unsupported"
            )
        if self.blinding_policy_identity != BLINDING_POLICY_IDENTITY:
            raise OwnerSpecificAuthorizationError(
                "blinding policy identity is unsupported"
            )
        if (
            self.stochastic_attribution_ceiling
            != STOCHASTIC_ATTRIBUTION_CEILING
        ):
            raise OwnerSpecificAuthorizationError(
                "stochastic attribution ceiling is unsupported"
            )
        if not self.experiment_policy_identity.startswith(
            "owner-specific-policy:"
        ):
            raise OwnerSpecificAuthorizationError(
                "experiment policy identity must bind a canonical policy digest"
            )
        expected_arms = {
            self.control_arm_id,
            self.variant_arm_id,
        }
        observed_arms = [item.arm_id for item in self.trial_schedule]
        if set(observed_arms) != expected_arms:
            raise OwnerSpecificAuthorizationError(
                "trial schedule must contain exactly the authorized arms"
            )
        for arm_id in expected_arms:
            if observed_arms.count(arm_id) != self.required_observations_per_arm:
                raise OwnerSpecificAuthorizationError(
                    "trial schedule arm count differs from the precommitment"
                )
        trial_ids = [item.trial_id for item in self.trial_schedule]
        call_ids = [
            call_id
            for item in self.trial_schedule
            for call_id in (
                item.planner_call_id,
                item.primary_judge_call_id,
                item.adversarial_judge_call_id,
            )
        ]
        if len(trial_ids) != len(set(trial_ids)):
            raise OwnerSpecificAuthorizationError(
                "trial schedule contains a duplicate trial identity"
            )
        if len(call_ids) != len(set(call_ids)):
            raise OwnerSpecificAuthorizationError(
                "trial schedule contains a call-identity collision"
            )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> "PromptExperimentAuthorization":
        names = (
            "trial_schedule_schema_version",
            "control_arm_id",
            "variant_arm_id",
            "trial_schedule",
            "required_observations_per_arm",
            "design_kind",
            "sampling_policy",
            "randomized_order",
            "blinded_judging",
            "outcome_metric",
            "experiment_policy_identity",
            "blinding_policy_identity",
            "stochastic_attribution_ceiling",
            "prompt_variant_specification",
        )
        raw = _exact_mapping(value, names, "prompt_experiment")
        schedule_raw = _strict_sequence(
            raw["trial_schedule"],
            "prompt_experiment.trial_schedule",
        )
        specification_raw = _exact_mapping(
            raw["prompt_variant_specification"],
            (
                "contract_version",
                "control_arm_id",
                "variant_arm_id",
                "variant_instruction_text",
                "variant_instruction_sha256",
                "maximum_instruction_characters",
            ),
            "prompt_variant_specification",
        )
        specification = PromptVariantSpecification(
            contract_version=_strict_text(
                specification_raw["contract_version"],
                "prompt_variant_specification.contract_version",
            ),
            control_arm_id=_strict_text(
                specification_raw["control_arm_id"],
                "prompt_variant_specification.control_arm_id",
            ),
            variant_arm_id=_strict_text(
                specification_raw["variant_arm_id"],
                "prompt_variant_specification.variant_arm_id",
            ),
            variant_instruction_text=_strict_text(
                specification_raw["variant_instruction_text"],
                "prompt_variant_specification.variant_instruction_text",
                maximum=20000,
                preserve=True,
            ),
            variant_instruction_sha256=_strict_digest(
                specification_raw["variant_instruction_sha256"],
                "prompt_variant_specification.variant_instruction_sha256",
            ),
            maximum_instruction_characters=_strict_int(
                specification_raw["maximum_instruction_characters"],
                "prompt_variant_specification.maximum_instruction_characters",
                minimum=1,
                maximum=20000,
            ),
        )
        return cls(
            trial_schedule_schema_version=_strict_text(
                raw["trial_schedule_schema_version"],
                "prompt_experiment.trial_schedule_schema_version",
            ),
            control_arm_id=_strict_text(
                raw["control_arm_id"],
                "prompt_experiment.control_arm_id",
            ),
            variant_arm_id=_strict_text(
                raw["variant_arm_id"],
                "prompt_experiment.variant_arm_id",
            ),
            trial_schedule=tuple(
                TrialScheduleEntry.from_mapping(item)
                for item in schedule_raw
            ),
            required_observations_per_arm=_strict_int(
                raw["required_observations_per_arm"],
                "prompt_experiment.required_observations_per_arm",
                minimum=1,
                maximum=100,
            ),
            design_kind=_strict_text(
                raw["design_kind"],
                "prompt_experiment.design_kind",
            ),
            sampling_policy=_strict_text(
                raw["sampling_policy"],
                "prompt_experiment.sampling_policy",
                maximum=500,
            ),
            randomized_order=_strict_bool(
                raw["randomized_order"],
                "prompt_experiment.randomized_order",
            ),
            blinded_judging=_strict_bool(
                raw["blinded_judging"],
                "prompt_experiment.blinded_judging",
            ),
            outcome_metric=_strict_text(
                raw["outcome_metric"],
                "prompt_experiment.outcome_metric",
            ),
            experiment_policy_identity=_strict_text(
                raw["experiment_policy_identity"],
                "prompt_experiment.experiment_policy_identity",
            ),
            blinding_policy_identity=_strict_text(
                raw["blinding_policy_identity"],
                "prompt_experiment.blinding_policy_identity",
            ),
            stochastic_attribution_ceiling=_strict_text(
                raw["stochastic_attribution_ceiling"],
                "prompt_experiment.stochastic_attribution_ceiling",
            ),
            prompt_variant_specification=specification,
        )

    def schedule_packet(self) -> dict[str, Any]:
        self.__post_init__()
        return {
            "schema_version": self.trial_schedule_schema_version,
            "entries": [asdict(item) for item in self.trial_schedule],
            "required_observations_per_arm": (
                self.required_observations_per_arm
            ),
            "design_kind": self.design_kind,
            "sampling_policy": self.sampling_policy,
            "randomized_order": self.randomized_order,
            "blinded_judging": self.blinded_judging,
        }

    def safe_packet(self) -> dict[str, Any]:
        """Return authorization facts without the variant instruction text."""

        self.__post_init__()
        return {
            "trial_schedule_schema_version": (
                self.trial_schedule_schema_version
            ),
            "control_arm_id": self.control_arm_id,
            "variant_arm_id": self.variant_arm_id,
            "trial_schedule": [
                asdict(item) for item in self.trial_schedule
            ],
            "required_observations_per_arm": (
                self.required_observations_per_arm
            ),
            "design_kind": self.design_kind,
            "sampling_policy": self.sampling_policy,
            "randomized_order": self.randomized_order,
            "blinded_judging": self.blinded_judging,
            "outcome_metric": self.outcome_metric,
            "experiment_policy_identity": self.experiment_policy_identity,
            "blinding_policy_identity": self.blinding_policy_identity,
            "stochastic_attribution_ceiling": (
                self.stochastic_attribution_ceiling
            ),
            "prompt_variant_specification": {
                "contract_version": (
                    self.prompt_variant_specification.contract_version
                ),
                "control_arm_id": (
                    self.prompt_variant_specification.control_arm_id
                ),
                "variant_arm_id": (
                    self.prompt_variant_specification.variant_arm_id
                ),
                "variant_instruction_sha256": (
                    self.prompt_variant_specification.variant_instruction_sha256
                ),
                "maximum_instruction_characters": (
                    self.prompt_variant_specification.maximum_instruction_characters
                ),
                "variant_instruction_retained": False,
            },
        }

    def to_packet(self) -> dict[str, Any]:
        self.__post_init__()
        return {
            **self.safe_packet(),
            "prompt_variant_specification": {
                "contract_version": (
                    self.prompt_variant_specification.contract_version
                ),
                "control_arm_id": (
                    self.prompt_variant_specification.control_arm_id
                ),
                "variant_arm_id": (
                    self.prompt_variant_specification.variant_arm_id
                ),
                "variant_instruction_text": (
                    self.prompt_variant_specification.variant_instruction_text
                ),
                "variant_instruction_sha256": (
                    self.prompt_variant_specification.variant_instruction_sha256
                ),
                "maximum_instruction_characters": (
                    self.prompt_variant_specification.maximum_instruction_characters
                ),
            },
        }


@dataclass(frozen=True, slots=True)
class PlannerRouteAuthorization:
    role: str
    provider: str
    model: str
    reasoning_effort: str
    maximum_input_tokens: int
    maximum_output_tokens: int
    timeout_seconds: int
    retry_cap: int
    per_call_cost_ceiling_usd: str
    maximum_planner_calls: int

    def __post_init__(self) -> None:
        if self.role != PLANNER_ROLE:
            raise OwnerSpecificAuthorizationError(
                "Planner route role is invalid"
            )
        _validate_route_common(self)
        _strict_int(
            self.maximum_planner_calls,
            "maximum_planner_calls",
            minimum=1,
            maximum=100,
        )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> "PlannerRouteAuthorization":
        names = (
            "role",
            "provider",
            "model",
            "reasoning_effort",
            "maximum_input_tokens",
            "maximum_output_tokens",
            "timeout_seconds",
            "retry_cap",
            "per_call_cost_ceiling_usd",
            "maximum_planner_calls",
        )
        raw = _exact_mapping(value, names, "planner_route")
        return cls(
            **_parse_route_fields(
                raw,
                count_fields=("maximum_planner_calls",),
            )
        )

    def to_packet(self) -> dict[str, Any]:
        self.__post_init__()
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SemanticJudgeRouteAuthorization:
    role: str
    provider: str
    model: str
    reasoning_effort: str
    maximum_input_tokens: int
    maximum_output_tokens: int
    timeout_seconds: int
    retry_cap: int
    per_call_cost_ceiling_usd: str
    maximum_primary_judge_calls: int
    maximum_adversarial_judge_calls: int

    def __post_init__(self) -> None:
        if self.role != SEMANTIC_JUDGE_ROLE:
            raise OwnerSpecificAuthorizationError(
                "semantic-judge route role is invalid"
            )
        _validate_route_common(self)
        _strict_int(
            self.maximum_primary_judge_calls,
            "maximum_primary_judge_calls",
            minimum=1,
            maximum=100,
        )
        _strict_int(
            self.maximum_adversarial_judge_calls,
            "maximum_adversarial_judge_calls",
            minimum=1,
            maximum=100,
        )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> "SemanticJudgeRouteAuthorization":
        names = (
            "role",
            "provider",
            "model",
            "reasoning_effort",
            "maximum_input_tokens",
            "maximum_output_tokens",
            "timeout_seconds",
            "retry_cap",
            "per_call_cost_ceiling_usd",
            "maximum_primary_judge_calls",
            "maximum_adversarial_judge_calls",
        )
        raw = _exact_mapping(value, names, "semantic_judge_route")
        return cls(
            **_parse_route_fields(
                raw,
                count_fields=(
                    "maximum_primary_judge_calls",
                    "maximum_adversarial_judge_calls",
                ),
            )
        )

    def to_packet(self) -> dict[str, Any]:
        self.__post_init__()
        return asdict(self)


@dataclass(frozen=True, slots=True)
class WholeEvaluationCaps:
    maximum_planner_boundary_runs: int
    maximum_total_broker_calls: int
    maximum_total_observed_cost_usd: str
    maximum_wall_clock_seconds: int

    def __post_init__(self) -> None:
        _strict_int(
            self.maximum_planner_boundary_runs,
            "maximum_planner_boundary_runs",
            minimum=1,
            maximum=100,
        )
        _strict_int(
            self.maximum_total_broker_calls,
            "maximum_total_broker_calls",
            minimum=1,
            maximum=300,
        )
        _positive_decimal(
            self.maximum_total_observed_cost_usd,
            "maximum_total_observed_cost_usd",
        )
        _strict_int(
            self.maximum_wall_clock_seconds,
            "maximum_wall_clock_seconds",
            minimum=1,
            maximum=86400,
        )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> "WholeEvaluationCaps":
        names = (
            "maximum_planner_boundary_runs",
            "maximum_total_broker_calls",
            "maximum_total_observed_cost_usd",
            "maximum_wall_clock_seconds",
        )
        raw = _exact_mapping(value, names, "whole_evaluation_caps")
        return cls(
            maximum_planner_boundary_runs=_strict_int(
                raw["maximum_planner_boundary_runs"],
                "whole_evaluation_caps.maximum_planner_boundary_runs",
                minimum=1,
                maximum=100,
            ),
            maximum_total_broker_calls=_strict_int(
                raw["maximum_total_broker_calls"],
                "whole_evaluation_caps.maximum_total_broker_calls",
                minimum=1,
                maximum=300,
            ),
            maximum_total_observed_cost_usd=_strict_decimal_text(
                raw["maximum_total_observed_cost_usd"],
                "whole_evaluation_caps.maximum_total_observed_cost_usd",
            ),
            maximum_wall_clock_seconds=_strict_int(
                raw["maximum_wall_clock_seconds"],
                "whole_evaluation_caps.maximum_wall_clock_seconds",
                minimum=1,
                maximum=86400,
            ),
        )

    def to_packet(self) -> dict[str, Any]:
        self.__post_init__()
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    store: bool
    background: bool
    retained_live_artifacts: bool
    retain_raw_prompts: bool
    retain_raw_outputs: bool
    retain_query_text: bool

    def __post_init__(self) -> None:
        if any(asdict(self).values()):
            raise OwnerSpecificAuthorizationError(
                "owner-specific execution requires every retention flag false"
            )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> "RetentionPolicy":
        names = (
            "store",
            "background",
            "retained_live_artifacts",
            "retain_raw_prompts",
            "retain_raw_outputs",
            "retain_query_text",
        )
        raw = _exact_mapping(value, names, "retention_policy")
        return cls(
            **{
                name: _strict_bool(
                    raw[name],
                    f"retention_policy.{name}",
                )
                for name in names
            }
        )

    def to_packet(self) -> dict[str, Any]:
        self.__post_init__()
        return asdict(self)


@dataclass(frozen=True, slots=True)
class InstalledOwnerIdentities:
    product_boundary_version: str
    mechanical_validator_version: str
    semantic_contract_version: str
    experiment_authority_version: str
    report_schema_version: str
    prompt_variant_contract_version: str
    orchestrator_version: str
    semantic_execution_observation_version: str

    def __post_init__(self) -> None:
        expected = {
            "product_boundary_version": CANONICAL_PRODUCT_BOUNDARY_VERSION,
            "mechanical_validator_version": (
                MECHANICAL_VALIDATOR_SCHEMA_VERSION
            ),
            "semantic_contract_version": (
                SEMANTIC_JUDGMENT_CONTRACT_VERSION
            ),
            "experiment_authority_version": (
                EXPERIMENT_AUTHORITY_SCHEMA_VERSION
            ),
            "report_schema_version": EVALUATION_REPORT_SCHEMA_VERSION,
            "prompt_variant_contract_version": (
                PROMPT_VARIANT_CONTRACT_VERSION
            ),
            "orchestrator_version": OWNER_SPECIFIC_ORCHESTRATOR_VERSION,
            "semantic_execution_observation_version": (
                SEMANTIC_EXECUTION_OBSERVATION_VERSION
            ),
        }
        for field_name, expected_value in expected.items():
            if getattr(self, field_name) != expected_value:
                raise OwnerSpecificAuthorizationError(
                    f"installed owner identity mismatch: {field_name}"
                )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> "InstalledOwnerIdentities":
        names = (
            "product_boundary_version",
            "mechanical_validator_version",
            "semantic_contract_version",
            "experiment_authority_version",
            "report_schema_version",
            "prompt_variant_contract_version",
            "orchestrator_version",
            "semantic_execution_observation_version",
        )
        raw = _exact_mapping(value, names, "owner_identities")
        return cls(
            **{
                name: _strict_text(
                    raw[name],
                    f"owner_identities.{name}",
                )
                for name in names
            }
        )

    def to_packet(self) -> dict[str, Any]:
        self.__post_init__()
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SemanticRequirementPacket:
    schema_version: str
    reference: str
    scenario_id: str
    essential_requirements: tuple[EssentialRequirement, ...]
    essential_architecture_constraints: tuple[str, ...]
    prohibited_upgrades_or_shortcuts: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.schema_version != SEMANTIC_REQUIREMENT_PACKET_SCHEMA_VERSION:
            raise OwnerSpecificAuthorizationError(
                "semantic requirement packet schema is unsupported"
            )
        _strict_text(self.reference, "semantic requirement reference")
        _strict_text(self.scenario_id, "semantic requirement scenario_id")
        if not self.essential_requirements:
            raise OwnerSpecificAuthorizationError(
                "semantic requirement packet must be nonempty"
            )
        ids = [
            item.requirement_id for item in self.essential_requirements
        ]
        if len(ids) != len(set(ids)):
            raise OwnerSpecificAuthorizationError(
                "semantic requirement identities must be unique"
            )
        kinds = {
            item.requirement_kind for item in self.essential_requirements
        }
        if "ANSWER_CAPABILITY" not in kinds:
            raise OwnerSpecificAuthorizationError(
                "semantic requirements need an answer-capability requirement"
            )
        for label, values in (
            (
                "essential_architecture_constraints",
                self.essential_architecture_constraints,
            ),
            (
                "prohibited_upgrades_or_shortcuts",
                self.prohibited_upgrades_or_shortcuts,
            ),
        ):
            if not values:
                raise OwnerSpecificAuthorizationError(
                    f"{label} must be explicit"
                )
            if len(values) != len(set(values)):
                raise OwnerSpecificAuthorizationError(
                    f"{label} must be stable and unique"
                )
            for item in values:
                _strict_text(item, label, maximum=1000)

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> "SemanticRequirementPacket":
        names = (
            "schema_version",
            "reference",
            "scenario_id",
            "essential_requirements",
            "essential_architecture_constraints",
            "prohibited_upgrades_or_shortcuts",
        )
        raw = _exact_mapping(
            value,
            names,
            "semantic_requirement_packet",
        )
        requirement_values = _strict_sequence(
            raw["essential_requirements"],
            "semantic_requirement_packet.essential_requirements",
        )
        requirements: list[EssentialRequirement] = []
        for item in requirement_values:
            requirement = _exact_mapping(
                item,
                (
                    "requirement_id",
                    "normalized_requirement",
                    "requirement_kind",
                ),
                "essential_requirement",
            )
            kind = _strict_text(
                requirement["requirement_kind"],
                "essential_requirement.requirement_kind",
            )
            if kind not in _REQUIREMENT_KINDS:
                raise OwnerSpecificAuthorizationError(
                    "essential requirement kind is unsupported"
                )
            requirements.append(
                EssentialRequirement(
                    requirement_id=_strict_text(
                        requirement["requirement_id"],
                        "essential_requirement.requirement_id",
                    ),
                    normalized_requirement=_strict_text(
                        requirement["normalized_requirement"],
                        "essential_requirement.normalized_requirement",
                        maximum=1000,
                    ),
                    requirement_kind=kind,
                )
            )
        return cls(
            schema_version=_strict_text(
                raw["schema_version"],
                "semantic_requirement_packet.schema_version",
            ),
            reference=_strict_text(
                raw["reference"],
                "semantic_requirement_packet.reference",
            ),
            scenario_id=_strict_text(
                raw["scenario_id"],
                "semantic_requirement_packet.scenario_id",
            ),
            essential_requirements=tuple(requirements),
            essential_architecture_constraints=_strict_text_tuple(
                raw["essential_architecture_constraints"],
                "semantic_requirement_packet.essential_architecture_constraints",
            ),
            prohibited_upgrades_or_shortcuts=_strict_text_tuple(
                raw["prohibited_upgrades_or_shortcuts"],
                "semantic_requirement_packet.prohibited_upgrades_or_shortcuts",
            ),
        )

    def to_packet(self) -> dict[str, Any]:
        self.__post_init__()
        return {
            "schema_version": self.schema_version,
            "reference": self.reference,
            "scenario_id": self.scenario_id,
            "essential_requirements": [
                asdict(item) for item in self.essential_requirements
            ],
            "essential_architecture_constraints": list(
                self.essential_architecture_constraints
            ),
            "prohibited_upgrades_or_shortcuts": list(
                self.prohibited_upgrades_or_shortcuts
            ),
        }


@dataclass(frozen=True, slots=True)
class CanonicalExperimentPolicyPacket:
    schema_version: str
    semantic_judge_route_identity_sha256: str
    semantic_requirement_packet_sha256: str
    outcome_metric: str
    trial_schedule_sha256: str
    prompt_variant_contract_version: str
    orchestrator_version: str
    semantic_judge_execution_observation_version: str
    blinding_policy_identity: str
    stochastic_attribution_ceiling: str
    canonicalization_version: str

    def __post_init__(self) -> None:
        if self.schema_version != CANONICAL_POLICY_PACKET_SCHEMA_VERSION:
            raise OwnerSpecificAuthorizationError(
                "canonical policy schema version is unsupported"
            )
        for label in (
            "semantic_judge_route_identity_sha256",
            "semantic_requirement_packet_sha256",
            "trial_schedule_sha256",
        ):
            _strict_digest(getattr(self, label), label)
        expected = {
            "outcome_metric": OUTCOME_METRIC,
            "prompt_variant_contract_version": (
                PROMPT_VARIANT_CONTRACT_VERSION
            ),
            "orchestrator_version": OWNER_SPECIFIC_ORCHESTRATOR_VERSION,
            "semantic_judge_execution_observation_version": (
                SEMANTIC_EXECUTION_OBSERVATION_VERSION
            ),
            "blinding_policy_identity": BLINDING_POLICY_IDENTITY,
            "stochastic_attribution_ceiling": (
                STOCHASTIC_ATTRIBUTION_CEILING
            ),
            "canonicalization_version": POLICY_CANONICALIZATION_VERSION,
        }
        for field_name, expected_value in expected.items():
            if getattr(self, field_name) != expected_value:
                raise OwnerSpecificAuthorizationError(
                    f"canonical policy field mismatch: {field_name}"
                )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> "CanonicalExperimentPolicyPacket":
        names = (
            "schema_version",
            "semantic_judge_route_identity_sha256",
            "semantic_requirement_packet_sha256",
            "outcome_metric",
            "trial_schedule_sha256",
            "prompt_variant_contract_version",
            "orchestrator_version",
            "semantic_judge_execution_observation_version",
            "blinding_policy_identity",
            "stochastic_attribution_ceiling",
            "canonicalization_version",
        )
        raw = _exact_mapping(
            value,
            names,
            "canonical_policy_packet",
        )
        return cls(
            **{
                name: _strict_text(
                    raw[name],
                    f"canonical_policy_packet.{name}",
                )
                for name in names
            }
        )

    def to_packet(self) -> dict[str, Any]:
        self.__post_init__()
        return asdict(self)

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.to_packet())

    @property
    def authority_policy(self) -> str:
        return f"owner-specific-policy:{self.sha256}"


@dataclass(frozen=True, slots=True)
class OwnerSpecificLiveAuthorization:
    schema_version: str
    evaluation_identity: EvaluationIdentityAuthorization
    scenario_packet_identity: ScenarioPacketIdentity
    prompt_experiment: PromptExperimentAuthorization
    planner_route: PlannerRouteAuthorization
    semantic_judge_route: SemanticJudgeRouteAuthorization
    whole_evaluation_caps: WholeEvaluationCaps
    retention_policy: RetentionPolicy
    owner_identities: InstalledOwnerIdentities
    semantic_requirement_packet: SemanticRequirementPacket
    canonical_policy_packet: CanonicalExperimentPolicyPacket
    policy_packet_sha256: str
    authority_policy: str

    def __post_init__(self) -> None:
        if self.schema_version != OWNER_SPECIFIC_AUTHORIZATION_SCHEMA_VERSION:
            raise OwnerSpecificAuthorizationError(
                "owner-specific authorization schema is unsupported"
            )
        _strict_digest(
            self.policy_packet_sha256,
            "policy_packet_sha256",
        )
        if self.policy_packet_sha256 != self.canonical_policy_packet.sha256:
            raise OwnerSpecificAuthorizationError(
                "canonical policy digest differs from the retained packet"
            )
        expected_authority_policy = (
            f"owner-specific-policy:{self.policy_packet_sha256}"
        )
        if (
            self.authority_policy != expected_authority_policy
            or self.prompt_experiment.experiment_policy_identity
            != expected_authority_policy
        ):
            raise OwnerSpecificAuthorizationError(
                "authority_policy does not bind the canonical policy digest"
            )
        if (
            self.evaluation_identity.scenario_id
            != self.scenario_packet_identity.scenario_id
            or self.semantic_requirement_packet.scenario_id
            != self.scenario_packet_identity.scenario_id
        ):
            raise OwnerSpecificAuthorizationError(
                "scenario identity differs across authorization owners"
            )
        expected_policy = build_canonical_policy_packet(
            semantic_judge_route=self.semantic_judge_route,
            requirement_packet=self.semantic_requirement_packet,
            prompt_experiment=self.prompt_experiment,
            owner_identities=self.owner_identities,
        )
        if (
            self.canonical_policy_packet.to_packet()
            != expected_policy.to_packet()
        ):
            raise OwnerSpecificAuthorizationError(
                "canonical policy packet differs from authorization conditions"
            )
        _validate_schedule_caps(self)
        _reject_forbidden_keys(
            self.to_packet(),
            forbidden=_FORBIDDEN_AUTHORIZATION_KEYS,
            label="authorization",
        )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> "OwnerSpecificLiveAuthorization":
        names = (
            "schema_version",
            "evaluation_identity",
            "scenario_packet_identity",
            "prompt_experiment",
            "planner_route",
            "semantic_judge_route",
            "whole_evaluation_caps",
            "retention_policy",
            "owner_identities",
            "semantic_requirement_packet",
            "canonical_policy_packet",
            "policy_packet_sha256",
            "authority_policy",
        )
        raw = _exact_mapping(value, names, "authorization")
        authorization = cls(
            schema_version=_strict_text(
                raw["schema_version"],
                "authorization.schema_version",
            ),
            evaluation_identity=(
                EvaluationIdentityAuthorization.from_mapping(
                    _strict_mapping(
                        raw["evaluation_identity"],
                        "authorization.evaluation_identity",
                    )
                )
            ),
            scenario_packet_identity=ScenarioPacketIdentity.from_mapping(
                _strict_mapping(
                    raw["scenario_packet_identity"],
                    "authorization.scenario_packet_identity",
                )
            ),
            prompt_experiment=PromptExperimentAuthorization.from_mapping(
                _strict_mapping(
                    raw["prompt_experiment"],
                    "authorization.prompt_experiment",
                )
            ),
            planner_route=PlannerRouteAuthorization.from_mapping(
                _strict_mapping(
                    raw["planner_route"],
                    "authorization.planner_route",
                )
            ),
            semantic_judge_route=(
                SemanticJudgeRouteAuthorization.from_mapping(
                    _strict_mapping(
                        raw["semantic_judge_route"],
                        "authorization.semantic_judge_route",
                    )
                )
            ),
            whole_evaluation_caps=WholeEvaluationCaps.from_mapping(
                _strict_mapping(
                    raw["whole_evaluation_caps"],
                    "authorization.whole_evaluation_caps",
                )
            ),
            retention_policy=RetentionPolicy.from_mapping(
                _strict_mapping(
                    raw["retention_policy"],
                    "authorization.retention_policy",
                )
            ),
            owner_identities=InstalledOwnerIdentities.from_mapping(
                _strict_mapping(
                    raw["owner_identities"],
                    "authorization.owner_identities",
                )
            ),
            semantic_requirement_packet=(
                SemanticRequirementPacket.from_mapping(
                    _strict_mapping(
                        raw["semantic_requirement_packet"],
                        "authorization.semantic_requirement_packet",
                    )
                )
            ),
            canonical_policy_packet=(
                CanonicalExperimentPolicyPacket.from_mapping(
                    _strict_mapping(
                        raw["canonical_policy_packet"],
                        "authorization.canonical_policy_packet",
                    )
                )
            ),
            policy_packet_sha256=_strict_digest(
                raw["policy_packet_sha256"],
                "authorization.policy_packet_sha256",
            ),
            authority_policy=_strict_text(
                raw["authority_policy"],
                "authorization.authority_policy",
            ),
        )
        authorization.__post_init__()
        return authorization

    def to_packet(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "evaluation_identity": self.evaluation_identity.to_packet(),
            "scenario_packet_identity": (
                self.scenario_packet_identity.to_packet()
            ),
            "prompt_experiment": self.prompt_experiment.to_packet(),
            "planner_route": self.planner_route.to_packet(),
            "semantic_judge_route": (
                self.semantic_judge_route.to_packet()
            ),
            "whole_evaluation_caps": (
                self.whole_evaluation_caps.to_packet()
            ),
            "retention_policy": self.retention_policy.to_packet(),
            "owner_identities": self.owner_identities.to_packet(),
            "semantic_requirement_packet": (
                self.semantic_requirement_packet.to_packet()
            ),
            "canonical_policy_packet": (
                self.canonical_policy_packet.to_packet()
            ),
            "policy_packet_sha256": self.policy_packet_sha256,
            "authority_policy": self.authority_policy,
        }

    @property
    def authorization_sha256(self) -> str:
        return canonical_sha256(self.to_packet())


@dataclass(frozen=True, slots=True)
class OwnerSpecificScenarioPacket:
    schema_version: str
    scenario_id: str
    fictional_scenario: bool
    normalized_fictional_user_request: str = field(
        repr=False,
        compare=False,
    )
    requested_mode: str
    current_date: str
    focus_academic: bool
    force_intent_news: bool
    include_domains: tuple[str, ...]
    exclude_domains: tuple[str, ...]
    news_preferred_domains: tuple[str, ...]
    router_input: Mapping[str, Any]
    route_projection: Mapping[str, Any]
    run_contract_projection: Mapping[str, Any]
    supplied_context: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.schema_version != SCENARIO_PACKET_SCHEMA_VERSION:
            raise OwnerSpecificAuthorizationError(
                "scenario packet schema version is unsupported"
            )
        _strict_text(self.scenario_id, "scenario_id", maximum=160)
        if self.fictional_scenario is not True:
            raise OwnerSpecificAuthorizationError(
                "owner-specific evaluation requires a fictional scenario"
            )
        _strict_text(
            self.normalized_fictional_user_request,
            "normalized_fictional_user_request",
            maximum=4000,
            preserve=True,
        )
        if self.requested_mode not in _MODE_VALUES:
            raise OwnerSpecificAuthorizationError(
                "scenario requested_mode is unsupported"
            )
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", self.current_date):
            raise OwnerSpecificAuthorizationError(
                "scenario current_date must be YYYY-MM-DD"
            )
        for label, value in (
            ("focus_academic", self.focus_academic),
            ("force_intent_news", self.force_intent_news),
        ):
            _strict_bool(value, label)
        for label, values in (
            ("include_domains", self.include_domains),
            ("exclude_domains", self.exclude_domains),
            ("news_preferred_domains", self.news_preferred_domains),
        ):
            if len(values) != len(set(values)):
                raise OwnerSpecificAuthorizationError(
                    f"{label} must be stable and unique"
                )
            for item in values:
                _strict_text(item, label, maximum=253)
        _validate_router_input(self.router_input)
        _validate_route_projection(self.route_projection)
        _validate_run_contract_projection(
            self.run_contract_projection
        )
        _reject_forbidden_keys(
            self.to_packet(),
            forbidden=_FORBIDDEN_SCENARIO_KEYS,
            label="scenario packet",
        )
        _reject_forbidden_keys(
            self.to_packet(),
            forbidden=_FORBIDDEN_AUTHORIZATION_KEYS
            - {"user_query_text"},
            label="scenario packet",
        )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> "OwnerSpecificScenarioPacket":
        names = (
            "schema_version",
            "scenario_id",
            "fictional_scenario",
            "normalized_fictional_user_request",
            "requested_mode",
            "current_date",
            "focus_academic",
            "force_intent_news",
            "include_domains",
            "exclude_domains",
            "news_preferred_domains",
            "router_input",
            "route_projection",
            "run_contract_projection",
            "supplied_context",
        )
        raw = _exact_mapping(value, names, "scenario_packet")
        packet = cls(
            schema_version=_strict_text(
                raw["schema_version"],
                "scenario_packet.schema_version",
            ),
            scenario_id=_strict_text(
                raw["scenario_id"],
                "scenario_packet.scenario_id",
            ),
            fictional_scenario=_strict_bool(
                raw["fictional_scenario"],
                "scenario_packet.fictional_scenario",
            ),
            normalized_fictional_user_request=_strict_text(
                raw["normalized_fictional_user_request"],
                "scenario_packet.normalized_fictional_user_request",
                maximum=4000,
                preserve=True,
            ),
            requested_mode=_strict_text(
                raw["requested_mode"],
                "scenario_packet.requested_mode",
            ),
            current_date=_strict_text(
                raw["current_date"],
                "scenario_packet.current_date",
            ),
            focus_academic=_strict_bool(
                raw["focus_academic"],
                "scenario_packet.focus_academic",
            ),
            force_intent_news=_strict_bool(
                raw["force_intent_news"],
                "scenario_packet.force_intent_news",
            ),
            include_domains=_strict_text_tuple(
                raw["include_domains"],
                "scenario_packet.include_domains",
                allow_empty=True,
            ),
            exclude_domains=_strict_text_tuple(
                raw["exclude_domains"],
                "scenario_packet.exclude_domains",
                allow_empty=True,
            ),
            news_preferred_domains=_strict_text_tuple(
                raw["news_preferred_domains"],
                "scenario_packet.news_preferred_domains",
                allow_empty=True,
            ),
            router_input=dict(
                _strict_mapping(
                    raw["router_input"],
                    "scenario_packet.router_input",
                )
            ),
            route_projection=dict(
                _strict_mapping(
                    raw["route_projection"],
                    "scenario_packet.route_projection",
                )
            ),
            run_contract_projection=dict(
                _strict_mapping(
                    raw["run_contract_projection"],
                    "scenario_packet.run_contract_projection",
                )
            ),
            supplied_context=dict(
                _strict_mapping(
                    raw["supplied_context"],
                    "scenario_packet.supplied_context",
                )
            ),
        )
        packet.__post_init__()
        return packet

    def to_packet(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "scenario_id": self.scenario_id,
            "fictional_scenario": self.fictional_scenario,
            "normalized_fictional_user_request": (
                self.normalized_fictional_user_request
            ),
            "requested_mode": self.requested_mode,
            "current_date": self.current_date,
            "focus_academic": self.focus_academic,
            "force_intent_news": self.force_intent_news,
            "include_domains": list(self.include_domains),
            "exclude_domains": list(self.exclude_domains),
            "news_preferred_domains": list(
                self.news_preferred_domains
            ),
            "router_input": dict(self.router_input),
            "route_projection": dict(self.route_projection),
            "run_contract_projection": dict(
                self.run_contract_projection
            ),
            "supplied_context": dict(self.supplied_context),
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.to_packet())


def build_canonical_policy_packet(
    *,
    semantic_judge_route: SemanticJudgeRouteAuthorization,
    requirement_packet: SemanticRequirementPacket,
    prompt_experiment: PromptExperimentAuthorization,
    owner_identities: InstalledOwnerIdentities,
) -> CanonicalExperimentPolicyPacket:
    """Bind every shared policy condition into one canonical identity."""

    return CanonicalExperimentPolicyPacket(
        schema_version=CANONICAL_POLICY_PACKET_SCHEMA_VERSION,
        semantic_judge_route_identity_sha256=canonical_sha256(
            semantic_judge_route.to_packet()
        ),
        semantic_requirement_packet_sha256=canonical_sha256(
            requirement_packet.to_packet()
        ),
        outcome_metric=prompt_experiment.outcome_metric,
        trial_schedule_sha256=canonical_sha256(
            prompt_experiment.schedule_packet()
        ),
        prompt_variant_contract_version=(
            owner_identities.prompt_variant_contract_version
        ),
        orchestrator_version=owner_identities.orchestrator_version,
        semantic_judge_execution_observation_version=(
            owner_identities.semantic_execution_observation_version
        ),
        blinding_policy_identity=(
            prompt_experiment.blinding_policy_identity
        ),
        stochastic_attribution_ceiling=(
            prompt_experiment.stochastic_attribution_ceiling
        ),
        canonicalization_version=POLICY_CANONICALIZATION_VERSION,
    )


def build_canonical_execute_command(
    *,
    repository_sha: str,
    live_addendum_path: str,
    scenario_packet_path: str,
    output_packet_path: str,
    repository_root: Path,
) -> tuple[tuple[str, ...], str, str]:
    """Build the only accepted non-test execute CLI token sequence."""

    if not _GIT_SHA_PATTERN.fullmatch(
        _strict_text(repository_sha, "repository_sha")
    ):
        raise OwnerSpecificAuthorizationError(
            "repository_sha must be one lowercase Git object ID"
        )
    addendum = normalize_repository_relative_path(
        live_addendum_path,
        label="live addendum path",
        repository_root=repository_root,
    )
    scenario = normalize_repository_relative_path(
        scenario_packet_path,
        label="scenario packet path",
        repository_root=repository_root,
    )
    output = normalize_repository_relative_path(
        output_packet_path,
        label="output packet path",
        repository_root=repository_root,
        require_output_local=True,
    )
    argv = (
        "scripts/evaluation/run_search_planner_owner_specific_evaluation.py",
        "--execution-mode",
        "execute",
        "--repository-sha",
        repository_sha,
        "--live-addendum",
        addendum,
        "--scenario-packet",
        scenario,
        "--output",
        output,
    )
    command = json.dumps(
        list(argv),
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return argv, command, text_sha256(command)


def validate_authorization_context(
    authorization: OwnerSpecificLiveAuthorization,
    *,
    scenario_packet: OwnerSpecificScenarioPacket,
    repository_sha: str,
    live_addendum_path: str,
    scenario_packet_path: str,
    output_packet_path: str,
    actual_argv: Sequence[str],
    repository_root: Path,
) -> None:
    """Validate all runtime-bound authority before any transport exists."""

    authorization.__post_init__()
    scenario_packet.__post_init__()
    identity = authorization.evaluation_identity
    scenario_identity = authorization.scenario_packet_identity
    if repository_sha != identity.repository_sha:
        raise OwnerSpecificAuthorizationError(
            "authorization repository SHA differs from the exact checkout"
        )
    if (
        scenario_packet.scenario_id != identity.scenario_id
        or scenario_packet.scenario_id != scenario_identity.scenario_id
    ):
        raise OwnerSpecificAuthorizationError(
            "authorization does not license the exact scenario"
        )
    normalized_addendum = normalize_repository_relative_path(
        live_addendum_path,
        label="live addendum path",
        repository_root=repository_root,
    )
    normalized_scenario = normalize_repository_relative_path(
        scenario_packet_path,
        label="scenario packet path",
        repository_root=repository_root,
    )
    normalized_output = normalize_repository_relative_path(
        output_packet_path,
        label="output packet path",
        repository_root=repository_root,
        require_output_local=True,
    )
    if (
        identity.live_addendum_path != normalized_addendum
        or identity.scenario_packet_path != normalized_scenario
        or identity.output_packet_path != normalized_output
        or scenario_identity.scenario_packet_path != normalized_scenario
    ):
        raise OwnerSpecificAuthorizationError(
            "authorization path identity differs from the exact request"
        )
    if scenario_identity.scenario_packet_sha256 != scenario_packet.sha256:
        raise OwnerSpecificAuthorizationError(
            "scenario packet digest differs from the exact authorization"
        )
    expected_argv, command, command_digest = build_canonical_execute_command(
        repository_sha=repository_sha,
        live_addendum_path=normalized_addendum,
        scenario_packet_path=normalized_scenario,
        output_packet_path=normalized_output,
        repository_root=repository_root,
    )
    if tuple(actual_argv) != expected_argv:
        raise OwnerSpecificAuthorizationError(
            "actual CLI invocation differs from the licensed command"
        )
    if (
        identity.canonical_operator_command != command
        or identity.canonical_operator_command_digest != command_digest
    ):
        raise OwnerSpecificAuthorizationError(
            "authorization command identity differs from the exact invocation"
        )
    variant_text = (
        authorization.prompt_experiment.prompt_variant_specification.variant_instruction_text
    )
    if scenario_packet.normalized_fictional_user_request in variant_text:
        raise OwnerSpecificAuthorizationError(
            "variant instruction contains the scenario request"
        )
    serialized_scenario = canonical_json_bytes(
        scenario_packet.to_packet()
    ).decode("utf-8")
    if serialized_scenario in variant_text:
        raise OwnerSpecificAuthorizationError(
            "variant instruction contains the serialized scenario"
        )
    _reject_secret_like_text(variant_text)


def _validate_schedule_caps(
    authorization: OwnerSpecificLiveAuthorization,
) -> None:
    trial_count = len(
        authorization.prompt_experiment.trial_schedule
    )
    planner_route = authorization.planner_route
    judge_route = authorization.semantic_judge_route
    caps = authorization.whole_evaluation_caps
    if planner_route.retry_cap != 0 or judge_route.retry_cap != 0:
        raise OwnerSpecificAuthorizationError(
            "owner-specific routes require exact retry cap zero"
        )
    if planner_route.maximum_planner_calls != trial_count:
        raise OwnerSpecificAuthorizationError(
            "Planner call cap must exactly match the trial schedule"
        )
    if (
        judge_route.maximum_primary_judge_calls != trial_count
        or judge_route.maximum_adversarial_judge_calls != trial_count
    ):
        raise OwnerSpecificAuthorizationError(
            "semantic-judge call caps must exactly match the trial schedule"
        )
    expected_total_calls = trial_count * 3
    if (
        caps.maximum_planner_boundary_runs != trial_count
        or caps.maximum_total_broker_calls != expected_total_calls
    ):
        raise OwnerSpecificAuthorizationError(
            "whole-evaluation call caps differ from the exact schedule"
        )
    worst_case_cost = (
        Decimal(planner_route.per_call_cost_ceiling_usd) * trial_count
        + Decimal(judge_route.per_call_cost_ceiling_usd)
        * trial_count
        * 2
    )
    if Decimal(caps.maximum_total_observed_cost_usd) != worst_case_cost:
        raise OwnerSpecificAuthorizationError(
            "whole-evaluation cost cap must equal the complete maximum budget"
        )


def _validate_route_common(value: Any) -> None:
    for label in ("provider", "model", "reasoning_effort"):
        _strict_text(getattr(value, label), label, maximum=240)
    _strict_int(
        value.maximum_input_tokens,
        "maximum_input_tokens",
        minimum=1,
        maximum=2_000_000,
    )
    _strict_int(
        value.maximum_output_tokens,
        "maximum_output_tokens",
        minimum=1,
        maximum=200_000,
    )
    _strict_int(
        value.timeout_seconds,
        "timeout_seconds",
        minimum=1,
        maximum=600,
    )
    _strict_int(
        value.retry_cap,
        "retry_cap",
        minimum=0,
        maximum=0,
    )
    _positive_decimal(
        value.per_call_cost_ceiling_usd,
        "per_call_cost_ceiling_usd",
    )


def _parse_route_fields(
    raw: Mapping[str, Any],
    *,
    count_fields: Sequence[str],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "role": _strict_text(raw["role"], "route.role"),
        "provider": _strict_text(raw["provider"], "route.provider"),
        "model": _strict_text(raw["model"], "route.model"),
        "reasoning_effort": _strict_text(
            raw["reasoning_effort"],
            "route.reasoning_effort",
        ),
        "maximum_input_tokens": _strict_int(
            raw["maximum_input_tokens"],
            "route.maximum_input_tokens",
            minimum=1,
            maximum=2_000_000,
        ),
        "maximum_output_tokens": _strict_int(
            raw["maximum_output_tokens"],
            "route.maximum_output_tokens",
            minimum=1,
            maximum=200_000,
        ),
        "timeout_seconds": _strict_int(
            raw["timeout_seconds"],
            "route.timeout_seconds",
            minimum=1,
            maximum=600,
        ),
        "retry_cap": _strict_int(
            raw["retry_cap"],
            "route.retry_cap",
            minimum=0,
            maximum=0,
        ),
        "per_call_cost_ceiling_usd": _strict_decimal_text(
            raw["per_call_cost_ceiling_usd"],
            "route.per_call_cost_ceiling_usd",
        ),
    }
    for name in count_fields:
        result[name] = _strict_int(
            raw[name],
            f"route.{name}",
            minimum=1,
            maximum=100,
        )
    return result


def _validate_router_input(value: Mapping[str, Any]) -> None:
    names = (
        "intent",
        "report_type",
        "query_type",
        "core_topic",
        "primary_entity",
        "entities",
        "is_academic",
    )
    raw = _exact_mapping(value, names, "scenario_packet.router_input")
    for name in names[:-2]:
        _strict_text(
            raw[name],
            f"scenario_packet.router_input.{name}",
            maximum=500,
        )
    _strict_text_tuple(
        raw["entities"],
        "scenario_packet.router_input.entities",
    )
    _strict_bool(
        raw["is_academic"],
        "scenario_packet.router_input.is_academic",
    )


def _validate_route_projection(value: Mapping[str, Any]) -> None:
    raw = _exact_mapping(
        value,
        ("route_id",),
        "scenario_packet.route_projection",
    )
    _strict_text(
        raw["route_id"],
        "scenario_packet.route_projection.route_id",
    )


def _validate_run_contract_projection(
    value: Mapping[str, Any],
) -> None:
    names = (
        "contract_id",
        "schema_version",
        "synthesis_mode",
        "selected_depth",
        "source_requirements",
    )
    raw = _exact_mapping(
        value,
        names,
        "scenario_packet.run_contract_projection",
    )
    for name in names[:-1]:
        _strict_text(
            raw[name],
            f"scenario_packet.run_contract_projection.{name}",
            maximum=240,
        )
    requirements = _strict_sequence(
        raw["source_requirements"],
        "scenario_packet.run_contract_projection.source_requirements",
    )
    for item in requirements:
        if not isinstance(item, Mapping):
            raise OwnerSpecificAuthorizationError(
                "run-contract source requirements must be objects"
            )
        canonical_json_bytes(dict(item))


def _reject_secret_like_text(value: str) -> None:
    lowered = value.casefold()
    for marker in (
        "authorization: bearer",
        "api key:",
        "api_key=",
        "broker token",
        "begin private key",
    ):
        if marker in lowered:
            raise OwnerSpecificAuthorizationError(
                "variant instruction contains secret-like material"
            )


def _reject_forbidden_keys(
    value: Any,
    *,
    forbidden: frozenset[str],
    label: str,
) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = (
                str(key).strip().casefold().replace("-", "_")
            )
            if normalized in forbidden:
                raise OwnerSpecificAuthorizationError(
                    f"{label} contains forbidden field: {normalized}"
                )
            _reject_forbidden_keys(
                nested,
                forbidden=forbidden,
                label=label,
            )
    elif isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes),
    ):
        for item in value:
            _reject_forbidden_keys(
                item,
                forbidden=forbidden,
                label=label,
            )


def _exact_mapping(
    value: Any,
    names: Sequence[str],
    label: str,
) -> dict[str, Any]:
    raw = dict(_strict_mapping(value, label))
    expected = set(names)
    missing = sorted(expected - set(raw))
    unknown = sorted(set(raw) - expected)
    if missing:
        raise OwnerSpecificAuthorizationError(
            f"{label} is missing fields: {', '.join(missing)}"
        )
    if unknown:
        raise OwnerSpecificAuthorizationError(
            f"{label} contains unknown fields: {', '.join(unknown)}"
        )
    return raw


def _strict_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise OwnerSpecificAuthorizationError(
            f"{label} must be one object"
        )
    return value


def _strict_sequence(value: Any, label: str) -> tuple[Any, ...]:
    if not isinstance(value, list):
        raise OwnerSpecificAuthorizationError(
            f"{label} must be one JSON array"
        )
    return tuple(value)


def _strict_text(
    value: Any,
    label: str,
    maximum: int = 1000,
    *,
    preserve: bool = False,
) -> str:
    if not isinstance(value, str):
        raise OwnerSpecificAuthorizationError(
            f"{label} must be a string"
        )
    normalized = value if preserve else value.strip()
    if not normalized.strip():
        raise OwnerSpecificAuthorizationError(
            f"{label} must be explicit"
        )
    if len(normalized) > maximum:
        raise OwnerSpecificAuthorizationError(
            f"{label} exceeds its bound"
        )
    return normalized


def _strict_text_tuple(
    value: Any,
    label: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    items = _strict_sequence(value, label)
    if not items and not allow_empty:
        raise OwnerSpecificAuthorizationError(
            f"{label} must be nonempty"
        )
    return tuple(
        _strict_text(item, f"{label} item", maximum=1000)
        for item in items
    )


def _strict_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise OwnerSpecificAuthorizationError(
            f"{label} must be boolean"
        )
    return value


def _strict_int(
    value: Any,
    label: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise OwnerSpecificAuthorizationError(
            f"{label} must be an integer"
        )
    if value < minimum or value > maximum:
        raise OwnerSpecificAuthorizationError(
            f"{label} is outside its exact bound"
        )
    return value


def _strict_digest(value: Any, label: str) -> str:
    text = _strict_text(value, label, maximum=64)
    if not _DIGEST_PATTERN.fullmatch(text):
        raise OwnerSpecificAuthorizationError(
            f"{label} must be one SHA-256 digest"
        )
    return text


def _strict_decimal_text(value: Any, label: str) -> str:
    text = _strict_text(value, label, maximum=80)
    _positive_decimal(text, label)
    return text


def _positive_decimal(value: str, label: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise OwnerSpecificAuthorizationError(
            f"{label} must be one exact decimal string"
        ) from exc
    if not parsed.is_finite() or parsed <= 0:
        raise OwnerSpecificAuthorizationError(
            f"{label} must be finite and positive"
        )
    return parsed


def _reject_nonfinite_numbers(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise OwnerSpecificAuthorizationError(
            "authorization contains a non-finite number"
        )
    if isinstance(value, Mapping):
        for nested in value.values():
            _reject_nonfinite_numbers(nested)
    elif isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes),
    ):
        for nested in value:
            _reject_nonfinite_numbers(nested)


__all__ = [
    "BLINDING_POLICY_IDENTITY",
    "CANONICAL_POLICY_PACKET_SCHEMA_VERSION",
    "EVALUATION_KIND",
    "GENERIC_BROKER_TRANSPORT_FACTORY_SPEC",
    "OUTCOME_METRIC",
    "OWNER_SPECIFIC_AUTHORIZATION_SCHEMA_VERSION",
    "OWNER_SPECIFIC_ORCHESTRATOR_VERSION",
    "PLANNER_ROLE",
    "POLICY_CANONICALIZATION_VERSION",
    "RETENTION_POSTURE",
    "SCENARIO_PACKET_SCHEMA_VERSION",
    "SEMANTIC_EXECUTION_OBSERVATION_VERSION",
    "SEMANTIC_JUDGE_ROLE",
    "SEMANTIC_REQUIREMENT_PACKET_SCHEMA_VERSION",
    "STOCHASTIC_ATTRIBUTION_CEILING",
    "TRIAL_SCHEDULE_SCHEMA_VERSION",
    "CanonicalExperimentPolicyPacket",
    "EvaluationIdentityAuthorization",
    "InstalledOwnerIdentities",
    "OwnerSpecificAuthorizationError",
    "OwnerSpecificLiveAuthorization",
    "OwnerSpecificScenarioPacket",
    "PlannerRouteAuthorization",
    "PromptExperimentAuthorization",
    "RetentionPolicy",
    "ScenarioPacketIdentity",
    "SemanticJudgeRouteAuthorization",
    "SemanticRequirementPacket",
    "TrialScheduleEntry",
    "WholeEvaluationCaps",
    "build_canonical_execute_command",
    "build_canonical_policy_packet",
    "canonical_json_bytes",
    "canonical_sha256",
    "load_json_object",
    "normalize_repository_relative_path",
    "text_sha256",
    "validate_authorization_context",
]
