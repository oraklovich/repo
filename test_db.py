# test_db.py
from models import init_db, get_db_session

# Инициализируем БД (создаем таблицы)
init_db()
print("✓ Таблицы созданы")

# Тестируем подключение
try:
    session = get_db_session()
    print("✓ Подключение к БД успешно")
    session.close()
except Exception as e:
    print(f"✗ Ошибка подключения: {e}")
