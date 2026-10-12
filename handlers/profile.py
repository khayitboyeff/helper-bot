"""
handlers/profile.py
Foydalanuvchi profili, referral tizimi va coin olish (reklama ko'rish) handleri.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config
from database.db import db
from utils.logger import logger

router = Router(name="profile")


# ============================================================
# PROFIL  (/profile buyrug'i VA "👤 Profil" tugmasi)
# ============================================================

@router.message(Command("profile"))
@router.message(F.text == "👤 Profil")
async def show_profile(message: Message) -> None:
    """Foydalanuvchi profilini ko'rsatadi."""
    try:
        telegram_id = message.from_user.id
        await db.check_and_expire_vip(telegram_id)
        user = await db.get_user(telegram_id)

        if not user:
            await message.answer("❌ Avval /start buyrug'ini bosing.")
            return

        vip_status = "✅ Faol" if user["vip"] else "❌ Yo'q"
        daily_used = await db.get_daily_usage(telegram_id)
        limit = config.VIP_DAILY_LIMIT if user["vip"] else config.FREE_DAILY_LIMIT
        username = f"@{user['username']}" if user["username"] else "yo'q"


        text = (
            "👤 <b>Sizning profilingiz</b>\n\n"
            f"🆔 ID: <code>{user['telegram_id']}</code>\n"
            f"👤 Ism: {user['full_name']}\n"
            f"📛 Username: {username}\n"
            f"🪙 Coinlar: <b>{user['coins']}</b>\n"
            f"💎 VIP: {vip_status}\n"
            f"📊 Bugungi limit: {daily_used}/{limit}"
        )

        await message.answer(text)
    except Exception as e:
        logger.error(f"show_profile xatolik: {e}")
        await message.answer("❌ Xatolik yuz berdi.")


# ============================================================
# SOZLAMALAR  (/settings)
# ============================================================

@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    await message.answer("⚙️ <b>Sozlamalar</b>\n\nTez orada qo'shiladi.")


# ============================================================
# COIN OLISH
# ============================================================

@router.message(F.text == "🎁 Coin olish")
async def show_coin_options(message: Message) -> None:
    """Coin olish variantlarini ko'rsatadi (reklama ko'rish orqali)."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=f"📺 Reklama ko'rish (+{config.COIN_PER_AD} coin)",
        callback_data="watch_ad",
    ))

    text = (
        "🎁 <b>Coin olish</b>\n\n"
        f"Reklama ko'rib +{config.COIN_PER_AD} coin oling.\n"
        f"Coinlar bilan OCR va tarjima kabi xizmatlardan "
        f"kunlik limitdan tashqari ham foydalanishingiz mumkin.\n\n"
        f"💰 Narxlar:\n"
        f"— OCR/PDF: {config.OCR_COST} coin\n"
        f"— Tarjima: {config.TRANSLATE_COST} coin"
    )
    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "watch_ad")
async def process_watch_ad(callback: CallbackQuery) -> None:
    """Reklama ko'rish simulyatsiyasi (keyin real reklama tarmog'i ulanadi)."""
    try:
        telegram_id = callback.from_user.id
        await db.add_coins(telegram_id, config.COIN_PER_AD)
        await callback.answer(f"✅ +{config.COIN_PER_AD} coin qo'shildi!", show_alert=True)
        logger.info(f"Foydalanuvchi {telegram_id} reklama ko'rib coin oldi.")
    except Exception as e:
        logger.error(f"process_watch_ad xatolik: {e}")
        await callback.answer("❌ Xatolik yuz berdi.", show_alert=True)