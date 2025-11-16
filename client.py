#!/usr/bin/env python3
"""
Клиент для Chandra OCR API

Примеры использования:

    # Распознать документ
    python client.py document.pdf
    
    # Сохранить в файл
    python client.py document.pdf --output result.txt
    
    # С метаданными
    python client.py document.pdf --json
    
    # Указать другой сервер
    python client.py document.pdf --url http://server:8000
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    print("❌ Требуется библиотека requests")
    print("Установите: pip install requests")
    sys.exit(1)


class ChandraOCRClient:
    """Клиент для Chandra OCR API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
    
    def ocr(
        self,
        file_path: str,
        method: str = "hf",
        include_images: bool = False,
        include_headers: bool = False
    ) -> str:
        """
        Распознать документ и получить текст
        
        Args:
            file_path: Путь к файлу
            method: Метод обработки (hf или vllm)
            include_images: Извлекать изображения
            include_headers: Включать колонтитулы
            
        Returns:
            Распознанный текст
        """
        url = f"{self.base_url}/ocr"
        
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {
                'method': method,
                'include_images': include_images,
                'include_headers': include_headers
            }
            
            response = requests.post(url, files=files, data=data)
            response.raise_for_status()
            
            return response.text
    
    def ocr_json(
        self,
        file_path: str,
        method: str = "hf",
        include_images: bool = False,
        include_headers: bool = False
    ) -> dict:
        """
        Распознать документ и получить JSON с метаданными
        
        Args:
            file_path: Путь к файлу
            method: Метод обработки (hf или vllm)
            include_images: Извлекать изображения
            include_headers: Включать колонтитулы
            
        Returns:
            Словарь с результатами
        """
        url = f"{self.base_url}/ocr/json"
        
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {
                'method': method,
                'include_images': include_images,
                'include_headers': include_headers
            }
            
            response = requests.post(url, files=files, data=data)
            response.raise_for_status()
            
            return response.json()
    
    def health(self) -> dict:
        """Проверить здоровье сервиса"""
        url = f"{self.base_url}/health"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()


def main():
    parser = argparse.ArgumentParser(
        description='Клиент для Chandra OCR API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  %(prog)s document.pdf
  %(prog)s scan.jpg --output result.txt
  %(prog)s form.pdf --json --pretty
  %(prog)s invoice.pdf --url http://192.168.1.100:8000
  %(prog)s --health
        """
    )
    
    parser.add_argument(
        'file',
        nargs='?',
        help='Файл для распознавания (PDF, JPG, PNG и др.)'
    )
    
    parser.add_argument(
        '--url',
        default='http://localhost:8000',
        help='URL API сервера (default: http://localhost:8000)'
    )
    
    parser.add_argument(
        '--method',
        choices=['hf', 'vllm'],
        default='hf',
        help='Метод обработки (default: hf)'
    )
    
    parser.add_argument(
        '--include-images',
        action='store_true',
        help='Извлекать изображения из документа'
    )
    
    parser.add_argument(
        '--include-headers',
        action='store_true',
        help='Включать колонтитулы в результат'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Получить результат в JSON формате с метаданными'
    )
    
    parser.add_argument(
        '--pretty',
        action='store_true',
        help='Форматировать JSON с отступами'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Сохранить результат в файл'
    )
    
    parser.add_argument(
        '--health',
        action='store_true',
        help='Проверить здоровье сервиса'
    )
    
    args = parser.parse_args()
    
    # Создание клиента
    client = ChandraOCRClient(base_url=args.url)
    
    # Проверка здоровья
    if args.health:
        try:
            health = client.health()
            print(json.dumps(health, indent=2, ensure_ascii=False))
            
            if health.get('status') == 'healthy':
                print("\n✓ Сервис работает нормально")
                sys.exit(0)
            else:
                print("\n✗ Сервис неисправен")
                sys.exit(1)
                
        except Exception as e:
            print(f"✗ Ошибка подключения: {e}")
            sys.exit(1)
    
    # Проверка наличия файла
    if not args.file:
        parser.print_help()
        sys.exit(1)
    
    file_path = Path(args.file)
    
    if not file_path.exists():
        print(f"✗ Файл не найден: {file_path}")
        sys.exit(1)
    
    print(f"📄 Файл: {file_path.name}")
    print(f"📊 Размер: {file_path.stat().st_size / 1024:.1f} КБ")
    print(f"🌐 Сервер: {args.url}")
    print(f"⚙️  Метод: {args.method}")
    print("\n🔄 Обработка...")
    
    try:
        # Распознавание
        if args.json:
            result = client.ocr_json(
                str(file_path),
                method=args.method,
                include_images=args.include_images,
                include_headers=args.include_headers
            )
            
            # Форматирование вывода
            if args.pretty:
                output = json.dumps(result, indent=2, ensure_ascii=False)
            else:
                output = json.dumps(result, ensure_ascii=False)
            
            # Вывод метрик
            print(f"\n✓ Готово!")
            print(f"  Символов: {len(result.get('text', ''))}")
            print(f"  Изображений: {result.get('images_count', 0)}")
            print(f"  Время: {result.get('processing_time', 0):.2f}s")
            print()
            
        else:
            output = client.ocr(
                str(file_path),
                method=args.method,
                include_images=args.include_images,
                include_headers=args.include_headers
            )
            
            print(f"\n✓ Готово! Распознано {len(output)} символов\n")
        
        # Сохранение или вывод
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(output, encoding='utf-8')
            print(f"💾 Сохранено в: {output_path}")
        else:
            print(output)
    
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Ошибка запроса: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
