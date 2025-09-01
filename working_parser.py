# working_parser.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import re
from database import get_db_connection

def parse_results_for_date(date_str):
    """
    Парсит страницу с результатами матчей за конкретную дату.
    Возвращает список словарей с найденными результатами.
    """
    url = f"https://scores24.live/ru/soccer/{date_str}"
    print(f"🕸️  Парсим URL: {url}")
    
    try:
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Ошибка при запросе к {url}: {e}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    results = []
    
    # Правильные селекторы для scores24.live
    # Ищем все матчи (контейнеры с матчами)
    match_containers = soup.find_all('div', class_='sm')
    
    print(f"🔍 Найдено контейнеров матчей: {len(match_containers)}")
    
    for container in match_containers:
        try:
            # Извлекаем команды
            teams_elem = container.find('a', class_='teams')
            if teams_elem:
                teams_text = teams_elem.get_text(strip=True)
                # Разделяем команды по тире или другим разделителям
                if ' - ' in teams_text:
                    home_team, away_team = teams_text.split(' - ', 1)
                else:
                    continue
            else:
                continue
            
            # Извлекаем счет
            score_elem = container.find('div', class_='sc')
            score_text = score_elem.get_text(strip=True) if score_elem else '?-?'
            
            # Извлекаем статус матча
            status_elem = container.find('div', class_='st')
            status = status_elem.get_text(strip=True) if status_elem else 'Неизвестно'
            
            # Парсим счет
            home_score = None
            away_score = None
            
            if score_text and ':' in score_text and score_text != '-:-':
                try:
                    home_score, away_score = map(int, score_text.split(':'))
                except ValueError:
                    pass
            
            # Извлекаем время матча
            time_elem = container.find('div', class_='dt')
            match_time_str = time_elem.get_text(strip=True) if time_elem else ''
            
            result = {
                'home_team': home_team.strip(),
                'away_team': away_team.strip(),
                'score': score_text,
                'home_score': home_score,
                'away_score': away_score,
                'status': status,
                'time': match_time_str,
                'date': date_str
            }
            
            results.append(result)
            print(f"   ⚽ {home_team} {score_text} {away_team} ({status})")
            
        except Exception as e:
            print(f"❌ Ошибка при парсинге матча: {e}")
            continue
    
    return results

def get_matches_without_results():
    """Возвращает список матчей из predictions без результатов в results."""
    conn = get_db_connection()
    cur = conn.cursor()
    
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
    
    cur.execute(query)
    matches = cur.fetchall()
    cur.close()
    conn.close()
    return matches

def save_result_to_db(home_team, away_team, match_time, home_score, away_score, status):
    """Сохраняет результат матча в базу данных."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO results (home_team, away_team, match_time, home_score, away_score, status, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (home_team, away_team, match_time) 
            DO UPDATE SET 
                home_score = EXCLUDED.home_score,
                away_score = EXCLUDED.away_score,
                status = EXCLUDED.status,
                updated_at = NOW()
        """, (home_team, away_team, match_time, home_score, away_score, status))
        
        conn.commit()
        print(f"✅ Результат сохранен: {home_team} {home_score}:{away_score} {away_team}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при сохранении результата: {e}")
        conn.rollback()
        return False
    
    finally:
        cur.close()
        conn.close()

def main():
    print("🕵️  ЗАПУСК РАБОЧЕГО ПАРСЕРА РЕЗУЛЬТАТОВ")
    print("=" * 60)
    
    # 1. Сначала тестируем на актуальных датах
    print("🧪 ТЕСТИРУЕМ НА АКТУАЛЬНЫХ ДАТАХ:")
    
    # Парсим вчерашние и сегодняшние матчи
    dates_to_test = [
        (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        datetime.now().strftime("%Y-%m-%d")
    ]
    
    all_parsed_results = []
    for date_str in dates_to_test:
        print(f"\n📅 Парсим дату: {date_str}")
        results = parse_results_for_date(date_str)
        all_parsed_results.extend(results)
        time.sleep(1)
    
    print(f"\n📊 Всего спарсено матчей: {len(all_parsed_results)}")
    
    # 2. Теперь получаем матчи из БД
    print("\n" + "=" * 60)
    print("📦 ОБРАБОТКА МАТЧЕЙ ИЗ БАЗЫ ДАННЫХ:")
    
    matches = get_matches_without_results()
    print(f"✅ Найдено матчей без результатов: {len(matches)}")
    
    if not matches:
        print("🔚 Нет матчей для обработки.")
        return
    
    # 3. Пытаемся найти и сохранить результаты
    saved_count = 0
    for match in matches:
        match_id, home_team, away_team, match_time = match
        print(f"\n🔍 Ищем результат для: {home_team} vs {away_team}")
        
        # Ищем в спарсенных результатах
        for result in all_parsed_results:
            # Простое сравнение названий команд
            if (result['home_team'].lower() == home_team.lower() and 
                result['away_team'].lower() == away_team.lower()):
                
                if save_result_to_db(
                    home_team, away_team, match_time,
                    result['home_score'], result['away_score'],
                    result['status']
                ):
                    saved_count += 1
                break
        else:
            print(f"   ❌ Результат не найден на сайте")
    
    print(f"\n🎯 ИТОГ: обработано {len(matches)} матчей, сохранено {saved_count} результатов")
    print("🔚 Парсинг завершен.")

if __name__ == '__main__':
    main()
