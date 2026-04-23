import logging

from telegram import Bot, InlineKeyboardMarkup

from bot.models.content import FunnelStep


logger = logging.getLogger(__name__)
START_IMAGE_FILE_ID = 'AgACAgIAAxkBAAIBfWnpmc4Tjkn9HGQqfqEW79jZPJ93AALbFmsbvUFJS1O2t6nwc_N8AQADAgADeQADOwQ'


class MessageService:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def _send_photo_by_id(
        self,
        chat_id: int,
        photo_id: str | None,
        caption: str | None = None,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> bool:
        if not photo_id:
            return False
        await self.bot.send_photo(
            chat_id=chat_id,
            photo=photo_id,
            caption=caption if caption else None,
            reply_markup=reply_markup,
            parse_mode='HTML' if caption else None,
        )
        return True

    async def send_start_media(
        self,
        chat_id: int,
        file_id: str | None,
        fallback_text: str | None,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> None:
        sent_video_note = False
        if file_id:
            try:
                await self.bot.send_video_note(chat_id=chat_id, video_note=file_id)
                sent_video_note = True
            except Exception as exc:
                logger.exception(
                    'Failed to send start video note. chat_id=%s video_note_file_id=%s error=%s',
                    chat_id,
                    file_id,
                    exc,
                )

        await self._send_photo_by_id(
            chat_id=chat_id,
            photo_id=START_IMAGE_FILE_ID,
            caption=fallback_text,
            reply_markup=reply_markup,
        )

        if file_id and not sent_video_note:
            logger.warning('Start video note was not sent, only start photo screen was delivered.')

    async def send_step(self, chat_id: int, step: FunnelStep, reply_markup: InlineKeyboardMarkup | None = None) -> None:
        text = step.body if not step.title else f'{step.title}\n\n{step.body}'
        image_file_id = None
        if step.metadata:
            image_file_id = step.metadata.get('image_file_id') or step.metadata.get('photo')
        if step.code == 'lesson_1' and image_file_id and text:
            await self.bot.send_photo(
                chat_id=chat_id,
                photo=str(image_file_id),
                caption=text,
                reply_markup=reply_markup,
                parse_mode='HTML',
            )
            return
        if image_file_id and step.code == 'lesson_2' and text:
            await self._send_photo_by_id(
                chat_id=chat_id,
                photo_id=str(image_file_id),
                caption=text,
                reply_markup=reply_markup,
            )
            return
        if image_file_id:
            await self._send_photo_by_id(chat_id=chat_id, photo_id=str(image_file_id))
        await self.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

    async def send_text(self, chat_id: int, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
        await self.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
