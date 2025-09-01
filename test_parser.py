# test_parser.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time

def parse_results_for_date(date_str):
    """
    Парсит страницу с результатами матчей за конкретную дату.
    Возвращает список словарей с найденными результатами.
    """
    url = f"https://scores24.live/ru/soccer/{date_str}"
    print(f"🕸️  Парсим URL: {url}")
    
    try:
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Ошибка при запросе к {url}: {e}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    results = []
    
    # Сохраняем HTML для отладки
    with open(f"debug_{date_str}.html", "w", encoding="utf-8") as f:
        f.write(soup.prettify())
    print(f"✅ HTML сохранен в debug_{date_str}.html")
    
    # Пробуем разные селекторы для поиска матчей
    selectors = [
        'div.sm', 'div.event', 'div.match', 'div.game', 
        'div[class*="match"]', 'div[class*="event"]',
        'tr', 'table tbody tr'
    ]
    
    for selector in selectors:
        match_containers = soup.select(selector)
        print(f"🔍 Селектор '{selector}': найдено {len(match_containers)} элементов")
        
        if match_containers:
            # Посмотрим структуру первого элемента
            print(f"📋 Пример структуры первого элемента ({selector}):")
            print(str(match_containers[0])[:200] + "..." if len(str(match_containers[0])) > 200 else str(match_containers[0]))
            break
    
    # Дополнительный поиск по классам
    print("\n🔍 Поиск по классам:")
    for class_name in ['sm', 'event', 'match', 'game', 'row', 'item']:
        elements = soup.find_all(class_=class_name)
        if elements:
            print(f"Класс '{class_name}': {len(elements)} элементов")
            if len(elements) > 0:
                print(f"Пример: {str(elements[0])[:100]}...")
    
    # Поиск всех таблиц
    tables = soup.find_all('table')
    print(f"\n📊 Найдено таблиц: {len(tables)}")
    for i, table in enumerate(tables[:3]):
        print(f"Таблица {i+1}:")
        print(str(table)[:200] + "..." if len(str(table)) > 200 else str(table))
    
    return results

def main():
    print("🧪 ТЕСТИРУЕМ ПАРСЕР НА РЕАЛЬНЫХ ДАННЫХ")
    print("=" * 50)
    
    # Тестируем на вчерашней дате
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"📅 Тестовая дата: {yesterday}")
    
    results = parse_results_for_date(yesterday)
    print(f"\n📊 Найдено результатов: {len(results)}")
    
    print("\n🔍 Дополнительная информация:")
    print("1. Откройте файл debug_*.html в браузере для изучения структуры")
    print("2. Посмотрите на классы элементов с матчами")
    print("3. Определите правильные CSS-селекторы для парсинга")
    
    # Также пробуем сегодняшнюю дату
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n📅 Дополнительно: сегодняшняя дата {today}")
    parse_results_for_date(today)
    
    print("\n🔚 Тест завершен. Изучите debug-файлы для определения правильных селекторов.")

if __name__ == '__main__':
    main()
