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


def test_readme_describes_the_current_product_entrypoint() -> None:
    content = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert "Trading and Risk Agentic Platform" in content
    assert "docker compose up -d --build" in content
    assert "docs/LOCAL_RUNBOOK.md" in content
    assert "Batch" not in content
    assert "Round" not in content


def test_runbook_and_script_reference_cover_current_operating_boundaries() -> None:
    runbook = (PROJECT_ROOT / "docs/LOCAL_RUNBOOK.md").read_text(encoding="utf-8")
    scripts = (PROJECT_ROOT / "scripts/README.md").read_text(encoding="utf-8")

    assert "System Status" in runbook
    assert "verify_delivery.py --profile offline" in runbook
    assert "risk.risk_alerts" in runbook
    assert "--profile offline" in scripts
    assert "--allow-paid-provider" in scripts


def test_env_example_contains_no_usable_secret_values() -> None:
    content = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    assert "ANTHROPIC_API_KEY=" in content
    assert "AUTH_JWT_SECRET=replace-with-a-random-local-secret" in content
    assert not re.search(r"(?:sk-ant-|sk-[A-Za-z0-9]{20,})", content)
