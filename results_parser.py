# results_parser.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from database import get_db_connection
import time
import re

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
        """, (home_team, away_team, match_time, home_score, away_score, status))
        
        conn.commit()
        print(f"✅ Результат сохранен: {home_team} {home_score}:{away_score} {away_team}")
        
    except Exception as e:
        print(f"❌ Ошибка при сохранении результата: {e}")
        conn.rollback()
    
    finally:
        cur.close()
        conn.close()

def parse_results_for_date(date_str):
    """
    Парсит страницу с результатами матчей за конкретную дату.
    Возвращает список словарей с найденными результатами.
    """
    url = f"https://scores24.live/ru/soccer/{date_str}"
    print(f"🕸️  Парсим URL: {url}")
    
    try:
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Ошибка при запросе к {url}: {e}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    results = []
    
    # Ищем все контейнеры с матчами
    match_containers = soup.find_all('div', class_='sm')
    
    for container in match_containers:
        try:
            # Извлекаем названия команд
            teams_elem = container.find('div', class_='teams')
            if not teams_elem:
                continue
                
            teams_text = teams_elem.get_text(strip=True)
            teams = teams_text.split(' - ')
            if len(teams) != 2:
                continue
                
            home_team = teams[0].strip()
            away_team = teams[1].strip()
            
            # Извлекаем счет
            score_elem = container.find('div', class_='sc')
            score_text = score_elem.get_text(strip=True) if score_elem else None
            
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
            
            results.append({
                'home_team': home_team,
                'away_team': away_team,
                'score': score_text,
                'home_score': home_score,
                'away_score': away_score,
                'status': status
            })
            
        except Exception as e:
            print(f"❌ Ошибка при парсинге контейнера: {e}")
            continue
    
    return results

def find_and_save_results(matches, all_parsed_results):
    """Ищет совпадения матчей и сохраняет результаты в БД."""
    saved_count = 0
    
    for match in matches:
        match_id, home_team, away_team, match_time = match
        date_str = match_time.strftime("%Y-%m-%d")
        
        # Ищем результат для этого матча
        for result in all_parsed_results:
            # Простое сравнение названий команд
            if (result['home_team'] == home_team and result['away_team'] == away_team):
                
                # Сохраняем результат в БД
                save_result_to_db(
                    home_team, 
                    away_team, 
                    match_time,
                    result['home_score'],
                    result['away_score'],
                    result['status']
                )
                saved_count += 1
                break
        
        # Также попробуем найти по частичному совпадению названий
        for result in all_parsed_results:
            if (home_team in result['home_team'] and away_team in result['away_team']):
                save_result_to_db(
                    home_team, 
                    away_team, 
                    match_time,
                    result['home_score'],
                    result['away_score'],
                    result['status']
                )
                saved_count += 1
                break
    
    return saved_count

def main():
    print("🕵️  Начинаем парсинг результатов матчей...")
    
    # 1. Получаем матчи без результатов
    matches = get_matches_without_results()
    print(f"✅ Найдено матчей для обработки: {len(matches)}")
    
    if not matches:
        print("🔚 Нет матчей для обработки.")
        return
    
    # 2. Группируем матчи по датам
    dates_to_parse = set()
    for match in matches:
        match_time = match[3]
        date_str = match_time.strftime("%Y-%m-%d")
        dates_to_parse.add(date_str)
    
    print(f"📅 Будем парсить результаты за даты: {', '.join(dates_to_parse)}")
    
    # 3. Парсим результаты для каждой даты
    all_parsed_results = []
    for date_str in dates_to_parse:
        results = parse_results_for_date(date_str)
        print(f"📊 Найдено результатов за {date_str}: {len(results)}")
        all_parsed_results.extend(results)
        time.sleep(2)  # Пауза между запросами
    
    # 4. Ищем и сохраняем результаты
    saved_count = find_and_save_results(matches, all_parsed_results)
    
    print(f"\n🎯 Итог: обработано {len(matches)} матчей, сохранено {saved_count} результатов")
    print("🔚 Парсинг завершен.")

if __name__ == '__main__':
    main()
