from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Notification System API"
    # Default matches docker-compose for local dev; override in .env for real deployments.
    database_url: str = (
        "postgresql+asyncpg://admin:adminpassword@localhost:5432/notification_system"
    )
    # Comma-separated origins. Stored as str so Pydantic Settings does not require JSON
    # for a list field (see pydantic-settings env parsing for list types).
    cors_origins: str = Field(
        default="http://localhost:3000",
        description="Comma-separated CORS allow_origins, e.g. http://localhost:3000,http://127.0.0.1:3000",
    )
    # Align pool capacity with app concurrency (e.g. delivery semaphore) to avoid QueuePool bottlenecks.
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    # 0 = do not set server-side statement timeout
    db_statement_timeout_ms: int = 0
    # Cap concurrent in-flight async deliveries; keep <= db_pool_size + db_max_overflow to avoid pool starvation
    notification_delivery_concurrency: int = 30

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins_list(self) -> list[str]:
        if not self.cors_origins or not str(self.cors_origins).strip():
            return ["http://localhost:3000"]
        return [
            part.strip() for part in str(self.cors_origins).split(",") if part.strip()
        ]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
