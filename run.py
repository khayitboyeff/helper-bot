"""
run.py

Yordamchi Bot - asosiy ishga tushirish fayli.
"""

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from config import config
from database.db import db
from utils.helpers import ensure_temp_dir
from utils.logger import logger


# ============================================================
# HANDLERS
# ============================================================

from handlers import admin
from handlers import ai_image as ai_image_handler
from handlers import coin
from handlers import downloader
from handlers import profile
from handlers import qr_code
from handlers import start
from handlers import tools
from handlers import vip
from handlers import settings


# ============================================================
# MAIN
# ============================================================

async def main() -> None:

    # --------------------------------------------------------
    # BOT TOKEN TEKSHIRISH
    # --------------------------------------------------------

    if not config.BOT_TOKEN:

        logger.error(
            "BOT_TOKEN topilmadi! "
            ".env faylini tekshiring."
        )

        return

    # --------------------------------------------------------
    # TEMP PAPKA
    # --------------------------------------------------------

    ensure_temp_dir()

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    await db.init_db()

    logger.info(
        "Telegram bot muvaffaqiyatli ishga tushdi."
    )

    # --------------------------------------------------------
    # BOT
    # --------------------------------------------------------

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        ),
    )
    await bot.set_my_commands([
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="help", description="Yordam va qo'llanma"),
        BotCommand(command="profile", description="Profilim"),
        BotCommand(command="coins", description="Coin balansim"),
        BotCommand(command="daily", description="Kunlik mukofot"),
        BotCommand(command="spin", description="Aylantirish"),
        BotCommand(command="vip", description="VIP imkoniyatlari"),
        BotCommand(command="top", description="Eng faol foydalanuvchilar"),
        BotCommand(command="settings", description="Sozlamalar"),
    ])
    # --------------------------------------------------------
    # DISPATCHER
    # --------------------------------------------------------

    dp = Dispatcher(
        storage=MemoryStorage()
    )

    # --------------------------------------------------------
    # ROUTERS
    # --------------------------------------------------------

    dp.include_router(
        admin.router
    )

    dp.include_router(
        start.router
    )

    dp.include_router(
        coin.router
    )

    # AI IMAGE
    dp.include_router(
        ai_image_handler.router
    )

    dp.include_router(
        qr_code.router
    )

    dp.include_router(
        downloader.router
    )

    dp.include_router(
        tools.router
    )

    dp.include_router(
        profile.router
    )

    dp.include_router(
        vip.router
    )

    dp.include_router(
        settings.router
    )

    logger.info(
        "Yordamchi Bot ishga tushmoqda..."
    )

    # --------------------------------------------------------
    # POLLING
    # --------------------------------------------------------

    try:

        # Eski webhook/update larni tozalash
        await bot.delete_webhook(
            drop_pending_updates=True
        )

        logger.info(
            "Bot polling rejimida ishga tushdi."
        )

        await dp.start_polling(
            bot
        )

    except Exception as error:

        logger.error(
            f"Bot ishga tushishda xatolik: {error}"
        )

    finally:

        await bot.session.close()

        logger.info(
            "Bot to'xtatildi."
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        logger.info(
            "Bot foydalanuvchi tomonidan "
            "to'xtatildi (Ctrl+C)."
        )