"""
bot.py
Yordamchi Bot - asosiy ishga tushirish nuqtasi.

Ishga tushirish:
    python bot.py
"""

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database.db import db
from utils.logger import logger
from utils.helpers import ensure_temp_dir

from handlers import start, tools, profile, vip, admin, coin, qr_code, gemini_chat


async def main() -> None:
    """Botni ishga tushiruvchi asosiy funksiya."""

    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN topilmadi! .env faylini tekshiring.")
        return

    # Vaqtinchalik papkani tayyorlash
    ensure_temp_dir()

    # Database'ni initsializatsiya qilish
    await db.init_db()

    # Bot va Dispatcher yaratish
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Routerlarni ro'yxatdan o'tkazish (tartib muhim: aniqroq handlerlar avval)
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(tools.router)
    dp.include_router(profile.router)
    dp.include_router(vip.router)
    dp.include_router(coin.router)
    dp.include_router(qr_code.router)
    dp.include_router(gemini_chat.router)

    logger.info("Yordamchi Bot ishga tushmoqda...")

    try:
        # Eski update'larni tashlab, botni polling rejimida ishga tushirish
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot ishga tushishda xatolik: {e}")
    finally:
        await bot.session.close()
        logger.info("Bot to'xtatildi.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot foydalanuvchi tomonidan to'xtatildi (Ctrl+C).")
