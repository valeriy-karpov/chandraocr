"""
Chandra OCR API Service
Локальный сервис распознавания документов на базе Chandra OCR
"""

import os
import shutil
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация FastAPI
app = FastAPI(
    title="Chandra OCR API",
    description="Локальный сервис OCR на базе модели Chandra для распознавания документов",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware для доступа из браузера
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OCRProcessor:
    """Класс для обработки OCR запросов"""
    
    # Поддерживаемые форматы
    SUPPORTED_EXTENSIONS = {
        '.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'
    }
    
    CONTENT_TYPE_MAP = {
        'application/pdf': '.pdf',
        'image/jpeg': '.jpg',
        'image/jpg': '.jpg',
        'image/png': '.png',
        'image/bmp': '.bmp',
        'image/tiff': '.tiff',
        'image/tif': '.tif',
        'image/webp': '.webp',
    }
    
    @staticmethod
    def detect_extension(upload: UploadFile) -> str:
        """
        Определение расширения файла
        1. По Content-Type
        2. По имени файла
        3. Fallback .bin
        """
        content_type = (upload.content_type or "").lower()
        
        # Проверка по Content-Type
        if content_type in OCRProcessor.CONTENT_TYPE_MAP:
            return OCRProcessor.CONTENT_TYPE_MAP[content_type]
        
        # Проверка по имени файла
        if upload.filename and "." in upload.filename:
            ext = "." + upload.filename.rsplit(".", 1)[-1].lower()
            if ext in OCRProcessor.SUPPORTED_EXTENSIONS:
                return ext
        
        # Fallback
        logger.warning(f"Unknown file type: {content_type}, filename: {upload.filename}")
        return ".bin"
    
    @staticmethod
    def validate_extension(ext: str) -> bool:
        """Проверка поддерживаемого расширения"""
        return ext.lower() in OCRProcessor.SUPPORTED_EXTENSIONS
    
    @staticmethod
    def run_chandra_ocr(
        input_path: Path, 
        method: str = "hf",
        include_images: bool = False,
        include_headers: bool = False
    ) -> dict:
        """
        Запуск Chandra OCR через CLI
        
        Args:
            input_path: Путь к входному файлу
            method: Метод инференса (hf или vllm)
            include_images: Извлекать изображения
            include_headers: Включать колонтитулы
            
        Returns:
            dict с результатами: text, metadata, images_count
        """
        if method not in ("hf", "vllm"):
            raise ValueError("method должен быть 'hf' или 'vllm'")
        
        # Создание временной директории для вывода
        output_dir = input_path.parent / "output"
        output_dir.mkdir(exist_ok=True)
        
        # Формирование команды
        cmd = [
            "chandra",
            str(input_path),
            str(output_dir),
            "--method", method,
        ]
        
        # Дополнительные параметры
        if not include_images:
            cmd.append("--no-images")
        if not include_headers:
            cmd.append("--no-headers-footers")
        
        logger.info(f"Запуск Chandra: {' '.join(cmd)}")
        
        # Запуск процесса
        start_time = datetime.now()
        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=settings.OCR_TIMEOUT
            )
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout при обработке файла {input_path.name}")
            raise RuntimeError(f"Превышено время ожидания ({settings.OCR_TIMEOUT}s)")
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        if proc.returncode != 0:
            error_msg = proc.stderr[-2000:] if proc.stderr else "Unknown error"
            logger.error(f"Chandra OCR failed: {error_msg}")
            raise RuntimeError(f"Ошибка OCR (код {proc.returncode}): {error_msg}")
        
        logger.info(f"OCR выполнен за {processing_time:.2f}s")
        
        # Поиск результатов
        result = {
            'text': '',
            'html': '',
            'metadata': {},
            'images_count': 0,
            'processing_time': processing_time
        }
        
        # Поиск markdown файла
        md_files = list(output_dir.glob("**/*.md"))
        if md_files:
            result['text'] = md_files[0].read_text(encoding="utf-8", errors="ignore")
            logger.info(f"Найден markdown: {md_files[0].name}, размер: {len(result['text'])} символов")
        
        # Поиск HTML файла
        html_files = list(output_dir.glob("**/*.html"))
        if html_files:
            result['html'] = html_files[0].read_text(encoding="utf-8", errors="ignore")
        
        # Поиск метаданных
        metadata_files = list(output_dir.glob("**/*_metadata.json"))
        if metadata_files:
            import json
            try:
                result['metadata'] = json.loads(
                    metadata_files[0].read_text(encoding="utf-8")
                )
            except Exception as e:
                logger.warning(f"Не удалось прочитать метаданные: {e}")
        
        # Подсчет изображений
        image_files = list(output_dir.glob("**/images/*.png"))
        result['images_count'] = len(image_files)
        
        if not result['text'] and not result['html']:
            logger.error("Не найден выходной файл (.md/.html)")
            raise RuntimeError("OCR не создал выходные файлы")
        
        return result


