from pydantic_settings import BaseSettings
from pydantic import Field


class AppSettings(BaseSettings):
    app_host: str = Field("localhost", env="APP_HOST")
    app_port: int = Field(8080, env="APP_PORT")
    debug: bool = Field(False, env="DEBUG")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra="ignore"


class CacheSettings(BaseSettings):
    ttl_cache_seconds: int = Field(300, env="TTL_CACHE_SECONDS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra="ignore"
