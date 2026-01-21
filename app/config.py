# config.py
from pydantic_settings import BaseSettings
from pydantic import Field


class AppSettings(BaseSettings):
    app_host: str = Field("127.0.0.1", env="APP_HOST")
    app_port: int = Field(8000, env="APP_PORT")
    debug: bool = Field(False, env="DEBUG")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"