import logging

from telegram import Bot, InlineKeyboardMarkup

from bot.models.content import FunnelStep


logger = logging.getLogger(__name__)
START_IMAGE_FILE_ID = 'AgACAgIAAxkBAAIBfWnpmc4Tjkn9HGQqfqEW79jZPJ93AALbFmsbvUFJS1O2t6nwc_N8AQADAgADeQADOwQ'


class MessageService:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def _send_photo_by_id(self, chat_id: int, photo_id: str | None) -> bool:
        if not photo_id:
            return False
        await self.bot.send_photo(chat_id=chat_id, photo=photo_id)
        return True

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
                await self._send_photo_by_id(chat_id=chat_id, photo_id=START_IMAGE_FILE_ID)
                if fallback_text:
                    await self.bot.send_message(chat_id=chat_id, text=fallback_text, reply_markup=reply_markup)
                return
            except Exception as exc:
                logger.warning('Failed to send video note, falling back to image/text: %s', exc)
        await self._send_photo_by_id(chat_id=chat_id, photo_id=START_IMAGE_FILE_ID)
        if fallback_text:
            await self.bot.send_message(chat_id=chat_id, text=fallback_text, reply_markup=reply_markup)
            return

    async def send_step(self, chat_id: int, step: FunnelStep, reply_markup: InlineKeyboardMarkup | None = None) -> None:
        text = step.body if not step.title else f'{step.title}\n\n{step.body}'
        image_file_id = None
        if step.metadata:
            image_file_id = step.metadata.get('image_file_id') or step.metadata.get('photo')
        if image_file_id:
            await self._send_photo_by_id(chat_id=chat_id, photo_id=str(image_file_id))
        await self.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

    async def send_text(self, chat_id: int, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
        await self.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
