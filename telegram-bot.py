#!/usr/bin/env python3

import requests
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Конфигурация (будем брать из переменных окружения)
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHECKER_SERVICE_URL = os.environ.get('CHECKER_SERVICE_URL', 'http://website-checker-service/check')

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Привет! Я бот для проверки сайтов. Используй /check чтобы узнать статус.')

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Делаем запрос к НАШЕМУ СЕРВИСУ в Kubernetes
        response = requests.get(f"{CHECKER_SERVICE_URL}", timeout=10)
        data = response.json()
        
        message = "📊 *Статус сайтов:*\n"
        for site in data['results']:
            status_icon = "🟢" if site['status'] == 'UP' else "🔴"
            message += f"{status_icon} {site['url']} - {site['status']} (код: {site.get('status_code', 'N/A')})\n"
            
        await update.message.reply_text(message, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f'❌ Ошибка при проверке сайтов: {e}')

def main():
    if not TELEGRAM_TOKEN:
        print("ERROR: TELEGRAM_TOKEN environment variable is not set!")
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("check", check_command))
    
    print("Bot is starting...")
    app.run_polling()

if __name__ == '__main__':
    main()
