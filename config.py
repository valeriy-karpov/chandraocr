"""
Конфигурация Chandra OCR API Service
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Базовые настройки сервера
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    
    # Директории
    BASE_DIR: Path = Path("/data/chandraocr")
    TEMP_DIR: Path = BASE_DIR / "temp"
    LOG_DIR: Path = BASE_DIR / "logs"
    
    # Файлы
    LOG_FILE: Path = LOG_DIR / "chandra_ocr.log"
    
    # Ограничения
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100 МБ
    OCR_TIMEOUT: int = 600  # 10 минут
    
    # Настройки Chandra
    DEFAULT_METHOD: str = "hf"  # hf или vllm
    MODEL_CHECKPOINT: str = "datalab-to/chandra"
    MAX_OUTPUT_TOKENS: int = 8192
    
    # vLLM настройки (если используется)
    VLLM_API_BASE: str = "http://localhost:8000/v1"
    VLLM_MODEL_NAME: str = "chandra"
    VLLM_GPUS: str = "0"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Создание глобального экземпляра настроек
settings = Settings()

# Экспорт переменных окружения для Chandra
os.environ.setdefault("MODEL_CHECKPOINT", settings.MODEL_CHECKPOINT)
os.environ.setdefault("MAX_OUTPUT_TOKENS", str(settings.MAX_OUTPUT_TOKENS))
os.environ.setdefault("VLLM_API_BASE", settings.VLLM_API_BASE)
os.environ.setdefault("VLLM_MODEL_NAME", settings.VLLM_MODEL_NAME)
os.environ.setdefault("VLLM_GPUS", settings.VLLM_GPUS)
