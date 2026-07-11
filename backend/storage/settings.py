from dataclasses import dataclass
from functools import lru_cache
import os


@dataclass(slots=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "mcp-gateway-agents")
    app_env: str = os.getenv("APP_ENV", "local")
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    streamlit_server_port: int = int(os.getenv("STREAMLIT_SERVER_PORT", "8501"))
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/mcp_gateway_agents",
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    embedding_provider: str = os.getenv(
        "EMBEDDING_PROVIDER",
        "local_sentence_transformer",
    )
    embedding_model_name: str = os.getenv(
        "EMBEDDING_MODEL_NAME",
        "sentence-transformers/all-MiniLM-L6-v2",
    )
    embedding_device: str = os.getenv("EMBEDDING_DEVICE", "cpu")
    embedding_dimensions: int = int(os.getenv("EMBEDDING_DIMENSIONS", "384"))
    embedding_normalize: bool = os.getenv(
        "EMBEDDING_NORMALIZE",
        "true",
    ).lower() in {"1", "true", "yes", "on"}
    embedding_query_prefix: str = os.getenv("EMBEDDING_QUERY_PREFIX", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    mcp_transport_mode: str = os.getenv("MCP_TRANSPORT_MODE", "registry")
    mcp_server_runtime: str = os.getenv("MCP_SERVER_RUNTIME", "preview")
    upstream_trade_project: str = os.getenv("UPSTREAM_TRADE_PROJECT", "")
    upstream_risk_project: str = os.getenv("UPSTREAM_RISK_PROJECT", "")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
