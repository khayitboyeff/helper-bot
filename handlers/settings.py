
"""
handlers/settings.py
YordamchiBot foydalanuvchi sozlamalari.
Aiogram 3.x + SQLite.
"""

import aiosqlite

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from config import config
from handlers.start import main_menu_keyboard
from utils.logger import logger

router = Router(name="settings")

LANGUAGES = {
    "uz": "🇺🇿 O‘zbekcha",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
}


async def init_settings_db() -> None:
    """Foydalanuvchi sozlamalari jadvalini yaratadi."""
    async with aiosqlite.connect(config.DB_PATH) as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                telegram_id INTEGER PRIMARY KEY,
                language TEXT NOT NULL DEFAULT 'uz',
                notifications INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (telegram_id)
                    REFERENCES users (telegram_id)
            )
        """)
        await conn.commit()


async def get_settings(telegram_id: int) -> dict:
    """Foydalanuvchi sozlamalarini oladi."""
    await init_settings_db()

    async with aiosqlite.connect(config.DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row

        cursor = await conn.execute(
            """
            SELECT language, notifications
            FROM user_settings
            WHERE telegram_id = ?
            """,
            (telegram_id,),
        )
        row = await cursor.fetchone()

        if row:
            return dict(row)

        await conn.execute(
            """
            INSERT OR IGNORE INTO user_settings
                (telegram_id, language, notifications)
            VALUES (?, 'uz', 1)
            """,
            (telegram_id,),
        )
        await conn.commit()

        return {
            "language": "uz",
            "notifications": 1,
        }


async def save_language(telegram_id: int, language: str) -> None:
    """Tanlangan tilni saqlaydi."""
    if language not in LANGUAGES:
        raise ValueError("Noto‘g‘ri til tanlandi.")

    await init_settings_db()

    async with aiosqlite.connect(config.DB_PATH) as conn:
        await conn.execute(
            """
            INSERT INTO user_settings
                (telegram_id, language, notifications)
            VALUES (?, ?, 1)
            ON CONFLICT(telegram_id) DO UPDATE SET
                language = excluded.language
            """,
            (telegram_id, language),
        )
        await conn.commit()


async def toggle_notifications(telegram_id: int) -> int:
    """Bildirishnomalarni yoqadi yoki o‘chiradi."""
    await get_settings(telegram_id)

    async with aiosqlite.connect(config.DB_PATH) as conn:
        await conn.execute(
            """
            UPDATE user_settings
            SET notifications = CASE
                WHEN notifications = 1 THEN 0
                ELSE 1
            END
            WHERE telegram_id = ?
            """,
            (telegram_id,),
        )

        cursor = await conn.execute(
            """
            SELECT notifications
            FROM user_settings
            WHERE telegram_id = ?
            """,
            (telegram_id,),
        )
        row = await cursor.fetchone()
        await conn.commit()

        return int(row[0])


def settings_keyboard(
    language: str,
    notifications: int,
) -> InlineKeyboardMarkup:
    """Sozlamalar tugmalarini yaratadi."""

    notification_text = (
        "🔔 Bildirishnomalar: Yoqilgan"
        if notifications
        else "🔕 Bildirishnomalar: O‘chirilgan"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🌐 Til: {LANGUAGES.get(language, LANGUAGES['uz'])}",
                    callback_data="settings:languages",
                )
            ],
            [
                InlineKeyboardButton(
                    text=notification_text,
                    callback_data="settings:notifications",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Profil",
                    callback_data="settings:profile",
                ),
                InlineKeyboardButton(
                    text="🏠 Bosh menyu",
                    callback_data="settings:home",
                ),
            ],
        ]
    )


def language_keyboard() -> InlineKeyboardMarkup:
    """Til tanlash tugmalari."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=LANGUAGES["uz"],
                    callback_data="settings:lang:uz",
                )
            ],
            [
                InlineKeyboardButton(
                    text=LANGUAGES["ru"],
                    callback_data="settings:lang:ru",
                )
            ],
            [
                InlineKeyboardButton(
                    text=LANGUAGES["en"],
                    callback_data="settings:lang:en",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Sozlamalarga qaytish",
                    callback_data="settings:back",
                )
            ],
        ]
    )


