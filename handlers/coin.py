"""
handlers/coin.py
Coin markazi: omad g'ildiragi (baraban), VIP xarid, /daily, /spin va /top.
"""

import html
import random

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import config
from database.db import db
from utils.logger import logger

router = Router(name="coins")

DAILY_FREE_SPINS = 3      # Kunlik bepul imkoniyatlar soni
VIP_PRICE_COINS = 100     # Coin evaziga VIP narxi
VIP_DAYS = 30             # VIP muddati (kun)

# Barabanda tushishi mumkin bo'lgan sovg'alar va ularning ehtimollik vazni (weights)
WHEEL_PRIZES = [
    {"type": "coin", "value": 1, "label": "🪙 +1 coin", "weight": 25},
    {"type": "coin", "value": 2, "label": "🪙 +2 coin", "weight": 20},
    {"type": "coin", "value": 3, "label": "🪙 +3 coin", "weight": 18},
    {"type": "coin", "value": 5, "label": "🪙 +5 coin", "weight": 12},
    {"type": "coin", "value": 9, "label": "🪙 +9 coin", "weight": 10},
    {"type": "coin", "value": 10, "label": "🪙 +10 coin", "weight": 7},
    {"type": "coin", "value": 15, "label": "🪙 +15 coin", "weight": 4},
    {"type": "coin", "value": 20, "label": "🪙 +20 coin", "weight": 2},
    {"type": "coin", "value": 23, "label": "🪙 +23 coin", "weight": 1.5},
    {"type": "vip", "value": 30, "label": "💎 1 Oylik VIP Status!", "weight": 0.5},
]


# ============================================================
# YORDAMCHI FUNKSIYALAR
# ============================================================

