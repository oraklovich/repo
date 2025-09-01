# results_json_parser.py
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, timedelta
from database import get_db_connection

def parse_results_from_json(date_str):
    """
    Парсит результаты матчей за конкретную дату используя JSON из script тегов
    (аналогично парсингу прогнозов)
    """
    url = f"https://scores24.live/ru/soccer/{date_str}"
    print(f"🕸️  Парсим URL: {url}")
    
    try:
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Ошибка при запросе: {e}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    results = []
    
    # Ищем script теги с данными (как при парсинге прогнозов)
    script_tags = soup.find_all('script')
    
    for script in script_tags:
        if 'window.URQL_DATA' in script.text:
            print("✅ Нашли window.URQL_DATA в результатах")
            
            # Извлекаем JSON данные
            json_data = re.search(r'window\.URQL_DATA\s*=\s*({.*?});', script.text, re.DOTALL)
            
            if json_data:
                try:
                    data = json.loads(json_data.group(1))
                    print(f"📊 Загружено {len(data)} записей из URQL_DATA")
                    
                    # Ищем матчи с результатами
                    for key, value in data.items():
                        if 'match' in key.lower() or 'event' in key.lower():
                            try:
                                match_data = value.get('data', {})
                                
                                # Проверяем, что есть результат
                                if (match_data.get('homeScore') is not None and 
                                    match_data.get('awayScore') is not None):
                                    
                                    # Получаем основные данные матча
                                    home_team = match_data.get('homeTeam', {}).get('name', '')
                                    away_team = match_data.get('awayTeam', {}).get('name', '')
                                    home_score = match_data.get('homeScore')
                                    away_score = match_data.get('awayScore')
                                    
                                    # Получаем статус матча
                                    status_type = match_data.get('status', {}).get('type', '')
                                    status_name = match_data.get('status', {}).get('name', '')
                                    
                                    # Получаем время матча
                                    start_date = match_data.get('startDate', '')
                                    if start_date:
                                        try:
                                            match_time = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                                        except:
                                            match_time = None
                                    else:
                                        match_time = None
                                    
                                    result = {
                                        'home_team': home_team,
                                        'away_team': away_team,
                                        'home_score': home_score,
                                        'away_score': away_score,
                                        'status': status_name or status_type,
                                        'match_time': match_time,
                                        'league': match_data.get('tournament', {}).get('name', ''),
                                        'source': 'json'
                                    }
                                    
                                    results.append(result)
                                    print(f"   ⚽ {home_team} {home_score}:{away_score} {away_team} ({status_name})")
                                    
                            except Exception as e:
                                print(f"❌ Ошибка обработки матча: {e}")
                                continue
                    
                except json.JSONDecodeError as e:
                    print(f"❌ Ошибка парсинга JSON: {e}")
                    continue
                except Exception as e:
                    print(f"❌ Общая ошибка: {e}")
                    continue
    
    print(f"📊 Найдено матчей с результатами: {len(results)}")
    return results

def get_matches_without_results():
    """Возвращает список матчей из predictions без результатов в results."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    query = """
        SELECT p.id, p.home_team, p.away_team, p.match_time
        FROM predictions p
        WHERE NOT EXISTS (
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
        print(f"❌ Ошибка при сохранении: {e}")
        conn.rollback()
        return False
    
    finally:
        cur.close()
        conn.close()

def main():
    print("🧠 ПАРСЕР РЕЗУЛЬТАТОВ (JSON логика)")
    print("=" * 60)
    
    # 1. Парсим результаты за несколько последних дней
    dates_to_parse = [
        (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
        (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    ]
    
    all_results = []
    for date_str in dates_to_parse:
        print(f"\n📅 Парсим дату: {date_str}")
        results = parse_results_from_json(date_str)
        all_results.extend(results)
    
    print(f"\n📊 Всего найдено результатов: {len(all_results)}")
    
    # 2. Получаем матчи из БД без результатов
    print("\n📦 Загружаем матчи из базы данных...")
    matches = get_matches_without_results()
    print(f"✅ Найдено матчей без результатов: {len(matches)}")
    
    if not matches:
        print("🔚 Нет матчей для обработки")
        return
    
    # 3. Сопоставляем и сохраняем результаты
    print("\n🔍 Сопоставляем матчи...")
    saved_count = 0
    
    for match in matches:
        match_id, home_team, away_team, match_time = match
        print(f"\n🔍 Ищем: {home_team} vs {away_team}")
        
        found = False
        for result in all_results:
            # Ищем по совпадению названий команд
            if (result['home_team'].lower() == home_team.lower() and 
                result['away_team'].lower() == away_team.lower()):
                
                print(f"   ✅ Найден результат: {result['home_score']}:{result['away_score']}")
                
                if save_result_to_db(
                    home_team, away_team, match_time,
                    result['home_score'], result['away_score'],
                    result['status']
                ):
                    saved_count += 1
                    found = True
                break
        
        if not found:
            print(f"   ❌ Результат не найден в JSON данных")
    
    print(f"\n🎯 ИТОГ: обработано {len(matches)} матчей, сохранено {saved_count} результатов")
    print("🔚 Парсинг завершен.")

if __name__ == '__main__':
    main()
