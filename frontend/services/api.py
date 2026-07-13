import json
import os
from dataclasses import dataclass
from urllib import error, parse, request


DEFAULT_API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


class ApiError(RuntimeError):
    def __init__(self, message: str, status_code: int = 0) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(slots=True)
class ApiClient:
    base_url: str = DEFAULT_API_BASE_URL
    access_token: str | None = None
    timeout_seconds: float = 5.0

    def request_json(
        self,
        method: str,
        endpoint_path: str,
        payload: dict[str, object] | None = None,
        query: dict[str, object] | None = None,
    ) -> dict[str, object]:
        url = f"{self.base_url.rstrip('/')}/{endpoint_path.lstrip('/')}"
        if query:
            url = f"{url}?{parse.urlencode({key: value for key, value in query.items() if value is not None})}"
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        api_request = request.Request(
            url=url,
            data=body,
            headers=headers,
            method=method.upper(),
        )
        try:
            with request.urlopen(api_request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = self._read_error_detail(exc)
            raise ApiError(detail, status_code=exc.code) from exc
        except error.URLError as exc:
            raise ApiError("Unable to reach the application API.") from exc

    def get(
        self,
        endpoint_path: str,
        query: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return self.request_json("GET", endpoint_path, query=query)

    def post(
        self,
        endpoint_path: str,
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return self.request_json("POST", endpoint_path, payload=payload)

    @staticmethod
    def _read_error_detail(exc: error.HTTPError) -> str:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            detail = payload.get("detail")
            if detail:
                return str(detail)
        except (ValueError, UnicodeDecodeError):
            pass
        return f"Application API request failed with status {exc.code}."


def build_api_client(
    access_token: str | None = None,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout_seconds: float = 5.0,
) -> ApiClient:
    return ApiClient(
        base_url=api_base_url,
        access_token=access_token,
        timeout_seconds=timeout_seconds,
    )
