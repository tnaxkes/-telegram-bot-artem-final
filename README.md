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

## Полезные команды

- `/start` — начать воронку
- `/stop` — остановить цепочку
- `/submit_application` — симулировать оставленную заявку и остановить дожимы
