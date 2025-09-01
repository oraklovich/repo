# database.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Конфигурация подключения к БД
DB_CONFIG = {
    "dbname": "football_db",
    "user": "football_user", 
    "password": "mysecretpassword",
    "host": "localhost",
    "port": "5432"
}

def get_db_connection():
    """Устанавливает и возвращает соединение с PostgreSQL."""
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('POSTGRES_DB', DB_CONFIG['dbname']),
            user=os.getenv('POSTGRES_USER', DB_CONFIG['user']),
            password=os.getenv('POSTGRES_PASSWORD', DB_CONFIG['password']),
            host=os.getenv('POSTGRES_HOST', DB_CONFIG['host']),
            port=os.getenv('POSTGRES_PORT', DB_CONFIG['port'])
        )
        return conn
    except Exception as e:
        print(f"Ошибка подключения к БД: {e}")
        raise e

if __name__ == '__main__':
    try:
        conn = get_db_connection()
        print("✅ Подключение к БД успешно установлено!")
        conn.close()
    except Exception as e:
        print("❌ Не удалось подключиться к БД.")
