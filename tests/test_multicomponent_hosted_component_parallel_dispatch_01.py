"""Phase 5A product-path regressions for hosted component parallel dispatch.

Test classification:
- proof class: offline_product_path_proof
- validation bucket: phase_focus
- harness label: PRODUCT-PATH-REGRESSION
- runtime path: ordinary qualifying ``run_pipeline`` multi-component execution
- promotion posture: remain phase-focused; these are detailed concurrency custody tests
"""

from __future__ import annotations

from copy import deepcopy

import pytest

from core.multicomponent_graph_scheduling import (
    BACKEND_CONSERVATIVE_UNKNOWN,
    BACKEND_HOSTED_API,
    BACKEND_LOCAL_OPENAI_COMPATIBLE,
    MULTICOMPONENT_SCHEDULER_SCHEMA_VERSION,
    MULTICOMPONENT_SCHEDULER_V2_SCHEMA_VERSION,
    MulticomponentGraphSchedulingError,
    initialize_scheduler_state,
    initialize_scheduler_v2_state,
    validate_scheduler_state,
)


@pytest.mark.parametrize(
    ("provider", "configured", "backend", "width"),
    [
        ("OpenAI", "OpenAI", BACKEND_HOSTED_API, 2),
        ("open_router", "OpenRouter", BACKEND_HOSTED_API, 2),
        (
            "lm_studio",
            "Local (LM Studio)",
            BACKEND_LOCAL_OPENAI_COMPATIBLE,
            1,
        ),
        ("unsupported-provider", "unsupported-provider", BACKEND_CONSERVATIVE_UNKNOWN, 1),
    ],
)
def test_scheduler_v2_profile_is_derived_only_from_canonical_provider_identity(
    provider: str,
    configured: str,
    backend: str,
    width: int,
) -> None:
    scheduler = initialize_scheduler_v2_state(
        run_id="run-profile",
        request_id="request-profile",
        configured_provider=provider,
    )

    assert scheduler["schema_version"] == MULTICOMPONENT_SCHEDULER_V2_SCHEMA_VERSION
    assert scheduler["configured_provider_class"] == configured
    assert scheduler["backend_class"] == backend
    assert scheduler["effective_width"] == width
    assert scheduler["hard_cap"] == width
    assert scheduler["maximum_active_physical_leases"] == width
    assert scheduler["runtime_parallelism"] is (width == 2)
    assert scheduler["serial_scheduling"] is (width == 1)


def test_retained_scheduler_v1_rejects_every_parallel_or_batch_extension() -> None:
    scheduler = initialize_scheduler_state(
        run_id="run-v1",
        request_id="request-v1",
    )
    assert scheduler["schema_version"] == MULTICOMPONENT_SCHEDULER_SCHEMA_VERSION
    validate_scheduler_state(scheduler)

    mutations = (
        ("runtime_parallelism", True),
        ("maximum_active_physical_leases", 2),
        ("effective_width", 2),
        ("batch_history", []),
    )
    for key, value in mutations:
        forged = deepcopy(scheduler)
        forged[key] = value
        with pytest.raises(MulticomponentGraphSchedulingError):
            validate_scheduler_state(forged)

