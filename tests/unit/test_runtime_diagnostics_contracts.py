from backend.diagnostics.contracts import (
    ReadinessComponent,
    ReadinessReason,
    ReadinessState,
    RuntimeReadinessReport,
)


def test_readiness_report_serializes_stable_state_and_component_payload() -> None:
    report = RuntimeReadinessReport(
        state=ReadinessState.DEGRADED,
        components=(
            ReadinessComponent(
                name="retrieval",
                state=ReadinessState.DISABLED,
                reason_code=ReadinessReason.DISABLED_BY_CONFIGURATION,
                message="Knowledge retrieval is disabled.",
                remediation="Set RETRIEVAL_ENABLED=true when retrieval is required.",
                details={"provider": "local_sentence_transformer"},
            ),
        ),
        config={"app_env": "local", "database_host": "localhost"},
    )

    assert report.to_payload() == {
        "state": "degraded",
        "components": [
            {
                "name": "retrieval",
                "state": "disabled",
                "reason_code": "disabled_by_configuration",
                "message": "Knowledge retrieval is disabled.",
                "remediation": "Set RETRIEVAL_ENABLED=true when retrieval is required.",
                "details": {"provider": "local_sentence_transformer"},
            }
        ],
        "config": {"app_env": "local", "database_host": "localhost"},
    }


def test_readiness_contract_does_not_include_raw_secret_fields() -> None:
    component = ReadinessComponent(
        name="backend",
        state=ReadinessState.READY,
        reason_code=ReadinessReason.CONFIGURED,
        message="Backend runtime is initialized.",
        details={"transport_mode": "registry"},
    )

    payload = component.to_payload()

    assert "api_key" not in payload
    assert "password" not in payload
    assert "token" not in payload
    assert payload["details"] == {"transport_mode": "registry"}