async def show_settings(target, telegram_id: int) -> None:
    """Sozlamalar oynasini ko‘rsatadi."""
    user = await get_settings(telegram_id)

    text = (
        "⚙️ <b>SOZLAMALAR</b>\n\n"
        "Bu bo‘lim orqali bot sozlamalarini boshqarishingiz mumkin.\n\n"
        f"🌐 Tanlangan til: "
        f"{LANGUAGES.get(user['language'], LANGUAGES['uz'])}\n"
        f"🔔 Bildirishnomalar: "
        f"{'Yoqilgan' if user['notifications'] else 'O‘chirilgan'}\n\n"
        "Kerakli sozlamani tanlang:"
    )

    await target.answer(
        text,
        reply_markup=settings_keyboard(
            user["language"],
            user["notifications"],
        ),
    )


@router.message(Command("settings"))
@router.message(F.text == "⚙️ Sozlamalar")
async def cmd_settings(message: Message) -> None:
    """ /settings buyrug‘i."""
    try:
        if not await user_exists(message.from_user.id):
            await message.answer(
                "Avval /start buyrug‘ini bosing."
            )
            return

        await show_settings(message, message.from_user.id)

    except Exception:
        logger.exception("Sozlamalarni ochishda xatolik")
        await message.answer(
            "Sozlamalarni ochib bo‘lmadi. Qayta urinib ko‘ring."
        )


async def user_exists(telegram_id: int) -> bool:
    """Foydalanuvchi ro‘yxatdan o‘tganini tekshiradi."""
    async with aiosqlite.connect(config.DB_PATH) as conn:
        cursor = await conn.execute(
            "SELECT 1 FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        return await cursor.fetchone() is not None


@router.callback_query(F.data == "settings:languages")
async def choose_language(callback: CallbackQuery) -> None:
    await callback.answer()

    await callback.message.edit_text(
        "🌐 <b>Tilni tanlang</b>\n\n"
        "Quyidagi tillardan birini tanlang:",
        reply_markup=language_keyboard(),
    )


@router.callback_query(F.data.startswith("settings:lang:"))
async def set_language(callback: CallbackQuery) -> None:
    try:
        if not await user_exists(callback.from_user.id):
            await callback.answer(
                "Avval /start buyrug‘ini bosing.",
                show_alert=True,
            )
            return

        language = callback.data.rsplit(":", 1)[-1]

        if language not in LANGUAGES:
            await callback.answer(
                "Noto‘g‘ri til tanlandi.",
                show_alert=True,
            )
            return

        await save_language(callback.from_user.id, language)
        await callback.answer("Til tanlovi saqlandi.")

        await show_settings(
            callback.message,
            callback.from_user.id,
        )

    except Exception:
        logger.exception("Tilni saqlashda xatolik")
        await callback.answer(
            "Tilni saqlab bo‘lmadi.",
            show_alert=True,
        )


@router.callback_query(F.data == "settings:notifications")
async def change_notifications(callback: CallbackQuery) -> None:
    try:
        if not await user_exists(callback.from_user.id):
            await callback.answer(
                "Avval /start buyrug‘ini bosing.",
                show_alert=True,
            )
            return

        status = await toggle_notifications(callback.from_user.id)

        await callback.answer(
            "Bildirishnomalar yoqildi."
            if status
            else "Bildirishnomalar o‘chirildi."
        )

        await show_settings(
            callback.message,
            callback.from_user.id,
        )

    except Exception:
        logger.exception("Bildirishnoma sozlamasida xatolik")
        await callback.answer(
            "Sozlamani o‘zgartirib bo‘lmadi.",
            show_alert=True,
        )


@router.callback_query(F.data == "settings:back")
async def settings_back(callback: CallbackQuery) -> None:
    await callback.answer()
    await show_settings(
        callback.message,
        callback.from_user.id,
    )


@router.callback_query(F.data == "settings:profile")
async def settings_profile(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "👤 Profilingizni ko‘rish uchun /profile buyrug‘ini yuboring."
    )


@router.callback_query(F.data == "settings:home")
async def settings_home(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "🏠 Bosh menyu",
        reply_markup=main_menu_keyboard(),
    )
