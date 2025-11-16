#!/bin/bash

# Скрипт тестирования Chandra OCR API

PORT=${1:-8000}
BASE_URL="http://localhost:$PORT"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          Тестирование Chandra OCR API                     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "URL: $BASE_URL"
echo ""

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для проверки
check() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $1"
    else
        echo -e "${RED}✗${NC} $1"
        return 1
    fi
}

# 1. Проверка доступности сервера
echo "1. Проверка доступности сервера..."
curl -s -f "$BASE_URL/" > /dev/null
check "Сервер доступен"
echo ""

# 2. Проверка health endpoint
echo "2. Проверка здоровья сервиса..."
HEALTH=$(curl -s "$BASE_URL/health")
echo "$HEALTH" | grep -q '"status":"healthy"'
check "Сервис работает"

echo "$HEALTH" | grep -q '"chandra_available":true'
check "Chandra доступен"
echo ""

# 3. Проверка Swagger документации
echo "3. Проверка документации..."
curl -s -f "$BASE_URL/docs" > /dev/null
check "Swagger UI доступен"

curl -s -f "$BASE_URL/redoc" > /dev/null
check "ReDoc доступен"
echo ""

# 4. Тест OCR (если есть тестовый файл)
echo "4. Тест OCR..."
if [ -f "test_image.png" ] || [ -f "test_document.pdf" ]; then
    TEST_FILE=$(ls test_image.png test_document.pdf 2>/dev/null | head -1)
    echo -e "${YELLOW}Найден тестовый файл: $TEST_FILE${NC}"
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/ocr" \
         -F "file=@$TEST_FILE" 2>&1)
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✓${NC} OCR выполнен успешно"
        echo "Первые 100 символов результата:"
        echo "$BODY" | head -c 100
        echo "..."
    else
        echo -e "${RED}✗${NC} OCR завершился с ошибкой (HTTP $HTTP_CODE)"
        echo "$BODY" | head -20
    fi
else
    echo -e "${YELLOW}⊘${NC} Тестовый файл не найден (создайте test_image.png или test_document.pdf)"
fi
echo ""

# 5. Проверка логов
echo "5. Проверка логирования..."
if [ -f "logs/chandra_ocr.log" ]; then
    LINES=$(wc -l < logs/chandra_ocr.log)
    echo -e "${GREEN}✓${NC} Лог-файл существует ($LINES строк)"
    
    echo "Последние 3 записи в логе:"
    tail -3 logs/chandra_ocr.log
else
    echo -e "${YELLOW}⊘${NC} Лог-файл еще не создан"
fi
echo ""

# Итог
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                 Тестирование завершено                     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📋 Полезные команды:"
echo ""
echo "  # Посмотреть информацию об API"
echo "  curl $BASE_URL/"
echo ""
echo "  # Проверить здоровье"
echo "  curl $BASE_URL/health | jq"
echo ""
echo "  # Распознать документ"
echo "  curl -X POST $BASE_URL/ocr \\"
echo "       -F 'file=@document.pdf' \\"
echo "       --output result.txt"
echo ""
echo "  # С метаданными (JSON)"
echo "  curl -X POST $BASE_URL/ocr/json \\"
echo "       -F 'file=@document.pdf' | jq"
echo ""
