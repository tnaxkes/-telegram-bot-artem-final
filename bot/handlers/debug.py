from telegram import Update
from telegram.ext import ContextTypes


async def log_incoming_file_ids(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Temporary debug code to capture file_id values in Railway logs.
    message = update.message
    if message is None:
        return

    if message.photo:
        print(f"photo file_id: {message.photo[-1].file_id}")

    if message.video_note:
        print(f"video_note file_id: {message.video_note.file_id}")
