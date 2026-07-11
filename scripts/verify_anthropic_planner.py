from __future__ import annotations

import json
import os
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent.planning.langchain import (
    DEFAULT_LANGCHAIN_MODEL_NAME,
    DEFAULT_LANGCHAIN_MODEL_PROVIDER,
    invoke_structured_planner,
)
from backend.agent.service import AgentService
from backend.mcp_gateway.registry import build_default_registry


SMOKE_ROLE = "analyst"
SMOKE_REQUEST = "Search the policy playbook for guidance relevant to this review."
MAX_API_CALLS = 1


def build_smoke_report(
    selected_tool_names: list[str],
    prompt_chars: int,
) -> dict[str, object]:
    return {
        "model_provider": DEFAULT_LANGCHAIN_MODEL_PROVIDER,
        "model_name": DEFAULT_LANGCHAIN_MODEL_NAME,
        "planner_mode": "structured",
        "selected_tool_names": selected_tool_names,
        "prompt_chars": prompt_chars,
        "api_calls": MAX_API_CALLS,
    }


def main() -> int:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY is required. Run this script with the project .env file loaded."
        )

    service = AgentService()
    registry = build_default_registry()
    planner_payload = service.build_langchain_planner_payload(
        normalized_role=SMOKE_ROLE,
        normalized_text=SMOKE_REQUEST,
        registry=registry,
    )
    planner_model = service.init_langchain_chat_model()
    if planner_model is None:
        raise RuntimeError("Unable to initialize the configured LangChain Anthropic model.")

    try:
        planner_decision = invoke_structured_planner(
            planner_model=planner_model,
            planner_prompt=planner_payload["planner_prompt"],
        )
    except Exception as exc:
        raise RuntimeError(
            f"Anthropic structured planner smoke failed: {type(exc).__name__}."
        ) from exc

    selected_tool_names = list(planner_decision.selected_tool_names)
    if not selected_tool_names:
        raise RuntimeError("Anthropic planner returned an empty tool selection.")

    print(
        json.dumps(
            build_smoke_report(
                selected_tool_names=selected_tool_names,
                prompt_chars=len(str(planner_payload["planner_prompt"])),
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
