"""
utils/helpers.py
Turli joylarda qayta-qayta ishlatiladigan yordamchi funksiyalar.
"""

import os
import re
import uuid
from datetime import datetime, date

from config import config


def ensure_temp_dir() -> str:
    """Vaqtinchalik fayllar papkasi mavjudligini tekshiradi, yo'q bo'lsa yaratadi."""
    if not os.path.exists(config.TEMP_DIR):
        os.makedirs(config.TEMP_DIR, exist_ok=True)
    return config.TEMP_DIR


def generate_temp_filename(extension: str = "mp4") -> str:
    """Unikal vaqtinchalik fayl nomi generatsiya qiladi."""
    ensure_temp_dir()
    filename = f"{uuid.uuid4().hex}.{extension}"
    return os.path.join(config.TEMP_DIR, filename)


def cleanup_file(filepath: str) -> None:
    """Faylni xavfsiz o'chirish, xatolik bo'lsa jim o'tkazib yuboradi."""
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
    except Exception:
        pass


def is_valid_url(text: str) -> bool:
    """Matn URL ekanligini tekshiradi."""
    url_pattern = re.compile(
        r"^(https?://)?"
        r"([\w\-]+\.)+[\w\-]{2,}"
        r"(/[\w\-./?%&=]*)?$",
        re.IGNORECASE,
    )
    return bool(url_pattern.match(text.strip()))


def detect_platform(url: str) -> str | None:
    """URL manzilidan platformani (youtube, instagram, tiktok, facebook) aniqlaydi."""
    url = url.lower()
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    if "instagram.com" in url:
        return "instagram"
    if "tiktok.com" in url:
        return "tiktok"
    if "facebook.com" in url or "fb.watch" in url:
        return "facebook"
    return None


def format_bytes(size: int) -> str:
    """Bayt hajmini o'qish oson formatga o'giradi (KB, MB, GB)."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def today_str() -> str:
    """Bugungi sanani YYYY-MM-DD formatida qaytaradi."""
    return date.today().isoformat()


def now_str() -> str:
    """Hozirgi vaqtni to'liq formatda qaytaradi."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_admin(telegram_id: int) -> bool:
    """Foydalanuvchi admin ekanligini tekshiradi."""
    return telegram_id in config.ADMIN_IDS


def escape_markdown(text: str) -> str:
    """Telegram MarkdownV2 uchun maxsus belgilarni escape qiladi."""
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in escape_chars else c for c in text)
