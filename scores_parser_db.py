# scores_parser_db.py
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from models import get_db_session, Prediction, init_db

def parse_and_save_predictions():
    """Парсит прогнозы и сохраняет их в БД"""
    print("Начинаем парсинг прогнозов с сайта...")
    
    try:
        # Твой URL для парсинга
        url = "https://scores24.live/ru/betting-tips/both-teams-to-score"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Делаем запрос к сайту
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Парсим HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Ищем script тег с данными (адаптируй под твой парсер)
        script_tag = soup.find('script', text=re.compile('window\.__DATA__'))
        if not script_tag:
            print("Не найден script тег с данными")
            return 0
        
        # Извлекаем JSON данные
        data_json = json.loads(script_tag.string.split('=', 1)[1])
        matches_data = data_json['data']['matches']
        
        # Подключаемся к БД
        session = get_db_session()
        new_count = 0
        
        print(f"Найдено {len(matches_data)} матчей для обработки...")
        
        # Обрабатываем каждый матч
        for match in matches_data:
            try:
                # ИЗМЕНИ ЭТУ ЧАСТЬ ПОД СТРУКТУРУ ТВОЕГО JSON!
                home_team = match['home_team']['name']
                away_team = match['away_team']['name']
                match_time = datetime.fromtimestamp(match['time'])
                
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
                        prediction_value="Yes",  # Предполагаем "Обе забьют = Да"
                        source="scores24.live"
                    )
                    session.add(new_prediction)
                    new_count += 1
                    print(f"✓ Добавлен: {home_team} vs {away_team}")
                    
            except Exception as e:
                print(f"✗ Ошибка обработки матча: {e}")
                continue
        
        # Сохраняем все изменения
        session.commit()
        session.close()
        
        print(f"Готово! Добавлено {new_count} новых прогнозов")
        return new_count
        
    except Exception as e:
        print(f"Ошибка при парсинге: {e}")
        return 0

if __name__ == "__main__":
    # Инициализируем БД
    init_db()
    
    # Запускаем парсинг
    parse_and_save_predictions()
