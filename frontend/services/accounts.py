from frontend.services.api import DEFAULT_API_BASE_URL, build_api_client


def search_accounts(
    query: str,
    limit: int = 5,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
    access_token: str | None = None,
) -> dict[str, object]:
    return build_api_client(access_token, api_base_url, timeout_seconds).post(
        "/accounts/search",
        {"query": query, "limit": limit},
    )


def get_account_investigation(
    account_id: str,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
    access_token: str | None = None,
) -> dict[str, object]:
    return build_api_client(access_token, api_base_url, timeout_seconds).get(
        f"/accounts/{account_id}/investigation"
    )