processor = OCRProcessor()


@app.post(
    "/ocr",
    response_class=PlainTextResponse,
    summary="Распознать документ",
    description=(
        "Распознавание документа (PDF, JPG, PNG и др.) с помощью Chandra OCR. "
        "Поддержка русского языка и латиницы. Возвращает распознанный текст в формате Markdown."
    ),
    responses={
        200: {"description": "Успешное распознавание", "content": {"text/plain": {}}},
        400: {"description": "Неверный формат файла"},
        500: {"description": "Ошибка обработки"}
    }
)
async def ocr_endpoint(
    file: UploadFile = File(..., description="Файл документа (PDF, JPG, PNG)"),
    method: Optional[str] = Form(default="hf", description="Метод: hf или vllm"),
    include_images: bool = Form(default=False, description="Извлекать изображения"),
    include_headers: bool = Form(default=False, description="Включать колонтитулы")
):
    """
    Основной endpoint для OCR
    """
    request_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    logger.info(f"[{request_id}] Новый запрос OCR: {file.filename}, method={method}")
    
    # Создание временной директории
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"chandra_{request_id}_", dir=settings.TEMP_DIR))
    
    try:
        # Определение расширения
        ext = processor.detect_extension(file)
        
        # Проверка поддерживаемого формата
        if not processor.validate_extension(ext):
            raise HTTPException(
                status_code=400,
                detail=f"Неподдерживаемый формат файла: {ext}. "
                       f"Поддерживаются: {', '.join(processor.SUPPORTED_EXTENSIONS)}"
            )
        
        # Сохранение файла
        input_path = tmp_dir / f"input{ext}"
        file_size = 0
        
        with input_path.open("wb") as f:
            while True:
                chunk = await file.read(8192)
                if not chunk:
                    break
                f.write(chunk)
                file_size += len(chunk)
        
        logger.info(f"[{request_id}] Файл сохранен: {input_path.name}, размер: {file_size} байт")
        
        # Проверка на пустой файл
        if file_size == 0:
            raise HTTPException(status_code=400, detail="Файл пустой")
        
        # Проверка максимального размера
        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Файл слишком большой: {file_size} байт. "
                       f"Максимум: {settings.MAX_FILE_SIZE} байт"
            )
        
        # Запуск OCR
        try:
            result = processor.run_chandra_ocr(
                input_path,
                method=method or "hf",
                include_images=include_images,
                include_headers=include_headers
            )
            
            logger.info(
                f"[{request_id}] OCR завершен: "
                f"{len(result['text'])} символов, "
                f"{result['images_count']} изображений, "
                f"{result['processing_time']:.2f}s"
            )
            
            # Возврат текста
            return result['text']
            
        except ValueError as e:
            logger.error(f"[{request_id}] Ошибка валидации: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except RuntimeError as e:
            logger.error(f"[{request_id}] Ошибка обработки: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Очистка временных файлов
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            logger.debug(f"[{request_id}] Временная директория очищена")
        except Exception as e:
            logger.warning(f"[{request_id}] Ошибка при очистке: {e}")


@app.post(
    "/ocr/json",
    response_class=JSONResponse,
    summary="Распознать документ (JSON ответ)",
    description="То же что /ocr, но возвращает JSON с дополнительной информацией"
)
async def ocr_json_endpoint(
    file: UploadFile = File(...),
    method: Optional[str] = Form(default="hf"),
    include_images: bool = Form(default=False),
    include_headers: bool = Form(default=False)
):
    """
    OCR endpoint с JSON-ответом (включает метаданные)
    """
    request_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    logger.info(f"[{request_id}] JSON OCR запрос: {file.filename}")
    
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"chandra_{request_id}_", dir=settings.TEMP_DIR))
    
    try:
        ext = processor.detect_extension(file)
        
        if not processor.validate_extension(ext):
            raise HTTPException(
                status_code=400,
                detail=f"Неподдерживаемый формат: {ext}"
            )
        
        input_path = tmp_dir / f"input{ext}"
        file_size = 0
        
        with input_path.open("wb") as f:
            while True:
                chunk = await file.read(8192)
                if not chunk:
                    break
                f.write(chunk)
                file_size += len(chunk)
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="Файл пустой")
        
        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Файл слишком большой: {file_size} байт"
            )
        
        result = processor.run_chandra_ocr(
            input_path,
            method=method or "hf",
            include_images=include_images,
            include_headers=include_headers
        )
        
        logger.info(f"[{request_id}] JSON OCR завершен успешно")
        
        return {
            "success": True,
            "text": result['text'],
            "html": result['html'] if result['html'] else None,
            "metadata": result['metadata'],
            "images_count": result['images_count'],
            "processing_time": result['processing_time'],
            "file_size": file_size,
            "filename": file.filename
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Ошибка: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.get("/", response_class=PlainTextResponse)
async def root():
    """Информация об API"""
    return f"""
╔════════════════════════════════════════════════════════════╗
║              CHANDRA OCR API SERVICE v1.0                  ║
╚════════════════════════════════════════════════════════════╝

Локальный сервис распознавания документов на базе Chandra OCR

📋 Endpoints:
  POST /ocr      - Распознать документ → текст (Markdown)
  POST /ocr/json - Распознать документ → JSON с метаданными
  GET  /health   - Проверка здоровья сервиса
  GET  /docs     - Swagger документация
  GET  /redoc    - ReDoc документация

📝 Пример использования:
  curl -X POST "http://localhost:{settings.PORT}/ocr" \\
       -F "file=@document.pdf" \\
       -F "method=hf" \\
       --output result.txt

🔧 Конфигурация:
  - Порт: {settings.PORT}
  - Макс. размер файла: {settings.MAX_FILE_SIZE / 1024 / 1024:.0f} МБ
  - Timeout OCR: {settings.OCR_TIMEOUT}s
  - Метод по умолчанию: {settings.DEFAULT_METHOD}
  - Логи: {settings.LOG_FILE}

🌐 Поддерживаемые форматы:
  {', '.join(sorted(processor.SUPPORTED_EXTENSIONS))}

💡 Язык: Русский + Латиница (автоматическое определение)
"""


@app.get("/health")
async def health_check():
    """Проверка работоспособности сервиса"""
    try:
        # Проверка доступности команды chandra
        result = subprocess.run(
            ["chandra", "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )
        chandra_available = result.returncode == 0
    except Exception as e:
        chandra_available = False
        logger.error(f"Chandra недоступна: {e}")
    
    return {
        "status": "healthy" if chandra_available else "unhealthy",
        "chandra_available": chandra_available,
        "version": "1.0.0",
        "temp_dir": str(settings.TEMP_DIR),
        "temp_dir_exists": settings.TEMP_DIR.exists()
    }


if __name__ == "__main__":
    # Создание необходимых директорий
    settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
    settings.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Запуск Chandra OCR API на порту {settings.PORT}")
    
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower()
    )
