"""
services/instagram.py
Instagram'dan video/reels yuklab olish uchun yt-dlp asosidagi servis.
"""

import asyncio
import os

import yt_dlp

from utils.helpers import generate_temp_filename
from utils.logger import logger


class InstagramService:
    """Instagram video/reels yuklab olish uchun servis klassi."""

    @staticmethod
    async def download_video(url: str) -> str | None:
        """Instagram video/reels'ni yuklab, fayl yo'lini qaytaradi."""
        output_path = generate_temp_filename("mp4")

        ydl_opts = {
            "format": "best[ext=mp4]/best",
            "outtmpl": output_path,
            "quiet": True,
            "no_warnings": True,
            "max_filesize": 50 * 1024 * 1024,
        }

        try:
            loop = asyncio.get_event_loop()

            def download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

            await loop.run_in_executor(None, download)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
            return None
        except Exception as e:
            logger.error(f"Instagram video yuklashda xatolik: {e}")
            return None
