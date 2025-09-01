#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

def parse_scores24():
    """Парсит данные с scores24.live о матчах 'Обе забьют' из JSON"""
    url = "https://scores24.live/ru/trends/soccer?trendsMarketSlug=btts"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        matches = []
        
        # Ищем JSON данные
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'URQL_DATA' in script.string:
                json_match = re.search(r'window\.URQL_DATA\s*=\s*JSON\.parse\("(.+?)"\)', script.string)
                if json_match:
                    json_str = json_match.group(1)
                    json_str = json_str.encode().decode('unicode_escape')
                    data = json.loads(json_str)
                    
                    # Ищем ключ с TrendList
                    for key, value in data.items():
                        if 'TrendList' in str(value):
                            trend_data = json.loads(value['data'])
                            edges = trend_data['TrendList']['edges']
                            
                            for edge in edges:
                                node = edge['node']
                                match_data = node['match']
                                
                                # Формируем информацию о матче
                                team1 = match_data['teams'][0]['name']
                                team2 = match_data['teams'][1]['name']
                                match_time = match_data['matchDate']
                                league = match_data['uniqueTournamentName']
                                odd = node['groups'][0]['minOdd']
                                
                                matches.append({
                                    'teams': f"{team1} vs {team2}",
                                    'time': match_time,
                                    'league': league,
                                    'probability': f"{odd:.2f}",
                                    'timestamp': datetime.now().isoformat()
                                })
                                
                            break
                    break
                
        return matches
        
    except Exception as e:
        print(f"Ошибка при парсинге: {e}")
        return []

if __name__ == '__main__':
    data = parse_scores24()
    print(f"Найдено матчей: {len(data)}")
    for match in data[:3]:
        print(match)
