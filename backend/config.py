from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""
    comfyui_url: str = "http://127.0.0.1:8188"
    host: str = "0.0.0.0"
    port: int = 10018
    max_queue_size: int = 10
    output_dir: str = "./outputs"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()