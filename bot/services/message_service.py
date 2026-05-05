import logging
import asyncio

from telegram import Bot, InlineKeyboardMarkup

from bot.models.content import FunnelStep


logger = logging.getLogger(__name__)
START_VIDEO_NOTE_FILE_ID = 'DQACAgIAAxkBAAFH1Kxp6QYzX3l_vAh-RYv8Rq9q_ParLQACU50AAiu2CEt8yzWa2Z6E2jsE'
START_IMAGE_FILE_ID = 'AgACAgIAAxkBAAFIx89p-PRYgvsrxMmQrA75AwHKMFQCeAACjBdrGwqVyUuWo0JtASeAXQEAAwIAA3kAAzsE'
LESSON_1_IMAGE_FILE_ID = 'AgACAgIAAxkBAAFIx8Np-PP7nof9G5G80fUl4Rz8YjSxwAACiRdrGwqVyUtmVV6JjymF_QEAAwIAA3kAAzsE'
LESSON_SHARED_IMAGE_FILE_ID = 'AgACAgIAAxkBAAFIIvJp7jWcGDHZwJ1DdIGzE0f-w1TB4QAClhVrGyjacEslkBs-q8YAAXMBAAMCAAN5AAM7BA'
LESSON_3_IMAGE_FILE_ID = 'AgACAgIAAxkBAAFIIyJp7jfBPQ46ycdpbNaomv6uTnJv_AACuxVrGyjacEuC836M3HAllwEAAwIAA3kAAzsE'
LESSON_2_NUDGE_1_VIDEO_FILE_ID = 'BAACAgIAAxkBAAFIIwtp7jcS9bL4fqPDOMmd8CpdMoi3VgACqKQAAijacEvJ4KQQk1h2fTsE'
LESSON_2_NUDGE_2_PHOTO_FILE_ID = 'AgACAgIAAxkBAAFIIypp7jg1VP1Zd_ziPsWhsuqLrXuXNQACwxVrGyjacEsCLXd5J7eNnQEAAwIAA3gAAzsE'
LESSON_2_NUDGE_3_PHOTO_FILE_ID = 'AgACAgIAAxkBAAFIIzVp7jh-Lfe8dXbZ0gKR2xKTgRVnOAACxBVrGyjacEvCTFYRLbAt1QEAAwIAA3kAAzsE'
LESSON_3_NUDGE_1_PHOTO_FILE_ID = 'AgACAgIAAxkBAAFIIzpp7jjl290SKabSQ3Yr4opkxNJtggACxxVrGyjacEvRlryBmJoZjwEAAwIAA3kAAzsE'
LESSON_3_NUDGE_2_VIDEO_FILE_ID = 'BAACAgIAAxkBAAFII49p7j0dJiTgjVRwX1vbSVGROAJr7AACAZcAAv4feEs6bJuL6EXkbjsE'
LESSON_3_NUDGE_3_PHOTO_FILE_ID = 'AgACAgIAAxkBAAFIIz5p7jkHyHWOlyYswkEa-VZrl_rDAgACyhVrGyjacEu03FfqieYrLwEAAwIAA3kAAzsE'


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
        try:
            await self.bot.send_photo(
                chat_id=chat_id,
                photo=photo_id,
                caption=caption if caption else None,
                reply_markup=reply_markup,
                parse_mode='HTML' if caption else None,
            )
            return True
        except Exception as exc:
            logger.exception(
                'Failed to send photo. chat_id=%s photo_file_id=%s error=%s',
                chat_id,
                photo_id,
                exc,
            )
            return False

    async def send_start_media(
        self,
        chat_id: int,
        file_id: str | None,
        fallback_text: str | None,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> None:
        start_video_note_id = file_id or START_VIDEO_NOTE_FILE_ID
        if start_video_note_id:
            try:
                await self.bot.send_video_note(
                    chat_id=chat_id,
                    video_note=start_video_note_id,
                )
                await asyncio.sleep(3)
            except Exception as exc:
                logger.exception(
                    'Failed to send start video note. chat_id=%s video_note_file_id=%s error=%s',
                    chat_id,
                    start_video_note_id,
                    exc,
                )

        sent = await self._send_photo_by_id(
            chat_id=chat_id,
            photo_id=START_IMAGE_FILE_ID,
            caption=fallback_text,
            reply_markup=reply_markup,
        )
        if not sent and fallback_text:
            await self.bot.send_message(
                chat_id=chat_id,
                text=fallback_text,
                reply_markup=reply_markup,
                parse_mode='HTML',
            )

    async def send_step(self, chat_id: int, step: FunnelStep, reply_markup: InlineKeyboardMarkup | None = None) -> None:
        text = step.body if not step.title else f'{step.title}\n\n{step.body}'
        image_file_id = None
        if step.code in {'lesson_1', 'lesson_2'}:
            image_file_id = LESSON_1_IMAGE_FILE_ID
        elif step.code == 'lesson_3':
            image_file_id = LESSON_3_IMAGE_FILE_ID
        if step.metadata:
            image_file_id = image_file_id or step.metadata.get('image_file_id') or step.metadata.get('photo')
        if image_file_id:
            sent = await self._send_photo_by_id(
                chat_id=chat_id,
                photo_id=str(image_file_id),
                caption=text if text else None,
                reply_markup=reply_markup,
            )
            if sent:
                return
        await self.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

    async def send_text(self, chat_id: int, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
        await self.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode='HTML',
        )

    async def send_lesson_2_nudge_1_video(self, chat_id: int, caption: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
        try:
            await self.bot.send_video(
                chat_id=chat_id,
                video=LESSON_2_NUDGE_1_VIDEO_FILE_ID,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode='HTML',
                write_timeout=8,
                read_timeout=12,
                connect_timeout=6,
                pool_timeout=6,
            )
        except Exception as exc:
            logger.exception(
                'Failed to send lesson_2_nudge_1 video. chat_id=%s video_file_id=%s error=%s',
                chat_id,
                LESSON_2_NUDGE_1_VIDEO_FILE_ID,
                exc,
            )
            await self.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode='HTML')

    async def send_lesson_2_nudge_2_photo(self, chat_id: int, caption: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
        try:
            await self.bot.send_photo(
                chat_id=chat_id,
                photo=LESSON_2_NUDGE_2_PHOTO_FILE_ID,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode='HTML',
            )
        except Exception as exc:
            logger.exception(
                'Failed to send lesson_2_nudge_2 photo. chat_id=%s photo_file_id=%s error=%s',
                chat_id,
                LESSON_2_NUDGE_2_PHOTO_FILE_ID,
                exc,
            )
            await self.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode='HTML')

    async def send_lesson_2_nudge_3_photo(self, chat_id: int, caption: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
        try:
            await self.bot.send_photo(
                chat_id=chat_id,
                photo=LESSON_2_NUDGE_3_PHOTO_FILE_ID,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode='HTML',
            )
        except Exception as exc:
            logger.exception(
                'Failed to send lesson_2_nudge_3 photo. chat_id=%s photo_file_id=%s error=%s',
                chat_id,
                LESSON_2_NUDGE_3_PHOTO_FILE_ID,
                exc,
            )
            await self.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode='HTML')

    async def send_lesson_3_nudge_1_photo(self, chat_id: int, caption: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
        try:
            await self.bot.send_photo(
                chat_id=chat_id,
                photo=LESSON_3_NUDGE_1_PHOTO_FILE_ID,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode='HTML',
            )
        except Exception as exc:
            logger.exception(
                'Failed to send lesson_3_nudge_1 photo. chat_id=%s photo_file_id=%s error=%s',
                chat_id,
                LESSON_3_NUDGE_1_PHOTO_FILE_ID,
                exc,
            )
            await self.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode='HTML')

    async def send_lesson_3_nudge_2_video(self, chat_id: int, caption: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
        try:
            await self.bot.send_video(
                chat_id=chat_id,
                video=LESSON_3_NUDGE_2_VIDEO_FILE_ID,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode='HTML',
                write_timeout=8,
                read_timeout=12,
                connect_timeout=6,
                pool_timeout=6,
            )
        except Exception as exc:
            logger.exception(
                'Failed to send lesson_3_nudge_2 video. chat_id=%s video_file_id=%s error=%s',
                chat_id,
                LESSON_3_NUDGE_2_VIDEO_FILE_ID,
                exc,
            )
            await self.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode='HTML')

    async def send_lesson_3_nudge_3_photo(self, chat_id: int, caption: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
        try:
            await self.bot.send_photo(
                chat_id=chat_id,
                photo=LESSON_3_NUDGE_3_PHOTO_FILE_ID,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode='HTML',
            )
        except Exception as exc:
            logger.exception(
                'Failed to send lesson_3_nudge_3 photo. chat_id=%s photo_file_id=%s error=%s',
                chat_id,
                LESSON_3_NUDGE_3_PHOTO_FILE_ID,
                exc,
            )
            await self.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode='HTML')
