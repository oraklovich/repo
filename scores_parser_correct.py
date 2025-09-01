# scores_parser_correct.py
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from models import get_db_session, Prediction, init_db

def parse_btts_predictions():
    """Парсит прогнозы 'Обе забьют' с правильного URL"""
    print("Начинаем парсинг прогнозов с правильного URL...")
    
    try:
        # Правильный URL для парсинга
        url = "https://scores24.live/ru/trends?trendsMarketSlug=btts"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Делаем запрос к сайту
        print(f"Запрашиваем URL: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # Проверяем успешность запроса
        
        print(f"✓ Страница загружена успешно (статус: {response.status_code})")
        
        # Парсим HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Ищем script тег с данными
        print("Ищем данные в script тегах...")
        script_tags = soup.find_all('script')
        
        target_script = None
        for i, script in enumerate(script_tags):
            if script.string and 'window.__DATA__' in script.string:
                target_script = script
                print(f"✓ Найден целевой script тег (номер {i})")
                break
        
        if not target_script:
            print("✗ Не найден script тег с window.__DATA__")
            print("Доступные script теги:")
            for i, script in enumerate(script_tags):
                if script.string:
                    print(f"Script {i}: длина {len(script.string)} символов")
                    if len(script.string) > 100:
                        print(f"  Начало: {script.string[:100]}...")
            return 0
        
        # Извлекаем и парсим JSON данные
        print("Парсим JSON данные...")
        script_content = target_script.string
        json_str = script_content.split('window.__DATA__ = ', 1)[1].strip()
        data_json = json.loads(json_str)
        
        # Ищем данные о матчах в структуре JSON
        print("Анализируем структуру JSON...")
        
        # Выводим ключи для понимания структуры
        print("Ключи в data_json:", list(data_json.keys()))
        if 'data' in data_json:
            print("Ключи в data:", list(data_json['data'].keys()))
        
        # Пробуем найти матчи в разных возможных местах
        matches_data = []
        
        # Вариант 1: data -> trends -> matches
        if 'data' in data_json and 'trends' in data_json['data']:
            trends = data_json['data']['trends']
            if 'matches' in trends:
                matches_data = trends['matches']
                print(f"✓ Найдено матчей в data.trends.matches: {len(matches_data)}")
        
        # Вариант 2: data -> matches
        if not matches_data and 'data' in data_json and 'matches' in data_json['data']:
            matches_data = data_json['data']['matches']
            print(f"✓ Найдено матчей в data.matches: {len(matches_data)}")
        
        # Вариант 3: прямо в корне
        if not matches_data and 'matches' in data_json:
            matches_data = data_json['matches']
            print(f"✓ Найдено матчей в корне: {len(matches_data)}")
        
        if not matches_data:
            print("✗ Не удалось найти данные о матчах в JSON")
            print("Доступные ключи в JSON:")
            import pprint
            pprint.pprint(list(data_json.keys()))
            if 'data' in data_json:
                pprint.pprint(list(data_json['data'].keys()))
            return 0
        
        # Подключаемся к БД
        session = get_db_session()
        new_count = 0
        
        print(f"Обрабатываем {len(matches_data)} матчей...")
        
        # Обрабатываем каждый матч
        for i, match in enumerate(matches_data[:5]):  # Первые 5 для теста
            try:
                print(f"\n--- Матч {i+1} ---")
                print("Структура матча:", list(match.keys()))
                
                # Извлекаем данные о командах (адаптируй под реальную структуру)
                home_team = match.get('home_team', {}).get('name', 'Unknown Home')
                away_team = match.get('away_team', {}).get('name', 'Unknown Away')
                
                # Извлекаем время матча
                match_time = None
                if 'time' in match:
                    match_time = datetime.fromtimestamp(match['time'])
                elif 'start_time' in match:
                    match_time = datetime.fromtimestamp(match['start_time'])
                else:
                    match_time = datetime.now()
                
                # Извлекаем прогноз (коэффициент или вероятность)
                prediction_value = "Yes"  # По умолчанию
                if 'odds' in match:
                    prediction_value = str(match['odds'])
                elif 'probability' in match:
                    prediction_value = str(match['probability'])
                
                print(f"Команды: {home_team} vs {away_team}")
                print(f"Время: {match_time}")
                print(f"Прогноз: {prediction_value}")
                
                # Проверяем, есть ли уже такой матч в БД
                existing = session.query(Prediction).filter_by(
                    home_team=home_team,
                    away_team=away_team, 
                    match_time=match_time
                ).first()
                
                if not existing:
                    # Создаем новую запись
                    new_prediction = Prediction(
                        home_team=home_team,
                        away_team=away_team,
                        match_time=match_time,
                        prediction_value=prediction_value,
                        source="scores24.live"
                    )
                    session.add(new_prediction)
                    new_count += 1
                    print(f"✓ Добавлен в БД: {home_team} vs {away_team}")
                else:
                    print(f"✓ Уже в БД: {home_team} vs {away_team}")
                    
            except Exception as e:
                print(f"✗ Ошибка обработки матча: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Сохраняем все изменения
        session.commit()
        session.close()
        
        print(f"\nГотово! Добавлено {new_count} новых прогнозов")
        return new_count
        
    except Exception as e:
        print(f"Ошибка при парсинге: {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    # Инициализируем БД
    init_db()
    
    # Запускаем парсинг
    parse_btts_predictions()
