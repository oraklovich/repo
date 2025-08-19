#!/usr/bin/env python3

import requests

websites = ['https://google.com', 'https://yahoo.com', 'https://github.com']

for site in websites:
    try:
        response = requests.get(site, timeout=5)
        # Проверяем, что статус-код ответа равен 200 (OK)
        if response.status_code == 200:
            print(f"{site} is UP! Status code: {response.status_code}")
        else:
            print(f"{site} is DOWN! Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        # Если произошла любая ошибка (нет сети, таймаут и т.д.)
        print(f"{site} is DOWN! Error: {e}")

