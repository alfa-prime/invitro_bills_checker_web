from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BASE_URL: str
    TIMEOUT: float
    HEADER_ORIGIN: str
    HEADER_REFERER: str
    API_KEY: str
    START_ROW: int
    MAX_COL: int

    LOGS_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings() # noqa