# check_table_structure.py
from database import get_db_connection

def main():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Узнаем структуру таблицы results
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'results'
        ORDER BY ordinal_position;
    """)
    
    columns = cur.fetchall()
    print("Структура таблицы 'results':")
    for col in columns:
        print(f"  {col[0]} ({col[1]})")
    
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
