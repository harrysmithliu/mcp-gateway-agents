from pydantic import BaseModel, ConfigDict, Field


class PlannerDecision(BaseModel):
    """Typed tool-selection result expected from the LangChain planner."""

    model_config = ConfigDict(extra="forbid")

    contract_version: str = Field(default="planner.v1", min_length=1)
    selected_tool_names: list[str] = Field(default_factory=list)
