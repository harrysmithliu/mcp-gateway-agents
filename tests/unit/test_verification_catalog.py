import pytest

from backend.verification.catalog import (
    STAGE_CATALOG,
    list_stage_names,
    resolve_stage_selection,
)


def test_local_profile_expands_dependencies_in_stable_order() -> None:
    stages = resolve_stage_selection((), profile="local")

    assert stages == (
        "readiness",
        "data_state",
        "rag_mcp",
        "workflow",
        "cache_guardrails",
        "evaluation",
    )


def test_default_stage_list_excludes_paid_provider() -> None:
    assert "anthropic_planner" not in list_stage_names()
    assert "anthropic_planner" in list_stage_names(include_paid_provider=True)


def test_paid_provider_requires_explicit_opt_in() -> None:
    with pytest.raises(ValueError, match="allow-paid-provider"):
        resolve_stage_selection(("anthropic_planner",))

    assert resolve_stage_selection(
        ("anthropic_planner",), allow_paid_provider=True
    ) == ("anthropic_planner",)


def test_selected_rag_stage_includes_only_its_dependencies() -> None:
    stages = resolve_stage_selection(("rag_mcp",))

    assert stages == ("readiness", "data_state", "rag_mcp")
    assert STAGE_CATALOG["data_state"].mutates_local_state is True


def test_live_evaluation_requires_runtime_but_is_in_local_profile() -> None:
    assert STAGE_CATALOG["evaluation"].requires_runtime is True
    assert "evaluation" in resolve_stage_selection((), profile="local")
