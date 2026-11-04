"""Protected hosted defaults and identity-scoped processing preferences.

Preferences affect only new admissions. An accepted job always carries its own
validated immutable configuration, including explicit retries.
"""

from __future__ import annotations

from dataclasses import replace

from scryraven.run_settings import PHYSICAL_REQUEST_CEILING, RunSettings

# Deliberately exact API identifiers, not arbitrary routing strings or aliases.
# This is the hosted preview's approved family; local Run Settings stay open.
HOSTED_MODEL_CHOICES = {
    "gpt-6.1-terra": {"label": "Terra", "reasoning": ("", "none", "low", "medium", "high", "xhigh", "max")},
    "gpt-6.1-sol": {"label": "Sol", "reasoning": ("", "low", "medium", "high", "xhigh", "max")},
    "gpt-6-luna": {"label": "Luna", "reasoning": ("", "none", "low", "medium", "high", "xhigh", "max")},
}


def validate_hosted_settings(settings: RunSettings) -> RunSettings:
    """Validate the approved API family without inference or credential access."""
    if settings.backend != "openai":
        raise ValueError("invalid_run_settings")
    for model, effort in ((settings.research_model, settings.research_reasoning),
                          (settings.answer_model, settings.answer_reasoning)):
        choice = HOSTED_MODEL_CHOICES.get(model)
        if choice is None or (effort or "") not in choice["reasoning"]:
            raise ValueError("invalid_run_settings")
    return settings


class HostedPreferences:
    def __init__(self, store, initial: RunSettings):
        self.store = store
        self.initial = validate_hosted_settings(initial)
        # Invalid protected data fails closed instead of silently using a new
        # model selection. No historical job or conversation is rewritten.
        self.defaults()

    def defaults(self) -> RunSettings:
        saved = self.store.get_hosted_preferences()
        return validate_hosted_settings(RunSettings.from_dict(saved)) if saved is not None else self.initial

    def for_user(self, owner_id: str, *, admin: bool = False) -> RunSettings:
        settings = self.defaults()
        tier = None if admin else self.store.get_hosted_processing(owner_id)
        return replace(settings, api_processing=tier) if tier is not None else settings

    def save_defaults(self, form) -> None:
        # All technical ceilings remain operator-owned. The form contains only
        # model/effort/tier choices, never credentials, backend or limits.
        settings = RunSettings(
            "openai", form["research_model"], form["research_reasoning"] or None,
            form["answer_model"], form["answer_reasoning"] or None, form["api_processing"],
            PHYSICAL_REQUEST_CEILING, self.initial.external_attempt_limit,
            self.initial.seconds_limit, self.initial.attention_character_limit,
        )
        self.store.set_hosted_preferences(validate_hosted_settings(settings).to_dict())

    def save_processing(self, owner_id: str, processing: str, *, admin: bool = False) -> None:
        if processing not in {"standard", "fast"}:
            raise ValueError("invalid_run_settings")
        if admin:
            self.store.set_hosted_preferences(replace(self.defaults(), api_processing=processing).to_dict())
        else:
            self.store.set_hosted_processing(owner_id, processing)
