# Быстрый старт - Chandra OCR API

## ⚡ За 3 минуты

### 1. Установка

```bash
cd /data/chandraocr
chmod +x install.sh start.sh test.sh
./install.sh
```

### 2. Запуск

```bash
./start.sh
```

Или вручную:
```bash
source .venv/bin/activate
python main.py
```

### 3. Тестирование

В новом терминале:
```bash
# Проверка работы
curl http://localhost:8000/health

# Распознать документ
curl -X POST http://localhost:8000/ocr \
     -F "file=@document.pdf" \
     --output result.txt
```

## 📋 Основные команды

```bash
# Запуск сервера
./start.sh

# Тестирование
./test.sh

# Просмотр логов
tail -f logs/chandra_ocr.log

# Python клиент
source .venv/bin/activate
python client.py document.pdf
python client.py document.pdf --json --output result.json
```

## 🌐 Endpoints

- `GET /` - Информация об API
- `GET /health` - Проверка здоровья
- `POST /ocr` - Распознать → текст
- `POST /ocr/json` - Распознать → JSON с метаданными
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc документация

## 🔧 Настройка

Отредактируйте `.env`:
```bash
PORT=8000
MAX_FILE_SIZE=104857600  # 100 МБ
OCR_TIMEOUT=600  # 10 минут
DEFAULT_METHOD=hf  # или vllm
```

## 🚀 Production

```bash
# Установка как systemd сервис
sudo cp chandra-ocr.service /etc/systemd/system/
sudo nano /etc/systemd/system/chandra-ocr.service  # отредактируйте пути
sudo systemctl daemon-reload
sudo systemctl enable chandra-ocr
sudo systemctl start chandra-ocr
```

## 📖 Полная документация

Смотрите [README.md](README.md)

## ❓ Проблемы?

1. Проверьте логи: `tail -f logs/chandra_ocr.log`
2. Проверьте здоровье: `curl http://localhost:8000/health`
3. Запустите тесты: `./test.sh`
