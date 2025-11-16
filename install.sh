#!/bin/bash

# Скрипт установки Chandra OCR API Service
# Использование: bash install.sh

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Установка Chandra OCR API Service                     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден. Установите Python 3.10 или выше."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
echo "✓ Python версия: $PYTHON_VERSION"

# Проверка версии Python (требуется 3.10+)
REQUIRED_VERSION="3.10"
if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Требуется Python 3.10 или выше"
    exit 1
fi

# Создание виртуального окружения
echo ""
echo "📦 Создание виртуального окружения..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "✓ Виртуальное окружение создано"
else
    echo "✓ Виртуальное окружение уже существует"
fi

# Активация виртуального окружения
echo ""
echo "🔧 Активация виртуального окружения..."
source .venv/bin/activate

# Обновление pip
echo ""
echo "📦 Обновление pip..."
pip install --upgrade pip setuptools wheel

# Установка зависимостей
echo ""
echo "📦 Установка зависимостей..."
pip install -r requirements.txt

# Проверка установки Chandra
echo ""
echo "🔍 Проверка установки Chandra..."
if command -v chandra &> /dev/null; then
    echo "✓ Chandra CLI установлен"
    chandra --help > /dev/null 2>&1 && echo "✓ Chandra работает корректно"
else
    echo "❌ Chandra CLI не найден"
    exit 1
fi

# Создание необходимых директорий
echo ""
echo "📁 Создание директорий..."
mkdir -p temp logs
echo "✓ Директории созданы"

# Копирование примера конфигурации
echo ""
echo "⚙️  Настройка конфигурации..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ Создан файл .env (можете отредактировать настройки)"
else
    echo "✓ Файл .env уже существует"
fi

# Проверка GPU (опционально)
echo ""
echo "🎮 Проверка GPU..."
if command -v nvidia-smi &> /dev/null; then
    echo "✓ NVIDIA GPU обнаружен:"
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader | head -n1
    echo ""
    echo "💡 Для ускорения можете установить flash-attention:"
    echo "   pip install flash-attn"
else
    echo "ℹ️  GPU не обнаружен. Будет использоваться CPU (медленнее)."
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              Установка завершена успешно! ✓                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📋 Следующие шаги:"
echo ""
echo "1. Активируйте виртуальное окружение:"
echo "   source .venv/bin/activate"
echo ""
echo "2. (Опционально) Отредактируйте настройки в .env"
echo ""
echo "3. Запустите сервер:"
echo "   python main.py"
echo "   или"
echo "   uvicorn main:app --host 0.0.0.0 --port 8000"
echo ""
echo "4. Проверьте работу:"
echo "   curl http://localhost:8000/health"
echo ""
echo "5. Документация API:"
echo "   http://localhost:8000/docs"
echo ""
echo "📝 Пример использования:"
echo "   curl -X POST http://localhost:8000/ocr \\"
echo "        -F 'file=@document.pdf' \\"
echo "        --output result.txt"
echo ""
