# exact_results_parser.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from database import get_db_connection

def parse_exact_results(date_str):
    """
    Парсит результаты матчей используя точную структуру HTML
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
    
    # Ищем все контейнеры матчей по классу
    match_containers = soup.find_all('div', class_='sc-17qxh4e-1')
    
    print(f"🔍 Найдено контейнеров матчей: {len(match_containers)}")
    
    for container in match_containers:
        try:
            # Извлекаем названия команд
            home_team_elem = container.find('div', class_='esbhnW')
            away_team_elem = container.find('div', class_='iztCrh')
            
            if not home_team_elem or not away_team_elem:
                # Альтернативный поиск по классам с названиями команд
                team_elems = container.find_all('div', class_='sc-17qxh4e-10')
                if len(team_elems) >= 2:
                    home_team = team_elems[0].get_text(strip=True)
                    away_team = team_elems[1].get_text(strip=True)
                else:
                    continue
            else:
                home_team = home_team_elem.get_text(strip=True)
                away_team = away_team_elem.get_text(strip=True)
            
            # Извлекаем счет - ищем основной счет
            score_container = container.find('div', class_='sc-pvs6fr-0')
            if score_container:
                home_score_elem = score_container.find('div', class_='bAhpay')
                away_score_elem = score_container.find('div', class_='hdZfIn')
                
                if home_score_elem and away_score_elem:
                    home_score = home_score_elem.get_text(strip=True)
                    away_score = away_score_elem.get_text(strip=True)
                else:
                    home_score = '?'
                    away_score = '?'
            else:
                home_score = '?'
                away_score = '?'
            
            # Извлекаем статус матча
            status_elem = container.find('div', class_='sc-1p31vt4-0')
            status = status_elem.get_text(strip=True) if status_elem else 'Неизвестно'
            
            result = {
                'home_team': home_team,
                'away_team': away_team,
                'home_score': home_score,
                'away_score': away_score,
                'score': f"{home_score}:{away_score}",
                'status': status
            }
            
            results.append(result)
            print(f"   ⚽ {home_team} {home_score}:{away_score} {away_team} ({status})")
            
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
        # Преобразуем score в числа если возможно
        try:
            home_score_int = int(home_score) if home_score != '?' else None
            away_score_int = int(away_score) if away_score != '?' else None
        except ValueError:
            home_score_int = None
            away_score_int = None
        
        cur.execute("""
            INSERT INTO results (home_team, away_team, match_time, home_score, away_score, status, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (home_team, away_team, match_time, home_score_int, away_score_int, status))
        
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
    print("🎯 ТОЧНЫЙ ПАРСЕР РЕЗУЛЬТАТОВ")
    print("=" * 60)
    
    # Парсим результаты за нужную дату
    results = parse_exact_results("2025-08-23")
    print(f"📊 Найдено результатов: {len(results)}")
    
    # Получаем матчи из БД
    matches = get_matches_without_results()
    print(f"✅ Найдено матчей без результатов: {len(matches)}")
    
    # Сопоставляем и сохраняем
    saved_count = 0
    for match in matches:
        match_id, home_team, away_team, match_time = match
        print(f"\n🔍 Ищем: {home_team} vs {away_team}")
        
        found = False
        for result in results:
            # Сравниваем названия команд
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
            print(f"   ❌ Результат не найден")
    
    print(f"\n🎯 ИТОГ: сохранено {saved_count} результатов")

if __name__ == '__main__':
    main()
