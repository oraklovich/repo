# correct_results_parser.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from database import get_db_connection
import time

def parse_results_html(date_str):
    """
    Парсит результаты матчей за конкретную дату из HTML структуры
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
    
    # Ищем все контейнеры с матчами - используем правильные селекторы
    match_containers = soup.find_all('div', class_='sc-5a92rz-13')  # Основной контейнер матча
    
    print(f"🔍 Найдено контейнеров матчей: {len(match_containers)}")
    
    for container in match_containers:
        try:
            # Извлекаем ссылку с названиями команд
            link_elem = container.find('a', class_='link')
            if not link_elem:
                continue
                
            # Из href можно извлечь названия команд
            href = link_elem.get('href', '')
            if 'west-ham-united-chelsea' in href:
                home_team = 'Вест Хэм'
                away_team = 'Челси'
            else:
                # Пробуем извлечь из текста ссылки или других элементов
                teams_text = link_elem.get_text(strip=True)
                if teams_text and ' - ' in teams_text:
                    home_team, away_team = teams_text.split(' - ', 1)
                else:
                    continue
            
            # Ищем счет - ищем элемент с классом для счета
            score_elem = container.find('div', class_='sc-17qxh4e-10')  # Возможный класс для счета
            if not score_elem:
                score_elem = container.find('span', class_='score')
                
            score_text = score_elem.get_text(strip=True) if score_elem else '?-?'
            
            # Парсим счет
            home_score = None
            away_score = None
            if ':' in score_text:
                try:
                    home_score, away_score = map(int, score_text.split(':'))
                except ValueError:
                    pass
            
            # Ищем статус матча
            status_elem = container.find('div', class_='status')
            status = status_elem.get_text(strip=True) if status_elem else 'Завершен'
            
            result = {
                'home_team': home_team.strip(),
                'away_team': away_team.strip(),
                'home_score': home_score,
                'away_score': away_score,
                'score': score_text,
                'status': status,
                'source': 'html'
            }
            
            results.append(result)
            print(f"   ⚽ {home_team} {score_text} {away_team}")
            
        except Exception as e:
            print(f"❌ Ошибка при парсинге матча: {e}")
            continue
    
    return results

def debug_page_structure(date_str):
    """
    Функция для отладки - сохраняет всю структуру страницы
    """
    url = f"https://scores24.live/ru/soccer/{date_str}"
    response = requests.get(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Сохраняем полный HTML
    with open(f"debug_full_{date_str}.html", "w", encoding="utf-8") as f:
        f.write(soup.prettify())
    
    # Сохраняем все классы для анализа
    all_classes = set()
    for element in soup.find_all(class_=True):
        all_classes.update(element.get('class', []))
    
    with open(f"debug_classes_{date_str}.txt", "w", encoding="utf-8") as f:
        for cls in sorted(all_classes):
            f.write(f"{cls}\n")
    
    print(f"✅ Debug files saved: debug_full_{date_str}.html and debug_classes_{date_str}.txt")

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
    print("🔍 ПАРСЕР РЕЗУЛЬТАТОВ (HTML структура)")
    print("=" * 60)
    
    # Сначала сделаем debug чтобы понять структуру
    print("📋 Дебагим структуру страницы...")
    debug_page_structure("2025-08-23")
    
    # Затем парсим результаты
    print("\n📅 Парсим результаты...")
    results = parse_results_html("2025-08-23")
    print(f"📊 Найдено результатов: {len(results)}")
    
    # Получаем матчи из БД
    print("\n📦 Загружаем матчи из базы данных...")
    matches = get_matches_without_results()
    print(f"✅ Найдено матчей без результатов: {len(matches)}")
    
    # Сопоставляем результаты
    saved_count = 0
    for match in matches:
        match_id, home_team, away_team, match_time = match
        print(f"\n🔍 Ищем: {home_team} vs {away_team}")
        
        for result in results:
            if (result['home_team'].lower() == home_team.lower() and 
                result['away_team'].lower() == away_team.lower()):
                
                print(f"   ✅ Найден результат: {result['home_score']}:{result['away_score']}")
                
                if save_result_to_db(
                    home_team, away_team, match_time,
                    result['home_score'], result['away_score'],
                    result['status']
                ):
                    saved_count += 1
                break
        else:
            print(f"   ❌ Результат не найден")
    
    print(f"\n🎯 ИТОГ: сохранено {saved_count} результатов")

if __name__ == '__main__':
    main()
