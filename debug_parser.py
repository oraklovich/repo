#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
import json
import re

url = 'https://scores24.live/ru/trends/soccer?trendsMarketSlug=btts'
headers = {'User-Agent': 'Mozilla/5.0'}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

scripts = soup.find_all('script')
for script in scripts:
    if script.string and 'URQL_DATA' in script.string:
        json_match = re.search(r'window\.URQL_DATA\s*=\s*JSON\.parse\("(.+?)"\)', script.string)
        if json_match:
            try:
                json_str = json_match.group(1)
                json_str = json_str.encode().decode('unicode_escape')
                data = json.loads(json_str)
                
                # Ищем ключ с TrendList
                for key, value in data.items():
                    if 'TrendList' in str(value):
                        trend_data = json.loads(value['data'])
                        edges = trend_data['TrendList']['edges']
                        
                        print('=== СТРУКТУРА ПЕРВОГО МАТЧА ===')
                        first_match = edges[0]['node']
                        print(json.dumps(first_match, ensure_ascii=False, indent=2))
                        
                        print('\n=== КЛЮЧИ ПЕРВОГО МАТЧА ===')
                        print(list(first_match.keys()))
                        
                        # Пробуем найти названия команд
                        if 'teams' in first_match:
                            print('\n=== КОМАНДЫ ===')
                            for team in first_match['teams']:
                                print(team)
                        
            except Exception as e:
                print(f'Ошибка: {e}')
        break
