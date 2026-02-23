from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine.url import URL, make_url


class Settings(BaseSettings):
    app_name: str = "SharpPicks"
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/sharppicks"
    odds_api_key: str = ""
    odds_api_base_url: str = "https://api.the-odds-api.com/v4"
    odds_api_regions: str = "us"
    odds_api_markets: str = "h2h,spreads,totals"
    odds_poll_interval_seconds: int = 600

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()


def get_database_url() -> str:
    return settings.database_url


def get_database_identity() -> tuple[str, str]:
    parsed: URL = make_url(get_database_url())
    return parsed.host or "<unknown>", parsed.database or "<unknown>"
