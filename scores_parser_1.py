#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from database import get_db_connection
import psycopg2

def upsert_prediction_to_db(home_team, away_team, match_time, league, odd):
    """
    Вставляет или обновляет прогноз в таблицу predictions
    """
    conn = get_db_connection()
    cur = conn.cursor()

    prediction_type = "btts"        # тип прогноза
    prediction_value = "yes"        # чтобы не было NULL
    source = "scores24.live"

    try:
        cur.execute(
            """
            UPDATE predictions
               SET league = %s,
                   odd = %s,
                   prediction_type = %s,
                   prediction_value = %s,
                   source = %s,
                   updated_at = NOW()
             WHERE home_team = %s
               AND away_team = %s
               AND match_time = %s
            """,
            (league, odd, prediction_type, prediction_value, source, home_team, away_team, match_time),
        )
        if cur.rowcount == 0:
            cur.execute(
                """
                INSERT INTO predictions
                    (home_team, away_team, match_time, league, odd, prediction_type, prediction_value, source, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """,
                (home_team, away_team, match_time, league, odd, prediction_type, prediction_value, source),
            )
            print(f"✅ Вставлен прогноз: {home_team} vs {away_team} @ {match_time} (odd={odd})")
        else:
            print(f"♻️ Обновлён прогноз: {home_team} vs {away_team} @ {match_time} (odd={odd})")

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка при сохранении прогноза: {e}")
    finally:
        cur.close()
        conn.close()


def parse_scores24(save_to_db=True):
    """Парсит данные с scores24.live о матчах 'Обе забьют'"""
    url = "https://scores24.live/ru/trends/soccer?trendsMarketSlug=btts"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    matches = []

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        scripts = soup.find_all('script')

        for script in scripts:
            if script.string and 'URQL_DATA' in script.string:
                json_match = re.search(r'window\.URQL_DATA\s*=\s*JSON\.parse\("(.+?)"\)', script.string)
                if not json_match:
                    continue

                json_str = json_match.group(1)
                json_str = json_str.encode().decode('unicode_escape')
                data = json.loads(json_str)

                for key, value in data.items():
                    if 'TrendList' in str(value):
                        trend_data = json.loads(value['data'])
                        edges = trend_data['TrendList']['edges']
                        
                        for edge in edges:
                            node = edge['node']
                            match_data = node['match']
                            
                            team1 = match_data['teams'][0]['name']
                            team2 = match_data['teams'][1]['name']
                            match_time = datetime.fromisoformat(match_data['matchDate'].replace("Z", "+00:00"))
                            league = match_data['uniqueTournamentName']
                            odd = float(node['groups'][0]['minOdd'])
                            
                            matches.append({
                                'home_team': team1,
                                'away_team': team2,
                                'match_time': match_time,
                                'league': league,
                                'odd': odd,
                                'prediction_type': 'btts',
                                'prediction_value': 'yes',
                                'source': 'scores24.live',
                                'timestamp': datetime.now().isoformat()
                            })

                            if save_to_db:
                                upsert_prediction_to_db(team1, team2, match_time, league, odd)
                        
                        break
                break

        return matches
        
    except Exception as e:
        print(f"❌ Ошибка при парсинге: {e}")
        return []


if __name__ == '__main__':
    data = parse_scores24()
    print(f"\n📊 Найдено прогнозов: {len(data)}")
    for match in data[:5]:
        print(f"{match['home_team']} vs {match['away_team']} @ {match['match_time']} | odd={match['odd']}")
