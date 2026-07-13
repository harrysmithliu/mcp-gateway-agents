from frontend.services.api import DEFAULT_API_BASE_URL, build_api_client


def batch_score_accounts(
    account_ids: list[str],
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
    access_token: str | None = None,
) -> dict[str, object]:
    return build_api_client(access_token, api_base_url, timeout_seconds).post(
        "/risk/batch-score",
        {"account_ids": account_ids},
    )
