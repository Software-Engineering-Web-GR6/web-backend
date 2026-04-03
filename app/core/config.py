from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    APP_NAME: str = "Smart Classroom Backend"
    APP_VERSION: str = "1.0.0"
    SECRET_KEY: str = "change-this-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    APP_TIMEZONE: str = "Asia/Bangkok"
    DATABASE_URL: str = "postgresql+asyncpg://smartclassroom:smartclassroom@localhost:5432/smart_classroom"
    DEFAULT_TEMP_WARNING: float = 30
    DEFAULT_TEMP_DANGER: float = 35
    DEFAULT_HUMIDITY_WARNING: float = 80
    DEFAULT_CO2_WARNING: float = 1000
    MQTT_ENABLED: bool = True
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_SENSOR_TOPIC: str = "smartclassrooms/sensors/readings"
    MQTT_DEVICE_COMMAND_TOPIC_PREFIX: str = "smartclassrooms/devices"
    MQTT_CLIENT_ID: str = "smart-classroom-backend"
    MQTT_KEEPALIVE_SECONDS: int = 60
    MQTT_DEVICE_ACK_TIMEOUT_SECONDS: float = 1.5
    SMTP_ENABLED: bool = False
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@smartclassroom.local"
    SMTP_USE_TLS: bool = True
    PASSWORD_RESET_CODE_EXPIRE_MINUTES: int = 10
    PASSWORD_RESET_CODE_LENGTH: int = 6
    PASSWORD_RESET_MAX_ATTEMPTS: int = 5

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
