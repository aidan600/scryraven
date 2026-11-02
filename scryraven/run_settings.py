"""Immutable, non-secret inference preferences captured by an accepted job."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from scryraven.model import ModelConfig, ModelRole, default_model_config, valid_model_identifier
from scryraven.research import RunLimits

BACKENDS = {"chatgpt_plan", "openai", "openrouter"}
REASONING = {None, "none", "low", "medium", "high", "xhigh", "max"}
ERROR_MESSAGES = {
    "invalid_run_settings": "Review the backend, exact model identifiers, reasoning and run allowance in Run Settings.",
    "paid_inference_confirmation_required": "Select billed API inference explicitly in Run Settings before submitting.",
    "model_configuration_missing": "The selected backend is unavailable. Its API key or plan sign-in is not configured in the credentialed launcher.",
    "model_request_rejected": "The provider rejected this exact model or its required parameters. Review Run Settings; no replacement model or backend was used.",
    "model_backend_incompatible": "This model cannot satisfy the required strict schema and tool contract. No replacement inference was requested.",
    "model_contract_incompatible": "This model did not satisfy the required strict schema and tool contract. No paid repair or replacement inference was requested.",
    "model_catalog_unavailable": "The signed-in plan model catalog is unavailable. No API fallback was used.",
    "model_unavailable": "This exact model is unavailable from the selected backend. No replacement model was used.",
    "model_routing_mismatch": "The provider reported a different model. Its answer was not accepted and no replacement inference was requested.",
    "model_authentication_failed": "The selected provider could not authenticate. Check its credentialed launcher configuration; no fallback was used.",
    "model_access_denied": "The selected provider denied access to this exact configuration. No fallback was used.",
    "model_reasoning_unsupported": "The selected model does not support this exact reasoning effort. Choose a supported setting for a new submission.",
    "model_not_supported": "This exact model is not available from the selected backend. No replacement model was used.",
    "historical_run_settings_unknown": "This historical run has no saved runtime configuration. Review Run Settings and create a new submission instead of retrying it.",
}


@dataclass(frozen=True)
class RunSettings:
    backend: str
    research_model: str
    research_reasoning: str | None
    answer_model: str
    answer_reasoning: str | None
    api_processing: str | None
    physical_request_limit: int
    external_attempt_limit: int = 16
    seconds_limit: float = 900
    attention_character_limit: int = 128_000

    def __post_init__(self):
        if self.backend not in BACKENDS:
            raise ValueError("invalid_run_settings")
        for model in (self.research_model, self.answer_model):
            if not valid_model_identifier(model, "api" if self.backend == "openai" else self.backend):
                raise ValueError("invalid_run_settings")
        if (self.research_reasoning not in REASONING or self.answer_reasoning not in REASONING
                or (self.api_processing not in {"standard", "fast"} if self.backend == "openai"
                    else self.api_processing is not None)
                or type(self.physical_request_limit) is not int
                or not 2 <= self.physical_request_limit <= (40 if self.backend == "chatgpt_plan" else 12)
                or type(self.external_attempt_limit) is not int or not 0 <= self.external_attempt_limit <= 16
                or type(self.seconds_limit) not in {float, int} or not 0 < self.seconds_limit <= 900
                or type(self.attention_character_limit) is not int
                or not 65_536 <= self.attention_character_limit <= 128_000):
            raise ValueError("invalid_run_settings")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict) -> RunSettings:
        if not isinstance(value, dict) or set(value) - set(cls.__dataclass_fields__):
            raise ValueError("invalid_run_settings")
        try:
            return cls(**value)
        except (TypeError, ValueError):
            raise ValueError("invalid_run_settings") from None

    @classmethod
    def effective(cls, model=None, limits: RunLimits | None = None) -> RunSettings:
        config = getattr(model, "config", None) or default_model_config()
        backend = {"api": "openai", "openrouter": "openrouter", "chatgpt_plan": "chatgpt_plan"}.get(
            getattr(model, "backend", None), "chatgpt_plan" if callable(model) else "openai")
        limits = limits or RunLimits()
        # An API processing choice applies to both roles. Preserve a mixed
        # preexisting profile visibly until the user chooses one explicit tier.
        processing = ("fast" if config.research.service_tier == config.answer.service_tier == "fast"
                      else "standard") if backend == "openai" else None
        return cls(backend, config.research.model, config.research.reasoning or None,
                   config.answer.model, config.answer.reasoning or None, processing,
                   min(limits.physical_model_requests, 40 if backend == "chatgpt_plan" else 12),
                   limits.external_attempts, limits.seconds, limits.attention_characters)

    def model_config(self) -> ModelConfig:
        tier = ("fast" if self.api_processing == "fast" else "default") if self.backend == "openai" else None
        return ModelConfig(ModelRole(self.research_model, self.research_reasoning, tier),
                           ModelRole(self.answer_model, self.answer_reasoning, tier))

    def limits(self) -> RunLimits:
        return RunLimits(self.physical_request_limit, self.external_attempt_limit,
                         self.seconds_limit, self.attention_character_limit)


def settings_from_form(form, initial: RunSettings) -> RunSettings:
    """Only allow bounded data fields; never treat an identifier as routing code."""
    names = ("backend", "research_model", "research_reasoning", "answer_model",
             "answer_reasoning", "api_processing", "physical_request_limit")
    if any(len(form.getlist(name)) != 1 for name in names if name != "api_processing"):
        raise ValueError("invalid_run_settings")
    if len(form.getlist("api_processing")) != (1 if form.get("backend") == "openai" else 0):
        raise ValueError("invalid_run_settings")
    try:
        limit = int(form["physical_request_limit"])
    except (TypeError, ValueError):
        raise ValueError("invalid_run_settings") from None
    backend = form["backend"]
    if limit not in ({6, 12, 40} if backend == "chatgpt_plan" else {6, 12}):
        raise ValueError("invalid_run_settings")
    settings = RunSettings(backend, form["research_model"], form["research_reasoning"] or None,
                           form["answer_model"], form["answer_reasoning"] or None,
                           form["api_processing"] if backend == "openai" else None, limit,
                           initial.external_attempt_limit, initial.seconds_limit,
                           initial.attention_character_limit)
    if backend != "chatgpt_plan" and form.getlist("paid_inference_confirmed") != ["1"]:
        raise ValueError("paid_inference_confirmation_required")
    return settings
