import logging

from telegram import Bot, InlineKeyboardMarkup

from bot.models.content import FunnelStep


logger = logging.getLogger(__name__)
START_VIDEO_NOTE_FILE_ID = 'DQACAgIAAxkBAAIBhWnpmmxR5qu56BBGJNJ5MKZY-He_AAJTnQACK7YIS--c7EpIOUk5OwQ'
START_IMAGE_FILE_ID = 'AgACAgIAAxkBAAIBfWnpmc4Tjkn9HGQqfqEW79jZPJ93AALbFmsbvUFJS1O2t6nwc_N8AQADAgADeQADOwQ'
LESSON_SHARED_IMAGE_FILE_ID = 'AgACAgIAAxkBAAIBfmnpmc6EzfmBYS-UDKZShxvpyRrvAALcFmsbvUFJSzmJ-N5TlpfJAQADAgADeQADOwQ'
LESSON_3_IMAGE_FILE_ID = 'AgACAgIAAxkBAAIBgGnpmc7xwKjsR84n7rqm_DMFEEgfAALdFmsbvUFJS9xc93RZjdQIAQADAgADeQADOwQ'
LESSON_2_NUDGE_1_VIDEO_FILE_ID = 'BAACAgIAAxkBAAFH8Ndp6uthRCOihuaFx6xBxr11nbsP2QACO50AAknbWUsrKtpGJFRdmDsE'
LESSON_2_NUDGE_2_PHOTO_FILE_ID = 'AgACAgIAAxkBAAFH-dZp63aThou9RLX9azZkF8ZRpLOFJQACuhNrG0nbYUu0rHr3VIdxjQEAAwIAA3gAAzsE'
LESSON_2_NUDGE_3_PHOTO_FILE_ID = 'AgACAgIAAxkBAAFH-fpp63gyDFB737FpP5fcn-z7_gIjkgACxxNrG0nbYUuc4vQUNDHgOgEAAwIAA3kAAzsE'
LESSON_3_NUDGE_1_PHOTO_FILE_ID = 'AgACAgIAAxkBAAFH-u1p64DDUCFuWhSQv1ASJFJ1duGuHwAC9RNrG0nbYUsIzOEF4jSFAgEAAwIAA3kAAzsE'
LESSON_3_NUDGE_2_VIDEO_FILE_ID = 'BAACAgIAAxkBAAFH-v9p64IepE_XTEKTpVyWgy92BZUOEAACqaIAAknbYUuftJ9afKN8MTsE'


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
        start_video_note_id = file_id or START_VIDEO_NOTE_FILE_ID
        if start_video_note_id:
            try:
                await self.bot.send_video_note(
                    chat_id=chat_id,
                    video_note=start_video_note_id,
                )
            except Exception as exc:
                logger.exception(
                    'Failed to send start video note. chat_id=%s video_note_file_id=%s error=%s',
                    chat_id,
                    start_video_note_id,
                    exc,
                )

        await self._send_photo_by_id(
            chat_id=chat_id,
            photo_id=START_IMAGE_FILE_ID,
            caption=fallback_text,
            reply_markup=reply_markup,
        )

    async def send_step(self, chat_id: int, step: FunnelStep, reply_markup: InlineKeyboardMarkup | None = None) -> None:
        text = step.body if not step.title else f'{step.title}\n\n{step.body}'
        image_file_id = None
        if step.code in {'lesson_1', 'lesson_2'}:
            image_file_id = LESSON_SHARED_IMAGE_FILE_ID
        elif step.code == 'lesson_3':
            image_file_id = LESSON_3_IMAGE_FILE_ID
        if step.metadata:
            image_file_id = image_file_id or step.metadata.get('image_file_id') or step.metadata.get('photo')
        if image_file_id:
            await self._send_photo_by_id(
                chat_id=chat_id,
                photo_id=str(image_file_id),
                caption=text if text else None,
                reply_markup=reply_markup,
            )
            return
        await self.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

    async def send_text(self, chat_id: int, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
        await self.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

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
            await self.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup)

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
            await self.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup)

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
            await self.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup)

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
            await self.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup)

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
            await self.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup)
