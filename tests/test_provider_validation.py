from core.provider_validation import missing_required_api_keys


def test_openai_required_when_model_provider_is_openai() -> None:
    missing = missing_required_api_keys(
        fast_provider="OpenAI",
        smart_provider="Local (LM Studio)",
        embed_provider="Local (LM Studio)",
        env={},
    )
    assert missing == ["OPENAI_API_KEY"]


def test_no_openai_key_required_for_non_openai_providers() -> None:
    missing = missing_required_api_keys(
        fast_provider="OpenRouter",
        smart_provider="Local (LM Studio)",
        embed_provider="Local (LM Studio)",
        env={},
    )
    assert missing == []


def test_only_active_search_provider_keys_are_required() -> None:
    missing = missing_required_api_keys(
        fast_provider="OpenRouter",
        smart_provider="Local (LM Studio)",
        embed_provider="Local (LM Studio)",
        active_search_providers=["exa", "linkup"],
        env={"EXA_API_KEY": "x"},
    )
    assert missing == ["LINKUP_API_KEY"]


def test_inactive_search_providers_do_not_require_keys() -> None:
    missing = missing_required_api_keys(
        fast_provider="OpenRouter",
        smart_provider="Local (LM Studio)",
        embed_provider="Local (LM Studio)",
        active_search_providers=["exa"],
        env={},
    )
    assert missing == ["EXA_API_KEY"]
