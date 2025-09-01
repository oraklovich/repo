#!/usr/bin/env python3

import os
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Подключаем SQLAlchemy
from models import get_db_session, Prediction, init_db

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
SCORES_API_URL = os.environ.get('SCORES_API_URL', 'http://scores-parser-service:5001')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '⚽ Футбольный бот прогнозов!\n\n'
        'Доступные команды:\n'
        '/btts - Матчи "Обе забьют"\n'
        '/help - Помощь'
    )


def save_prediction_to_db(home_team, away_team, match_time, prediction_value="Yes", source="telegram_bot"):
    """
    Сохраняет прогноз в БД, если его ещё нет
    """
    session = get_db_session()
    existing = session.query(Prediction).filter_by(
        home_team=home_team,
        away_team=away_team,
        match_time=match_time
    ).first()

    if not existing:
        pred = Prediction(
            home_team=home_team,
            away_team=away_team,
            match_time=match_time,
            prediction_value=prediction_value,
            source=source
        )
        session.add(pred)
        session.commit()
        print(f"✅ В БД добавлен прогноз: {home_team} vs {away_team} ({match_time})")
    else:
        print(f"⚠ Прогноз уже есть в БД: {home_team} vs {away_team} ({match_time})")

    session.close()


async def btts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get(f"{SCORES_API_URL}/matches/btts", timeout=15)
        data = response.json()
        
        if not data['matches']:
            await update.message.reply_text('❌ Нет данных о матчах')
            return
            
        message = "⚽ *Матчи \"Обе забьют\":*\n\n"

        # Сохраняем матчи в БД
        for match in data['matches']:
            message += f"• {match['teams']}\n"
            message += f"  🕐 {match['time']} | 📊 {match['probability']}\n\n"

            # Разбиваем команды (ожидаем формат "Home - Away")
            if " - " in match['teams']:
                home_team, away_team = match['teams'].split(" - ", 1)
            else:
                continue  # если формат другой, пропускаем

            # Парсим время матча
            try:
                match_time = datetime.fromisoformat(match['time'])
            except Exception:
                match_time = datetime.utcnow()

            # Сохраняем в predictions
            save_prediction_to_db(home_team.strip(), away_team.strip(), match_time)

        message += f"_Обновлено: {data['matches'][0]['timestamp']}_"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f'❌ Ошибка: {str(e)}')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '🤖 Команды бота:\n'
        '/start - Начать работу\n'
        '/btts - Прогноз "Обе забьют"\n'
        '/help - Эта справка'
    )


def main():
    # Инициализация БД
    init_db()

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("btts", btts_command))
    app.add_handler(CommandHandler("help", help_command))
    
    print("Football bot starting...")
    app.run_polling()


if __name__ == '__main__':
    main()