def get_coins_keyboard() -> InlineKeyboardMarkup:
    """Coin markazining inline tugmalari."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎰 Barabanni Aylantirish", callback_data="spin_wheel")],
            [InlineKeyboardButton(
                text=f"💎 VIP xarid ({VIP_PRICE_COINS} coin)",
                callback_data="coin_buy_vip",
            )],
        ]
    )


async def build_coins_text(user_id: int) -> str:
    """Coin markazi matnini tayyorlaydi (balans va qolgan imkoniyatlar bilan)."""
    coins_count = await db.get_user_coins(user_id)
    spins_today = await db.get_daily_spins(user_id)
    extra_spins = await db.get_extra_spins(user_id)
    left_spins = max(0, DAILY_FREE_SPINS - spins_today)

    extra_line = f"🎟 Qo'shimcha imkoniyat: <b>{extra_spins}</b>\n" if extra_spins else ""

    return (
        "🪙 <b>Coin Markazi & Omad G'ildiragi</b>\n\n"
        f"💰 Balansingiz: <b>{coins_count} coin</b>\n"
        f"🎰 Bugungi imkoniyat: <b>{left_spins}/{DAILY_FREE_SPINS}</b>\n"
        f"{extra_line}\n"
        "✨ Barabanda yutib olishingiz mumkin bo'lgan sovg'alar:\n"
        "• +1, +2, +3, +5, +9, +10, +15, +20, +23 coinlar\n"
        "• 💎 <b>1 oylik VIP Status</b>\n\n"
        f"<i>Eslatma: Kunlik {DAILY_FREE_SPINS} ta imkoniyat tugagach, har bir "
        "qo'shimcha imkoniyat uchun 1 ta do'st taklif qilishingiz kerak!</i>"
    )


async def build_limit_text(bot, user_id: int) -> str:
    """Kunlik limit tugaganda ko'rsatiladigan matn (referral havola bilan)."""
    bot_username = (await bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    return (
        f"⚠️ <b>Kunlik limit tugadi ({DAILY_FREE_SPINS}/{DAILY_FREE_SPINS})!</b>\n\n"
        "🎰 Barabanni yana aylantirish uchun do'stlaringizni taklif qiling.\n"
        "<b>Har bir kirgan do'stingiz uchun +1 ta aylantirish imkoniyati beriladi!</b>\n\n"
        f"🔗 Sizning taklif havolangiz:\n<code>{ref_link}</code>"
    )


async def perform_spin(user_id: int) -> str | None:
    """
    Barabanni aylantiradi va yutuq matnini qaytaradi.
    Imkoniyat qolmagan bo'lsa None qaytaradi.
    """
    spins_today = await db.get_daily_spins(user_id)

    # Bepul limit tugagan bo'lsa, qo'shimcha imkoniyatdan foydalanamiz
    # (use_extra_spin tekshirish va ayirishni bitta amalda bajaradi)
    if spins_today >= DAILY_FREE_SPINS:
        if not await db.use_extra_spin(user_id):
            return None

    prize = random.choices(
        WHEEL_PRIZES,
        weights=[p["weight"] for p in WHEEL_PRIZES],
        k=1,
    )[0]

    await db.increment_daily_spins(user_id)

    if prize["type"] == "coin":
        await db.add_coins(user_id, prize["value"])
        return f"🎉 Tabriklaymiz! Siz <b>{prize['label']}</b> yutib oldingiz!"

    await db.set_vip(user_id, days=prize["value"])
    return "🎉 <b>DAXSHAT!</b> Siz <b>1 oylik VIP Status</b> yutib oldingiz! 💎"


# ============================================================
# COIN MARKAZI  (/coins va menyu tugmalari)
# ============================================================

@router.message(Command("coins"))
@router.message(F.text.in_({"🪙 Coinlarim", "🎁 Coin olish", "🪙 Spin / Coin"}))
async def cmd_coins(message: Message) -> None:
    """Coin menyusini ko'rsatish."""
    try:
        text = await build_coins_text(message.from_user.id)
        await message.answer(text, reply_markup=get_coins_keyboard())
    except Exception:
        logger.exception("cmd_coins xatolik")
        await message.answer("❌ Coin menyusini ochishda xatolik yuz berdi.")


# ============================================================
# /daily - KUNLIK MUKOFOT
# ============================================================

@router.message(Command("daily"))
async def cmd_daily(message: Message) -> None:
    try:
        user_id = message.from_user.id

        if not await db.get_user(user_id):
            await message.answer("❌ Avval /start buyrug'ini bosing.")
            return

        if await db.claim_daily_reward(user_id, config.DAILY_REWARD):
            await message.answer(f"🎁 Kunlik mukofot: <b>+{config.DAILY_REWARD}</b> coin!")
        else:
            await message.answer("⏳ Bugungi mukofotni allaqachon olgansiz. Ertaga qaytib keling.")
    except Exception:
        logger.exception("cmd_daily xatolik")
        await message.answer("❌ Xatolik yuz berdi.")


# ============================================================
# /spin - BARABAN (buyruq orqali)
# ============================================================

@router.message(Command("spin"))
async def cmd_spin(message: Message) -> None:
    try:
        user_id = message.from_user.id

        if not await db.get_user(user_id):
            await message.answer("❌ Avval /start buyrug'ini bosing.")
            return

        win_msg = await perform_spin(user_id)
        if win_msg is None:
            await message.answer(await build_limit_text(message.bot, user_id))
        else:
            await message.answer(win_msg)
    except Exception:
        logger.exception("cmd_spin xatolik")
        await message.answer("❌ Xatolik yuz berdi.")


# ============================================================
# /top - ENG KO'P COINLI FOYDALANUVCHILAR
# ============================================================

@router.message(Command("top"))
async def cmd_top(message: Message) -> None:
    try:
        users = await db.get_top_users(10)
        if not users:
            await message.answer("Hali foydalanuvchilar yo'q.")
            return

        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        text = "🏆 <b>Eng faol foydalanuvchilar</b>\n\n"

        for i, u in enumerate(users, 1):
            name = u["full_name"] or (f"@{u['username']}" if u["username"] else str(u["telegram_id"]))
            text += f"{medals.get(i, f'{i}.')} {html.escape(name)} — {u['coins']} coin\n"

        await message.answer(text)
    except Exception:
        logger.exception("cmd_top xatolik")
        await message.answer("❌ Xatolik yuz berdi.")


# ============================================================
# BARABAN TUGMASI (inline)
# ============================================================

@router.callback_query(F.data == "spin_wheel")
async def cb_spin_wheel(callback: CallbackQuery) -> None:
    """Barabanni aylantirish handleri."""
    user_id = callback.from_user.id
    try:
        if not await db.get_user(user_id):
            await callback.answer("❌ Avval /start buyrug'ini bosing.", show_alert=True)
            return

        win_msg = await perform_spin(user_id)

        if win_msg is None:
            await callback.answer(
                f"🚫 Bugungi {DAILY_FREE_SPINS} ta bepul imkoniyatingiz tugadi!",
                show_alert=True,
            )
            await callback.message.answer(await build_limit_text(callback.bot, user_id))
            return

        await callback.answer("🎰 Baraban aylantirildi!")
        await callback.message.answer(win_msg)

        # Asosiy menyudagi balans va limit matnini yangilash
        try:
            await callback.message.edit_text(
                await build_coins_text(user_id),
                reply_markup=get_coins_keyboard(),
            )
        except Exception as e:
            logger.error(f"Xabar matnini tahrirlashda xatolik: {e}")

    except Exception:
        logger.exception("cb_spin_wheel xatolik")
        await callback.answer("❌ Xatolik yuz berdi.", show_alert=True)


# ============================================================
# VIP XARID (coin evaziga)
# ============================================================

@router.callback_query(F.data == "coin_buy_vip")
async def cb_buy_vip(callback: CallbackQuery) -> None:
    """Coin evaziga VIP xarid qilish."""
    user_id = callback.from_user.id
    try:
        # deduct_coins balansni tekshirish va ayirishni bitta amalda bajaradi
        if not await db.deduct_coins(user_id, VIP_PRICE_COINS, reason="VIP xarid qilish"):
            await callback.answer(
                f"❌ Kamida {VIP_PRICE_COINS} coin bo'lishi kerak!",
                show_alert=True,
            )
            return

        try:
            await db.set_vip(user_id, days=VIP_DAYS)
        except Exception:
            # VIP berilmasa, coinlarni qaytarib qo'yamiz
            await db.add_coins(user_id, VIP_PRICE_COINS)
            raise

        await callback.answer(f"🎉 {VIP_DAYS} kunlik VIP status faollashtirildi!", show_alert=True)

        try:
            await callback.message.edit_text(
                await build_coins_text(user_id),
                reply_markup=get_coins_keyboard(),
            )
        except Exception as e:
            logger.error(f"Xabar matnini tahrirlashda xatolik: {e}")

    except Exception:
        logger.exception("cb_buy_vip xatolik")
        await callback.answer("❌ Xatolik yuz berdi.", show_alert=True)