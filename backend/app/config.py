from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SharpPicks"
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/sharppicks"
    odds_api_key: str = ""
    odds_api_base_url: str = "https://api.the-odds-api.com/v4"
    odds_api_regions: str = "us"
    odds_api_markets: str = "h2h,spreads,totals"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
