import re


def extract_langchain_planner_output_candidates(
    planner_output_text: str,
) -> list[str]:
    candidate_chunks = re.split(r"[,;\n|]+", planner_output_text)
    normalized_candidates: list[str] = []
    for candidate_chunk in candidate_chunks:
        normalized_candidate = candidate_chunk.strip().strip("`*[](){}- ")
        if not normalized_candidate:
            continue
        normalized_candidates.append(normalized_candidate)

    return normalized_candidates


def parse_langchain_planner_output(
    planner_output_text: str,
    allowed_tool_names: list[str],
) -> list[str]:
    """Parse free-text planner output into allowed tool names."""
    allowed_tool_names_by_lower = {
        tool_name.lower(): tool_name for tool_name in allowed_tool_names
    }
    candidate_tool_names = extract_langchain_planner_output_candidates(
        planner_output_text
    )
    selected_tool_names: list[str] = []
    seen_tool_names: set[str] = set()

    for candidate_tool_name in candidate_tool_names:
        normalized_tool_name = allowed_tool_names_by_lower.get(
            candidate_tool_name.lower()
        )
        if normalized_tool_name is None:
            continue
        if normalized_tool_name in seen_tool_names:
            continue

        seen_tool_names.add(normalized_tool_name)
        selected_tool_names.append(normalized_tool_name)

    return selected_tool_names
