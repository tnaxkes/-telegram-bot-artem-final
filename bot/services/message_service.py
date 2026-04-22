import logging
from pathlib import Path

from telegram import Bot, InlineKeyboardMarkup

from bot.models.content import FunnelStep


logger = logging.getLogger(__name__)
START_IMAGE_PATH = Path('/Users/grigory/Downloads/photo_2026-04-22 18.57.31.jpeg')


class MessageService:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_start_media(
        self,
        chat_id: int,
        file_id: str | None,
        fallback_text: str | None,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> None:
        if file_id:
            try:
                await self.bot.send_video_note(chat_id=chat_id, video_note=file_id)
                if fallback_text:
                    if START_IMAGE_PATH.exists():
                        with START_IMAGE_PATH.open('rb') as image_file:
                            await self.bot.send_photo(chat_id=chat_id, photo=image_file, caption=fallback_text, reply_markup=reply_markup)
                    else:
                        await self.bot.send_message(chat_id=chat_id, text=fallback_text, reply_markup=reply_markup)
                return
            except Exception as exc:
                logger.warning('Failed to send video note, falling back to image/text: %s', exc)
        if START_IMAGE_PATH.exists():
            with START_IMAGE_PATH.open('rb') as image_file:
                await self.bot.send_photo(chat_id=chat_id, photo=image_file, caption=fallback_text, reply_markup=reply_markup)
            return
        if fallback_text:
            await self.bot.send_message(chat_id=chat_id, text=fallback_text, reply_markup=reply_markup)

    async def send_step(self, chat_id: int, step: FunnelStep, reply_markup: InlineKeyboardMarkup | None = None) -> None:
        text = step.body if not step.title else f'{step.title}\n\n{step.body}'
        image_path_value = step.metadata.get('image_path') if step.metadata else None
        if image_path_value:
            image_path = Path(str(image_path_value))
            if image_path.exists():
                with image_path.open('rb') as image_file:
                    await self.bot.send_photo(chat_id=chat_id, photo=image_file, caption=text, reply_markup=reply_markup)
                return
        await self.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

    async def send_text(self, chat_id: int, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
        await self.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
