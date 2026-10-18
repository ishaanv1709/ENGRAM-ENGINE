from pathlib import Path
from contextvars import ContextVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.collective", extra="ignore")

    @classmethod
    def settings_customise_sources(
        cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings
    ):
        # This local app's explicit project file wins over unrelated inherited
        # provider keys on the Windows host. Explicit constructor values win all.
        return init_settings, dotenv_settings, env_settings, file_secret_settings

    database_url: str = "postgresql://engram:engram-local@127.0.0.1:55432/engram"
    falkor_host: str = "127.0.0.1"
    falkor_port: int = 56379
    falkor_password: str = "engram-graph-local"
    falkor_username: str = "default"
    falkor_tls: bool = False
    qdrant_url: str = "http://127.0.0.1:56333"
    qdrant_api_key: str = ""
    mem0_history_backend: str = "sqlite"
    anthropic_api_key: str = "****"
    agent_provider: str = "anthropic"
    groq_api_key: str = "****"
    decision_provider: str = "jev"
    safeguard_model: str = "openai/gpt-oss-safeguard-20b"
    groq_tokens_per_minute: int = 8000
    groq_max_output_tokens: int = 2000
    memory_max_output_tokens: int = 2000
    safeguard_tokens_per_minute: int = 2000
    decision_url: str = "http://127.0.0.1:8009/v1/systemone"
    decision_timeout: int = 180
    web_search_provider: str = "tavily"
    langsearch_api_key: str = "****"
    langsearch_daily_limit: int = Field(default=1000, ge=1, le=1000)
    agent_model: str = "claude-sonnet-4-5-20250929"
    jev_api_key: str = "****"
    jev_model: str = "jev-latest"
    tavily_api_key: str = "****"
    embedding_url: str = "http://127.0.0.1:8091/v1"
    embedding_model: str = "mxbai-embed-large-v1"
    embedding_model_path: Path = Path("data/models/mxbai-embed-large-v1_fp32.gguf")
    embedding_dimension: int = 1024
    artifact_root: Path = Path("data/collective/artifacts")
    artifact_backend: str = "local"
    artifact_service_origin: str = ""
    artifact_service_token: str = ""
    artifact_bucket: str = "engram-collective-artifacts"
    sandbox_image: str = "engram-sandbox:local"
    sandbox_runtime: str = "wsl"
    wsl_distribution: str = "Ubuntu-22.04"
    max_parallel_agents: int = 3
    max_agent_steps: int = 48
    max_tool_calls: int = 32
    max_run_seconds: int = 900
    lease_seconds: int = 90
    memory_budget_tokens: int = 2000
    cache_size: int = 50
    cookie_secure: bool = False
    agent_api_key: str = ""
    agent_base_url: str = ""
    agent_protocol: str = "chat"
    provider_identity: str = "host"
    policy_override: dict | None = None
    provider_encryption_key: str = ""
    origins: list[str] = [
        "http://127.0.0.1:8088",
        "http://localhost:8088",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


base_settings = Settings()
provider_settings = ContextVar("engram_provider_settings", default={})


class ScopedSettings:
    """Provider overrides are local to a request/task and its worker threads."""

    def __getattr__(self, name):
        values = provider_settings.get()
        return values[name] if name in values else getattr(base_settings, name)


settings = ScopedSettings()


def configured(value: str) -> bool:
    return bool(value.strip()) and "****" not in value and not value.startswith("your-")


class DependencyUnavailable(RuntimeError):
    """A required real service is unavailable; never synthesize a replacement."""


def require_key(name: str, value: str) -> str:
    if not configured(value):
        raise DependencyUnavailable(f"Configure {name} in .env.collective to enable this operation.")
    return value
