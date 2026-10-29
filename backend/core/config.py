"""Application configuration and strict simulation mode enforcement."""

import sys
from pathlib import Path
from typing import Any, List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Secure Data Wiping & Certified IT Asset Recycling Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # CRITICAL: Application refuses to start with any value other than 'simulation'
    WIPE_MODE: str = "simulation"

    # Database
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "securewipe"
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5434
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5434/securewipe"

    # Security & Tokens
    JWT_SECRET: str = "super-secret-wipe-jwt-key-2026-production-ready"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Simulation & Policy Parameters
    APPROVAL_EXPIRY_HOURS: int = 24
    SIM_FAILURE_RATE: float = 0.0
    SIM_PASS_SLEEP_MS: int = 150  # fast and responsive for tests & live UI

    # Storage Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    STORAGE_DIR: Path = Path(__file__).resolve().parent.parent.parent / "backend" / "storage"
    CERTS_DIR: Path = Path(__file__).resolve().parent.parent.parent / "backend" / "storage" / "certs"

    # Public URL of the web app, used for the verification link / QR code on certificates
    PUBLIC_APP_URL: str = "http://localhost:5173"

    # Seed demo users and devices on startup when the database is empty (handy on fresh cloud hosts)
    AUTO_SEED: bool = True

    # Extra allowed origins by pattern, e.g. every Netlify site and deploy preview
    CORS_ORIGIN_REGEX: str = r"https://([a-z0-9-]+--)?[a-z0-9-]+\.netlify\.app"

    # CORS
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, list):
            return v
        return []

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalise_database_url(cls, v: Any) -> Any:
        """Accepts plain postgres:// URLs from hosting providers (Render, Neon, Supabase...)."""
        if isinstance(v, str):
            for prefix in ("postgres://", "postgresql://", "postgresql+psycopg://"):
                if v.startswith(prefix):
                    return "postgresql+asyncpg://" + v[len(prefix):]
        return v

    @field_validator("WIPE_MODE")
    @classmethod
    def enforce_simulation_mode(cls, v: str) -> str:
        if v.lower() != "simulation":
            sys.stderr.write(
                f"\nCRITICAL SECURITY HALT: WIPE_MODE is '{v}'. The platform ONLY supports 'simulation'. Aborting immediately.\n"
            )
            raise ValueError("Platform strictly refuses to run outside 'simulation' mode.")
        return "simulation"


settings = Settings()

# Ensure storage directories exist
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
settings.CERTS_DIR.mkdir(parents=True, exist_ok=True)
