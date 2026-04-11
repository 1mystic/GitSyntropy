from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GS_", env_file=str(_ENV_FILE), extra="ignore")

    app_name: str = "GitSyntropy API"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    jwt_secret: str = "local-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_exp_minutes: int = 60
    jwt_issuer: str = "gitsyntropy-local"
    github_client_id: str = "local-dev"
    github_redirect_url: str = "http://localhost:4321/auth"
    github_scope: str = "read:user user:email"
    frontend_url: str = "http://localhost:4321"
    anthropic_model: str = "claude-sonnet-4-6"
    anthropic_api_key: str = ""
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/gitsyntropy"
    github_client_secret: str = ""
    github_access_token: str = ""   # Personal access token for server-side GitHub API calls


settings = Settings()
