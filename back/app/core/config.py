import os

from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "..",
    ".env",
)


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    SECRET_KEY: str
    ALGORITHM: str
    INITIAL_ADMIN_USERNAME: str | None = None
    INITIAL_ADMIN_EMAIL: str | None = None
    INITIAL_ADMIN_PASSWORD: str | None = None
    INITIAL_ADMIN_FULL_NAME: str | None = None

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        extra="ignore",
    )


settings = Settings()
