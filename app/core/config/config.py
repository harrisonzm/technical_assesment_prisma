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

    # Seguridad
    secret_key: str = Field(default="change-me", min_length=8)
    cors_origins: list[str] = ["http://localhost:3000"]

    # Base de datos
    database_url: str = "sqlite+aiosqlite:///./app.db"

    # Consumidor
    consumer_interval_seconds: float = 5.0
    log_file_path: str | None = None

    @property
    def is_prod(self) -> bool:
        return self.environment == "prod"


@lru_cache
def get_settings() -> Settings:
    """Instancia única de Settings (cacheada) para usar como dependencia de FastAPI."""
    return Settings()
