# check_pending_matches.py
import sys
from database import get_db_connection  # Импортируем вашу функцию для подключения

def main():
    print("🕵️  Проверяем матчи, требующие сбора результатов...")

    try:
        # Подключаемся к БД
        conn = get_db_connection()
        cur = conn.cursor()
        print("✅ Подключение к БД установлено.")
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        sys.exit(1)

    # SQL-запрос для поиска матчей без результатов
    query = """
        SELECT p.id, p.home_team, p.away_team, p.match_time
        FROM predictions p
        WHERE p.match_time < NOW()
        AND NOT EXISTS (
            SELECT 1 
            FROM results r 
            WHERE r.home_team = p.home_team 
            AND r.away_team = p.away_team 
            AND r.match_time = p.match_time
        )
        ORDER BY p.match_time DESC;
    """
    try:
        cur.execute(query)
        pending_matches = cur.fetchall()
        count = len(pending_matches)
        print(f"✅ Найдено матчей без результатов: {count}")

        if count > 0:
            print("\nСписок матчей для обработки:")
            print("-" * 50)
            for match in pending_matches:
                id, home_team, away_team, match_time = match
                print(f"ID: {id} | {home_team} vs {away_team} | {match_time}")

    except Exception as e:
        print(f"❌ Ошибка выполнения запроса к БД: {e}")
    finally:
        # Всегда закрываем соединение
        cur.close()
        conn.close()
        print("\n✅ Соединение с БД закрыто.")

if __name__ == '__main__':
    main()
