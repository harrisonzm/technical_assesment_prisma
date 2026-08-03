from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()
class Settings(BaseSettings):
    """Configuración de la aplicación, cargada desde variables de entorno o .env."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
    )

    # Aplicación
    app_name: str = "technical_assesment_prisma"
    environment: Literal["local", "dev", "staging", "prod"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    service_name: str = "backend"

    # Servidor
    host: str = "0.0.0.0"
    port: int = 8000

    # Rendimiento HTTP
    gzip_minimum_size: int = Field(default=500, ge=0)
    redis_url: str = "redis://redis:6379/0"
    redis_timeout_seconds: float = Field(default=0.2, gt=0)
    cache_ttl_seconds: int = Field(default=30, ge=0)
    cache_key_prefix: str = "technical-assessment:http-cache"
    rate_limit_requests: int = Field(default=100, ge=0)
    rate_limit_window_seconds: int = Field(default=60, ge=1)
    rate_limit_key_prefix: str = "technical-assessment:rate-limit"
    request_max_concurrency: int = Field(default=50, ge=1)
    request_queue_size: int = Field(default=100, ge=0)
    request_queue_timeout_seconds: float = Field(default=10.0, gt=0)

    # Seguridad
    secret_key: str = Field(default="change-me", min_length=8)
    cors_origins: list[str] = ["http://localhost:3000"]

    # Base de datos
    database_url: str = "sqlite+aiosqlite:///./app.db"

    # Consumidor
    consumer_api_url: str = "http://backend:8000/api/v1"
    consumer_timeout_seconds: float = Field(default=5.0, gt=0)
    consumer_max_retries: int = Field(default=3, ge=0)
    consumer_retry_delay_seconds: float = Field(default=1.0, ge=0)
    consumer_batch_size: int = Field(default=3, ge=1, le=100)
    log_file_path: str | None = None

    @property
    def is_prod(self) -> bool:
        return self.environment == "prod"


@lru_cache
def get_settings() -> Settings:
    """Instancia única de Settings (cacheada) para usar como dependencia de FastAPI."""
    return Settings()
