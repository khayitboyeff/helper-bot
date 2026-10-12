""""
config.py
Loyihaning barcha sozlamalari shu yerda saqlanadi.
.env faylidan environment o'zgaruvchilarini o'qiydi.
"""
 
import os
from pathlib import Path
from dotenv import load_dotenv

# .env faylini joriy papkadan qat’i nazar loyiha ildizidan yuklaydi.
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)
 
 
class Config:
    # Bot tokeni (BotFather'dan olinadi)
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
 
    # Adminlar ro'yxati (vergul bilan ajratilgan telegram ID'lar)
    ADMIN_IDS: list[int] = [
        int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
    ]
 
    # Database fayl yo'li
    DB_PATH: str = os.getenv("DB_PATH", "database/yordamchi_bot.db")
 
    # Vaqtinchalik fayllar papkasi (yuklab olingan video/audio shu yerda saqlanadi)
    TEMP_DIR: str = os.getenv("TEMP_DIR", "temp")
 
    # FFmpeg binary yo'li (aksariyat holda "ffmpeg" yetarli, agar PATH'da bo'lsa)
    FFMPEG_PATH: str = os.getenv("FFMPEG_PATH", "ffmpeg")
 
    # Tesseract OCR binary yo'li
    # Linux uchun odatda "tesseract", Windows uchun to'liq yo'l kerak bo'lishi mumkin
    # masalan: C:\Program Files\Tesseract-OCR\tesseract.exe
    TESSERACT_CMD: str = os.getenv("TESSERACT_CMD", "tesseract")
 
    # Coin tizimi sozlamalari
    COIN_PER_AD: int = int(os.getenv("COIN_PER_AD", "5"))
    DAILY_REWARD: int = int(os.getenv("DAILY_REWARD", "10"))  # /daily mukofoti
    DOWNLOAD_COST: int = int(os.getenv("DOWNLOAD_COST", "2"))
    OCR_COST: int = int(os.getenv("OCR_COST", "3"))
    TRANSLATE_COST: int = int(os.getenv("TRANSLATE_COST", "1"))
 
    # Kunlik bepul limit (VIP bo'lmagan foydalanuvchilar uchun)
    FREE_DAILY_LIMIT: int = int(os.getenv("FREE_DAILY_LIMIT", "5"))
    VIP_DAILY_LIMIT: int = int(os.getenv("VIP_DAILY_LIMIT", "100"))
 
    # Referral tizimi
    REFERRAL_TARGET: int = int(os.getenv("REFERRAL_TARGET", "10"))
    REFERRAL_REWARD_USD: float = float(os.getenv("REFERRAL_REWARD_USD", "5.0"))
 
    # Karta orqali o'tkazma rekvizitlari (Stars'dan alohida)
    CARD_NUMBER: str = os.getenv("CARD_NUMBER", "")
    CARD_HOLDER: str = os.getenv("CARD_HOLDER", "")
    PAYMENT_ADMIN_CONTACT: str = os.getenv("PAYMENT_ADMIN_CONTACT", "")
 
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip().strip("\"\'")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    GEMINI_DAILY_LIMIT: int = int(os.getenv("GEMINI_DAILY_LIMIT", "200"))

    # Log fayl yo'li
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/bot.log")
 
 
config = Config()
 