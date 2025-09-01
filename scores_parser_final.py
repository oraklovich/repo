# scores_parser_final.py
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
        
        # Извлекаем и парсим JSON данные
        print("Парсим JSON данные из URQL_DATA...")
        script_content = target_script.string.strip()
        
        # Извлекаем JSON строку
        json_str = script_content.split('window.URQL_DATA=JSON.parse("', 1)[1]
        json_str = json_str.rsplit('");', 1)[0]
        
        # Декодируем экранированные символы
        json_str = json_str.encode('utf-8').decode('unicode_escape')
        
        # Парсим JSON
        urql_data = json.loads(json_str)
        
        # Анализируем структуру данных
        print("Анализируем структуру URQL_DATA...")
        
        # Ищем ключи в данных
        first_key = list(urql_data.keys())[0]
        print(f"Первый ключ в URQL_DATA: {first_key}")
        
        # Получаем данные по первому ключу
        trend_data = urql_data[first_key]
        if 'data' in trend_data:
            trend_data = json.loads(trend_data['data'])
        
        print(f"Ключи в trend_data: {list(trend_data.keys())}")
        
        # Ищем матчи в структуре
        matches_data = []
        
        if 'TrendFilter' in trend_data:
            trend_filter = trend_data['TrendFilter']
            if 'matches' in trend_filter:
                matches_data = trend_filter['matches']
                print(f"✓ Найдено матчей: {len(matches_data)}")
        
        if not matches_data:
            print("✗ Не удалось найти матчи в структуре данных")
            print("Доступные ключи:")
            for key in trend_data.keys():
                print(f"  {key}")
                if key == 'TrendFilter':
                    for subkey in trend_data[key].keys():
                        print(f"    {subkey}")
            return 0
        
        # Подключаемся к БД
        session = get_db_session()
        new_count = 0
        
        print(f"\nОбрабатываем {len(matches_data)} матчей...")
        
        # Обрабатываем каждый матч
        for i, match in enumerate(matches_data[:10]):  # Первые 10 для теста
            try:
                print(f"\n--- Матч {i+1} ---")
                
                # Извлекаем данные о командах
                home_team = match.get('homeTeam', {}).get('name', 'Unknown Home')
                away_team = match.get('awayTeam', {}).get('name', 'Unknown Away')
                
                # Извлекаем время матча
                match_time = None
                if 'startTime' in match:
                    match_time = datetime.fromtimestamp(match['startTime'])
                else:
                    match_time = datetime.now()
                
                # Извлекаем прогноз (коэффициент)
                prediction_value = "Yes"  # По умолчанию
                if 'trend' in match and 'odds' in match['trend']:
                    prediction_value = str(match['trend']['odds'])
                
                print(f"Команды: {home_team} vs {away_team}")
                print(f"Время: {match_time}")
                print(f"Коэффициент: {prediction_value}")
                
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
