"""
services/youtube.py
YouTube'dan video va MP3 yuklab olish uchun yt-dlp asosidagi servis.
"""

import asyncio
import os

import yt_dlp

from config import config
from utils.helpers import generate_temp_filename
from utils.logger import logger


class YouTubeService:
    """YouTube video/audio yuklab olish uchun servis klassi."""

    # YouTube blokirovkasidan o'tish va har qanday havolani (Shorts, mobile) qo'llash
    BASE_YDL_OPTS = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "format_sort": ["res:1080", "ext:mp4:m4a"],  # Sifat va formatni xavfsiz saralash
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios"],  # Blokirovkadan qutulishning eng samarali usuli
                "skip": ["dash", "hls"],
            }
        },
    }

    @staticmethod
    async def download_video(url: str) -> str | None:
        """
        Berilgan YouTube URL bo'yicha videoni yuklab, fayl yo'lini qaytaradi.
        """
        output_path = generate_temp_filename("mp4")

        ydl_opts = {
            **YouTubeService.BASE_YDL_OPTS,
            # Birlashtirish xatosini oldini olish uchun eng yaxshi yagona MP4 yoki best format
            "format": "best[ext=mp4]/best",
            "outtmpl": output_path,
            "max_filesize": 50 * 1024 * 1024,  # Telegram limiti: EXACT 50MB
        }

        # Agar FFmpeg mavjud bo'lsa, o'rnatamiz
        ffmpeg_path = getattr(config, "FFMPEG_PATH", None)
        if ffmpeg_path:
            ydl_opts["ffmpeg_location"] = ffmpeg_path

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, YouTubeService._run_download, url, ydl_opts)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
            return None
        except Exception as e:
            logger.error(f"YouTube video yuklashda xatolik: {e}")
            return None

    @staticmethod
    async def download_audio(url: str) -> str | None:
        """
        Berilgan YouTube URL bo'yicha audioni (MP3) yuklab, fayl yo'lini qaytaradi.
        """
        output_path = generate_temp_filename("mp3")
        temp_template = output_path.rsplit(".", 1)[0]

        ydl_opts = {
            **YouTubeService.BASE_YDL_OPTS,
            "format": "bestaudio/best",
            "outtmpl": f"{temp_template}.%(ext)s",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }

        ffmpeg_path = getattr(config, "FFMPEG_PATH", None)
        if ffmpeg_path:
            ydl_opts["ffmpeg_location"] = ffmpeg_path

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, YouTubeService._run_download, url, ydl_opts)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
            return None
        except Exception as e:
            logger.error(f"YouTube audio yuklashda xatolik: {e}")
            return None

    @staticmethod
    def _run_download(url: str, ydl_opts: dict) -> None:
        """yt-dlp orqali sinxron yuklab olish."""
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    @staticmethod
    async def get_video_info(url: str) -> dict | None:
        """Video haqida ma'lumot oladi."""
        ydl_opts = {**YouTubeService.BASE_YDL_OPTS}
        try:
            loop = asyncio.get_event_loop()

            def extract():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)

            info = await loop.run_in_executor(None, extract)
            if not info:
                return None

            return {
                "title": info.get("title", "Noma'lum"),
                "duration": info.get("duration", 0),
                "uploader": info.get("uploader", "Noma'lum"),
            }
        except Exception as e:
            logger.error(f"YouTube video ma'lumotini olishda xatolik: {e}")
            return None