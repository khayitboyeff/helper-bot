"""
services/translator.py
100+ tilga tarjima qilish uchun servis (deep-translator kutubxonasi orqali,
Google Translate'ning bepul web interfeysidan foydalanadi, API key talab qilmaydi).
Avtomatik til aniqlash ham qo'llab-quvvatlanadi.
"""

import asyncio

from deep_translator import GoogleTranslator

from utils.logger import logger


class TranslatorService:
    """Matnlarni turli tillarga tarjima qilish uchun servis klassi."""

    @staticmethod
    async def translate(text: str, target_lang: str = "uz", source_lang: str = "auto") -> str | None:
        """
        Matnni berilgan tilga tarjima qiladi.
        source_lang='auto' bo'lsa, manba til avtomatik aniqlanadi.
        """
        try:
            loop = asyncio.get_event_loop()

            def run_translate():
                translator = GoogleTranslator(source=source_lang, target=target_lang)
                return translator.translate(text)

            result = await loop.run_in_executor(None, run_translate)
            return result
        except Exception as e:
            logger.error(f"Tarjima xatolik: {e}")
            return None

    @staticmethod
    def get_supported_languages() -> dict:
        """Qo'llab-quvvatlanadigan tillar ro'yxatini qaytaradi (kod: nom)."""
        try:
            return GoogleTranslator().get_supported_languages(as_dict=True)
        except Exception as e:
            logger.error(f"Tillar ro'yxatini olishda xatolik: {e}")
            return {}
