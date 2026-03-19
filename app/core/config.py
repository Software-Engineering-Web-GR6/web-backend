from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Smart Classroom Backend"
    APP_VERSION: str = "1.0.0"
    SECRET_KEY: str = "change-this-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    DATABASE_URL: str = "sqlite+aiosqlite:///./smart_classroom.db"
    DEFAULT_TEMP_WARNING: float = 30
    DEFAULT_TEMP_DANGER: float = 35
    DEFAULT_HUMIDITY_WARNING: float = 80
    DEFAULT_CO2_WARNING: float = 1000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
