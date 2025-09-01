# scores_parser_fixed.py
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
        
        # Извлекаем JSON данные более аккуратно
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
            # Пробуем декодировать unicode escape
            json_str = json_str.encode('utf-8').decode('unicode_escape')
        except:
            print("⚠ Не удалось декодировать unicode escape, используем как есть")
        
        # Сохраняем сырые данные для отладки
        with open('debug_urql_data.json', 'w', encoding='utf-8') as f:
            f.write(json_str)
        print("✓ Сырые JSON данные сохранены в debug_urql_data.json")
        
        # Пробуем распарсить JSON
        try:
            urql_data = json.loads(json_str)
            print("✓ JSON успешно распарсен")
        except json.JSONDecodeError as e:
            print(f"✗ Ошибка парсинга JSON: {e}")
            print("Пробуем найти первый валидный JSON объект...")
            
            # Ищем начало первого JSON объекта
            brace_start = json_str.find('{')
            brace_end = json_str.rfind('}')
            
            if brace_start != -1 and brace_end != -1:
                json_str = json_str[brace_start:brace_end+1]
                try:
                    urql_data = json.loads(json_str)
                    print("✓ Усеченный JSON успешно распарсен")
                except:
                    print("✗ Не удалось распарсить даже усеченный JSON")
                    return 0
            else:
                print("✗ Не найдены фигурные скобки в JSON")
                return 0
        
        # Анализируем структуру данных
        print("Анализируем структуру данных...")
        print(f"Тип данных: {type(urql_data)}")
        
        if isinstance(urql_data, dict):
            print(f"Ключи: {list(urql_data.keys())}")
            
            # Ищем данные о матчах
            matches_data = []
            
            # Пробуем разные возможные пути к данным
            for key, value in urql_data.items():
                if isinstance(value, dict) and 'data' in value:
                    try:
                        data_value = json.loads(value['data']) if isinstance(value['data'], str) else value['data']
                        if isinstance(data_value, dict) and 'TrendFilter' in data_value:
                            trend_data = data_value['TrendFilter']
                            if 'matches' in trend_data:
                                matches_data = trend_data['matches']
                                print(f"✓ Найдено матчей: {len(matches_data)}")
                                break
                    except:
                        continue
            
            if not matches_data:
                print("✗ Не удалось найти матчи в структуре данных")
                return 0
            
            # Подключаемся к БД
            session = get_db_session()
            new_count = 0
            
            print(f"\nОбрабатываем {len(matches_data)} матчей...")
            
            # Обрабатываем каждый матч
            for i, match in enumerate(matches_data[:5]):  # Первые 5 для теста
                try:
                    print(f"\n--- Матч {i+1} ---")
                    print(f"Структура матча: {list(match.keys())}")
                    
                    # Извлекаем данные о командах
                    home_team = match.get('homeTeam', {}).get('name', 'Unknown Home') if isinstance(match.get('homeTeam'), dict) else 'Unknown Home'
                    away_team = match.get('awayTeam', {}).get('name', 'Unknown Away') if isinstance(match.get('awayTeam'), dict) else 'Unknown Away'
                    
                    # Извлекаем время матча
                    match_time = None
                    if 'startTime' in match:
                        match_time = datetime.fromtimestamp(match['startTime'])
                    else:
                        match_time = datetime.now()
                    
                    # Извлекаем прогноз
                    prediction_value = "Yes"
                    if 'trend' in match and isinstance(match['trend'], dict):
                        if 'odds' in match['trend']:
                            prediction_value = str(match['trend']['odds'])
                    
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
            
        else:
            print(f"✗ Неожиданный тип данных: {type(urql_data)}")
            return 0
        
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
