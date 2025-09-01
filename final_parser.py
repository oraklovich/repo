# final_parser.py
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from models import get_db_session, Prediction, init_db
import time

def safe_db_operation(func):
    """Декоратор для безопасных операций с БД"""
    def wrapper(*args, **kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"✗ Ошибка БД (попытка {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)  # Ждем перед повторной попыткой
                else:
                    raise e
    return wrapper

@safe_db_operation
def save_prediction(session, home_team, away_team, match_time, prediction_value):
    """Безопасно сохраняет прогноз в БД"""
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
        session.commit()
        return True
    return False

def parse_btts_predictions():
    """Парсит прогнозы 'Обе забьют'"""
    print("🚀 Запуск парсера прогнозов...")
    
    try:
        url = "https://scores24.live/ru/trends?trendsMarketSlug=btts"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        print(f"📡 Запрашиваем данные с: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"✅ Страница загружена (статус: {response.status_code})")
        
        # Парсим HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Ищем script тег с URQL_DATA
        script_tags = soup.find_all('script')
        
        target_script = None
        for script in script_tags:
            if script.string and 'window.URQL_DATA' in script.string:
                target_script = script
                break
        
        if not target_script:
            print("❌ Не найден script тег с данными")
            return 0
        
        # Извлекаем JSON данные
        script_content = target_script.string.strip()
        start_marker = 'window.URQL_DATA=JSON.parse("'
        end_marker = '");'
        
        start_idx = script_content.find(start_marker)
        end_idx = script_content.find(end_marker, start_idx)
        
        if start_idx == -1 or end_idx == -1:
            print("❌ Не удалось извлечь JSON данные")
            return 0
        
        json_str = script_content[start_idx + len(start_marker):end_idx]
        
        # Декодируем экранированные символы
        try:
            json_str = json_str.encode('utf-8').decode('unicode_escape')
        except:
            print("⚠ Не удалось декодировать unicode escape")
        
        # Парсим JSON
        urql_data = json.loads(json_str)
        
        # Ищем матчи в TopPredictionMatches
        matches_data = []
        for key, value in urql_data.items():
            if isinstance(value, dict) and 'data' in value:
                try:
                    data_value = json.loads(value['data']) if isinstance(value['data'], str) else value['data']
                    if isinstance(data_value, dict) and 'TopPredictionMatches' in data_value:
                        matches_data = data_value['TopPredictionMatches']
                        break
                except:
                    continue
        
        if not matches_data:
            print("❌ Не найдены матчи для обработки")
            return 0
        
        print(f"📊 Найдено матчей: {len(matches_data)}")
        
        # Подключаемся к БД
        session = get_db_session()
        new_count = 0
        
        # Обрабатываем каждый матч
        for i, match in enumerate(matches_data):
            try:
                # Извлекаем данные о командах
                teams = match.get('teams', [])
                if len(teams) >= 2:
                    home_team = teams[0].get('name', 'Unknown Home').strip()
                    away_team = teams[1].get('name', 'Unknown Away').strip()
                else:
                    continue  # Пропускаем матчи без команд
                
                # Извлекаем время матча
                if 'matchDate' in match:
                    match_time = datetime.fromisoformat(match['matchDate'].replace('Z', '+00:00'))
                else:
                    continue  # Пропускаем матчи без времени
                
                # Сохраняем в БД
                if save_prediction(session, home_team, away_team, match_time, "Yes"):
                    print(f"✅ [{i+1}/{len(matches_data)}] Добавлен: {home_team} vs {away_team}")
                    new_count += 1
                else:
                    print(f"⚠ [{i+1}/{len(matches_data)}] Уже в БД: {home_team} vs {away_team}")
                    
            except Exception as e:
                print(f"❌ [{i+1}/{len(matches_data)}] Ошибка обработки матча: {e}")
                continue
        
        session.close()
        print(f"\n🎉 Парсинг завершен! Добавлено {new_count} новых прогнозов")
        return new_count
        
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    # Инициализируем БД
    init_db()
    
    # Запускаем парсинг
    parse_btts_predictions()
