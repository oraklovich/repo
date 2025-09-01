# simple_parser_db.py
from models import get_db_session, Prediction, init_db
from datetime import datetime

def test_save_to_db():
    """Простая функция для теста сохранения данных в БД"""
    print("Тестируем сохранение данных в БД...")
    
    # Создаем сессию БД
    session = get_db_session()
    
    # Создаем тестовый прогноз
    test_prediction = Prediction(
        home_team="Тестовая команда 1",
        away_team="Тестовая команда 2", 
        match_time=datetime.now(),
        prediction_value="Yes",
        source="test"
    )
    
    # Добавляем в сессию и сохраняем
    session.add(test_prediction)
    session.commit()
    
    print("✓ Тестовые данные сохранены в БД")
    
    # Проверяем, что данные действительно сохранились
    count = session.query(Prediction).count()
    print(f"✓ Всего записей в таблице predictions: {count}")
    
    session.close()

if __name__ == "__main__":
    # Инициализируем БД
    init_db()
    
    # Тестируем сохранение
    test_save_to_db()
