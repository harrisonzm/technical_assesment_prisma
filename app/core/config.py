from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación, cargada desde variables de entorno o .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Aplicación
    app_name: str = "technical_assesment_prisma"
    environment: Literal["local", "dev", "staging", "prod"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Servidor
    host: str = "0.0.0.0"
    port: int = 8000

    # Seguridad
    secret_key: str = Field(default="change-me", min_length=8)
    cors_origins: list[str] = ["http://localhost:3000"]

    # Base de datos
    database_url: str = "sqlite+aiosqlite:///./app.db"

    @property
    def is_prod(self) -> bool:
        return self.environment == "prod"


@lru_cache
def get_settings() -> Settings:
    """Instancia única de Settings (cacheada) para usar como dependencia de FastAPI."""
    return Settings()
