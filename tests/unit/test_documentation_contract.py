from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_supported_documentation_surfaces_exist() -> None:
    for relative_path in (
        "README.md",
        "docs/LOCAL_RUNBOOK.md",
        "scripts/README.md",
        ".env.example",
        "compose.yaml",
    ):
        assert (PROJECT_ROOT / relative_path).is_file()

    compose = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")
    assert "HF_HOME: /root/.cache/huggingface" in compose
    assert "${HOME}/.cache/huggingface:/root/.cache/huggingface" in compose


def test_readme_describes_the_current_product_entrypoint() -> None:
    content = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert "Trading and Risk Agentic Platform" in content
    assert "docker compose up -d --build" in content
    assert "docs/LOCAL_RUNBOOK.md" in content
    assert "four core MCP SDK tools" in content
    assert "knowledge.search" in content
    assert "risk.score_account" in content
    assert "trade.query_metrics" in content
    assert "ops.create_alert_or_action" in content
    assert "seeded risk-source profiles" in content
    assert "reusable model artifacts" not in content
    assert "Batch" not in content
    assert "Round" not in content


def test_runbook_and_script_reference_cover_current_operating_boundaries() -> None:
    runbook = (PROJECT_ROOT / "docs/LOCAL_RUNBOOK.md").read_text(encoding="utf-8")
    scripts = (PROJECT_ROOT / "scripts/README.md").read_text(encoding="utf-8")

    assert "System Status" in runbook
    assert "verify_delivery.py --profile offline" in runbook
    assert "risk.risk_alerts" in runbook
    assert "verify_batch7_delivery.py --mode inspect" in runbook
    assert "--confirm-reset" in runbook
    assert "--profile offline" in scripts
    assert "verify_batch7_delivery.py --mode verify_current" in scripts
    assert "--allow-paid-provider" in scripts
    assert "test_mcp_stdio_transport.py tests/integration/test_mcp_transport_sdk_mode.py" in runbook
    assert "four SDK-exposed core tools" in runbook
    assert "not currently exposed through the SDK MCP server" in runbook
    assert "focused retrieval-backed `knowledge.search` check" in runbook
    assert "one local SDK stdio `knowledge.search` call" in scripts


def test_requirements_distinguish_delivered_and_future_mcp_tools() -> None:
    content = (PROJECT_ROOT / "docs/PROJECT_REQUIREMENTS.md").read_text(
        encoding="utf-8"
    )

    assert "Delivered SDK MCP core:" in content
    for tool_name in (
        "knowledge.search",
        "risk.score_account",
        "trade.query_metrics",
        "ops.create_alert_or_action",
    ):
        assert f"- `{tool_name}`" in content

    assert "Delivered HTTP/domain capabilities not currently exposed through the SDK MCP" in content
    assert "- `risk.batch_score`" in content
    assert "- `audit.fetch_recent_events`" in content
    assert "Future MCP and domain expansion:" in content
    assert "- `trade.query_account_activity`" in content
    assert "- `trade.render_report`" in content


def test_env_example_contains_no_usable_secret_values() -> None:
    content = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    assert "ANTHROPIC_API_KEY=" in content
    assert "AUTH_JWT_SECRET=replace-with-a-random-local-secret" in content
    assert not re.search(r"(?:sk-ant-|sk-[A-Za-z0-9]{20,})", content)
