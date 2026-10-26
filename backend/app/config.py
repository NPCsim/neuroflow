from typing import List, Union
from pydantic import field_validator, Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./neuroflow.db"
    CORS_ORIGINS: Union[str, List[str]] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        validation_alias=AliasChoices("CORS_ORIGINS", "ALLOWED_ORIGINS"),
    )
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GEMINI_TIMEOUT_SECONDS: float = 30.0
    GEMINI_MAX_RETRIES: int = 3

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.strip().startswith("["):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:3000", "http://127.0.0.1:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
