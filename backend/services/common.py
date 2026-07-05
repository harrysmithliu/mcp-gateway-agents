def extract_query_text(request_payload: dict[str, object]) -> str:
    raw_query = request_payload.get("query")
    if isinstance(raw_query, str) and raw_query.strip():
        return raw_query.strip()

    raw_message_text = request_payload.get("message_text")
    if isinstance(raw_message_text, str) and raw_message_text.strip():
        return raw_message_text.strip()

    return ""


def tokenize_text(text: str) -> set[str]:
    normalized_text = text.lower()
    return {
        token.strip(".,!?():;[]{}")
        for token in normalized_text.split()
        if token.strip(".,!?():;[]{}")
    }
