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
    MQTT_ENABLED: bool = True
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_SENSOR_TOPIC: str = "smartclassrooms/sensors/readings"
    MQTT_DEVICE_COMMAND_TOPIC_PREFIX: str = "smartclassrooms/devices"
    MQTT_CLIENT_ID: str = "smart-classroom-backend"
    MQTT_KEEPALIVE_SECONDS: int = 60
    MQTT_DEVICE_ACK_TIMEOUT_SECONDS: float = 3.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
