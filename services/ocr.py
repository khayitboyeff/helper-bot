"""
services/ocr.py
Rasm ichidagi matnni aniqlash (OCR - Optical Character Recognition) uchun
Tesseract OCR asosidagi servis. Shuningdek video -> audio konvertatsiyasi
(FFmpeg orqali) ham shu yerda joylashgan, chunki media-processing bilan bog'liq.
"""

import asyncio
import os

import pytesseract
from PIL import Image

from config import config
from utils.helpers import generate_temp_filename
from utils.logger import logger

# Tesseract binary yo'lini sozlash (ayniqsa Windows uchun muhim)
pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD


class OCRService:
    """Rasm ichidagi matnni aniqlash uchun servis klassi."""

    @staticmethod
    async def extract_text(image_path: str, lang: str = "eng+rus+uzb") -> str | None:
        """
        Rasmdan matnni ajratib oladi.
        lang: tesseract til kodlari ('eng', 'rus', 'uzb' va h.k, '+' bilan birlashtiriladi)
        """
        try:
            loop = asyncio.get_event_loop()

            def run_ocr():
                image = Image.open(image_path)
                try:
                    return pytesseract.image_to_string(image, lang=lang)
                except pytesseract.TesseractError:
                    # Agar uzb til paketi o'rnatilmagan bo'lsa, faqat eng+rus bilan urinib ko'ramiz
                    return pytesseract.image_to_string(image, lang="eng+rus")

            text = await loop.run_in_executor(None, run_ocr)
            return text.strip() if text else ""
        except Exception as e:
            logger.error(f"OCR xatolik: {e}")
            return None


class MediaService:
    """FFmpeg asosidagi video<->audio konvertatsiya servisi."""

    @staticmethod
    async def video_to_audio(video_path: str) -> str | None:
        """Video faylni MP3 audioga aylantiradi."""
        output_path = generate_temp_filename("mp3")

        cmd = [
            config.FFMPEG_PATH,
            "-i", video_path,
            "-vn",
            "-acodec", "libmp3lame",
            "-q:a", "2",
            "-y",
            output_path,
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"FFmpeg xatolik: {stderr.decode(errors='ignore')}")
                return None

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
            return None
        except Exception as e:
            logger.error(f"video_to_audio xatolik: {e}")
            return None
