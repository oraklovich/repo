#!/usr/bin/env python3

from flask import Flask, jsonify
import requests
from datetime import datetime
import os

app = Flask(__name__)

# Список сайтов для проверки
WEBSITES = ['https://google.com', 'https://yahoo.com', 'https://github.com', 'https://httpbin.org/status/500']

def check_site(url):
    """Проверяет доступность сайта и возвращает результат"""
    try:
        response = requests.get(url, timeout=5)
        return {
            'url': url,
            'status': 'UP' if response.status_code == 200 else 'DOWN',
            'status_code': response.status_code,
            'response_time_ms': round(response.elapsed.total_seconds() * 1000, 2)
        }
    except requests.exceptions.RequestException as e:
        return {
            'url': url,
            'status': 'DOWN',
            'error': str(e),
            'status_code': None,
            'response_time_ms': None
        }

@app.route('/')
def index():
    """Главная страница с приветствием"""
    return jsonify({"message": "Website Checker API is running!", "timestamp": datetime.utcnow().isoformat()})

@app.route('/health')
def health_check():
    """Эндпоинт для проверки здоровья самого приложения (используется в Kubernetes)"""
    return jsonify({"status": "healthy"})

@app.route('/check')
def check_all_sites():
    """Основной эндпоинт для проверки всех сайтов"""
    results = []
    for url in WEBSITES:
        result = check_site(url)
        results.append(result)
    
    return jsonify({
        "timestamp": datetime.utcnow().isoformat(),
        "results": results
    })

if __name__ == '__main__':
    # Получаем порт из переменной окружения (это важно для Kubernetes)
    port = int(os.environ.get('PORT', 5000))
    # Запускаем приложение на всех интерфейсах ('0.0.0.0') 
    app.run(host='0.0.0.0', port=port, debug=False)#!/usr/bin/env python3

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

