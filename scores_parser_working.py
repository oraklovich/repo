# scores_parser_working.py
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from models import get_db_session, Prediction, init_db

def parse_btts_predictions():
    """Парсит прогнозы 'Обе забьют' с правильного URL"""
    print("Начинаем парсинг прогнозов...")
    
    try:
        # Правильный URL для парсинга
        url = "https://scores24.live/ru/trends?trendsMarketSlug=btts"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Connection': 'keep-alive'
        }
        
        # Делаем запрос к сайту
        print(f"Запрашиваем URL: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"✓ Страница загружена успешно (статус: {response.status_code})")
        
        # Парсим HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Ищем script тег с URQL_DATA
        print("Ищем window.URQL_DATA...")
        script_tags = soup.find_all('script')
        
        target_script = None
        for i, script in enumerate(script_tags):
            if script.string and 'window.URQL_DATA' in script.string:
                target_script = script
                print(f"✓ Найден целевой script тег с URQL_DATA")
                break
        
        if not target_script:
            print("✗ Не найден script тег с window.URQL_DATA")
            return 0
        
        # Извлекаем JSON данные
        print("Извлекаем JSON данные...")
        script_content = target_script.string.strip()
        
        # Находим начало и конец JSON данных
        start_marker = 'window.URQL_DATA=JSON.parse("'
        end_marker = '");'
        
        start_idx = script_content.find(start_marker)
        if start_idx == -1:
            print("✗ Не найден начальный маркер JSON")
            return 0
        
        start_idx += len(start_marker)
        end_idx = script_content.find(end_marker, start_idx)
        
        if end_idx == -1:
            print("✗ Не найден конечный маркер JSON")
            return 0
        
        # Извлекаем JSON строку
        json_str = script_content[start_idx:end_idx]
        
        # Декодируем экранированные символы
        try:
            json_str = json_str.encode('utf-8').decode('unicode_escape')
        except:
            print("⚠ Не удалось декодировать unicode escape, используем как есть")
        
        # Парсим JSON
        urql_data = json.loads(json_str)
        print("✓ JSON успешно распарсен")
        
        # Ищем матчи в ключе -2139603846 -> TopPredictionMatches
        matches_data = []
        
        for key, value in urql_data.items():
            if isinstance(value, dict) and 'data' in value:
                try:
                    data_value = json.loads(value['data']) if isinstance(value['data'], str) else value['data']
                    if isinstance(data_value, dict) and 'TopPredictionMatches' in data_value:
                        matches_data = data_value['TopPredictionMatches']
                        print(f"✓ Найдено матчей в TopPredictionMatches: {len(matches_data)}")
                        break
                except:
                    continue
        
        if not matches_data:
            print("✗ Не удалось найти матчи в TopPredictionMatches")
            return 0
        
        # Подключаемся к БД
        session = get_db_session()
        new_count = 0
        
        print(f"\nОбрабатываем {len(matches_data)} матчей...")
        
        # Обрабатываем каждый матч
        for i, match in enumerate(matches_data):
            try:
                print(f"\n--- Матч {i+1} ---")
                
                # Извлекаем данные о командах
                teams = match.get('teams', [])
                if len(teams) >= 2:
                    home_team = teams[0].get('name', 'Unknown Home')
                    away_team = teams[1].get('name', 'Unknown Away')
                else:
                    home_team = 'Unknown Home'
                    away_team = 'Unknown Away'
                
                # Извлекаем время матча
                match_time = None
                if 'matchDate' in match:
                    # Преобразуем дату из формата "2024-01-20T18:00:00Z"
                    match_date_str = match['matchDate']
                    match_time = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
                else:
                    match_time = datetime.now()
                
                # Для BTTS прогноза используем значение "Yes"
                prediction_value = "Yes"
                
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
                continue
        
        # Сохраняем все изменения
        session.commit()
        session.close()
        
        print(f"\n🎉 Готово! Добавлено {new_count} новых прогнозов")
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
