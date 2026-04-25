# Funnel Telegram Bot

Локальный режим для теста на Mac:
- одна команда запуска бота
- локальная SQLite база в `data/bot.db`
- follow-up через встроенный `JobQueue`
- без обязательного Redis/PostgreSQL

## Быстрый старт

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 run_bot.py
```

Перед запуском заполни `BOT_TOKEN` в `.env`.

## Google Sheets лиды и автодожимы

- В `.env` заполни `GOOGLE_SHEET_ID` значением ID таблицы Google Sheets.
- В `.env` заполни `GOOGLE_SERVICE_ACCOUNT_JSON` полным JSON service account в одну строку.
- Выдай service account доступ к нужной Google Sheets таблице.
- В таблице должна быть колонка `tg_name`, в ней хранится именно `chat_id` пользователя из Telegram.
- При `/start` бот записывает `chat_id` в колонку `tg_name` без дублей.
- Автодожимы запускаются автоматически 2 раза в день через встроенный планировщик бота.

## Полезные команды

- `/start` — начать воронку
- `/stop` — остановить цепочку
- `/submit_application` — симулировать оставленную заявку и остановить дожимы
