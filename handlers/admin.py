"""
handlers/admin.py
Admin panel: statistikalar, VIP berish, coin qo'shish, loglarni ko'rish,
foydalanuvchilarni bloklash/blokdan chiqarish, barchaga xabar yuborish (broadcast).
"""

import os

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile

from config import config
from database.db import db
from utils.helpers import is_admin
from utils.logger import logger

router = Router(name="admin")


def admin_only(handler):
    """Decorator o'rniga oddiy tekshiruv funksiyasi sifatida ishlatiladi (har handler ichida chaqiriladi)."""
    return handler


@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    """Admin panel bosh menu."""
    if not is_admin(message.from_user.id):
        await message.answer("🚫 Bu buyruq faqat adminlar uchun.")
        return

    text = (
        "🛠 <b>Admin Panel</b>\n\n"
        "/stats — Statistikani ko'rish\n"
        "/give_vip [user_id] [kunlar] — VIP berish\n"
        "/add_coins [user_id] [miqdor] — Coin qo'shish\n"
        "/ban [user_id] — Foydalanuvchini bloklash\n"
        "/unban [user_id] — Blokdan chiqarish\n"
        "/logs — Oxirgi loglarni ko'rish\n"
        "/broadcast [xabar] — Barchaga xabar yuborish"
    )
    await message.answer(text)


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """Bot statistikasini ko'rsatadi."""
    if not is_admin(message.from_user.id):
        return

    try:
        total_users = await db.count_users()
        vip_users = await db.count_vip_users()
        total_downloads = await db.count_downloads()

        text = (
            "📊 <b>Bot statistikasi</b>\n\n"
            f"👥 Jami foydalanuvchilar: <b>{total_users}</b>\n"
            f"💎 VIP foydalanuvchilar: <b>{vip_users}</b>\n"
            f"⬇️ Jami yuklab olishlar: <b>{total_downloads}</b>\n"
        )
        await message.answer(text)
    except Exception as e:
        logger.error(f"cmd_stats xatolik: {e}")
        await message.answer("❌ Xatolik yuz berdi.")


@router.message(Command("give_vip"))
async def cmd_give_vip(message: Message) -> None:
    """Foydalanuvchiga VIP beradi. Format: /give_vip [user_id] [kunlar]"""
    if not is_admin(message.from_user.id):
        return

    try:
        parts = message.text.split()
        if len(parts) < 2 or not parts[1].isdigit():
            await message.answer("❗ Format: /give_vip [user_id] [kunlar(ixtiyoriy, default=30)]")
            return

        target_id = int(parts[1])
        days = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 30

        user = await db.get_user(target_id)
        if not user:
            await message.answer("❌ Bunday foydalanuvchi topilmadi.")
            return

        await db.set_vip(target_id, days)
        await message.answer(f"✅ Foydalanuvchi {target_id} ga {days} kunlik VIP berildi.")

        try:
            await message.bot.send_message(
                target_id, f"🎉 Tabriklaymiz! Sizga {days} kunlik VIP status berildi!"
            )
        except Exception:
            pass

        logger.info(f"Admin {message.from_user.id} -> VIP berdi: {target_id} ({days} kun)")
    except Exception as e:
        logger.error(f"cmd_give_vip xatolik: {e}")
        await message.answer("❌ Xatolik yuz berdi.")


@router.message(Command("add_coins"))
async def cmd_add_coins(message: Message) -> None:
    """Foydalanuvchiga coin qo'shadi. Format: /add_coins [user_id] [miqdor]"""
    if not is_admin(message.from_user.id):
        return

    try:
        parts = message.text.split()
        if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
            await message.answer("❗ Format: /add_coins [user_id] [miqdor]")
            return

        target_id = int(parts[1])
        amount = int(parts[2])

        user = await db.get_user(target_id)
        if not user:
            await message.answer("❌ Bunday foydalanuvchi topilmadi.")
            return

        await db.add_coins(target_id, amount)
        await message.answer(f"✅ {target_id} ga {amount} coin qo'shildi.")

        try:
            await message.bot.send_message(target_id, f"🎁 Sizga {amount} coin qo'shildi!")
        except Exception:
            pass

        logger.info(f"Admin {message.from_user.id} -> coin qo'shdi: {target_id} (+{amount})")
    except Exception as e:
        logger.error(f"cmd_add_coins xatolik: {e}")
        await message.answer("❌ Xatolik yuz berdi.")


@router.message(Command("ban"))
async def cmd_ban(message: Message) -> None:
    """Foydalanuvchini bloklaydi. Format: /ban [user_id]"""
    if not is_admin(message.from_user.id):
        return

    try:
        parts = message.text.split()
        if len(parts) != 2 or not parts[1].isdigit():
            await message.answer("❗ Format: /ban [user_id]")
            return

        target_id = int(parts[1])
        await db.ban_user(target_id, True)
        await message.answer(f"🚫 Foydalanuvchi {target_id} bloklandi.")
        logger.info(f"Admin {message.from_user.id} -> bloklandi: {target_id}")
    except Exception as e:
        logger.error(f"cmd_ban xatolik: {e}")
        await message.answer("❌ Xatolik yuz berdi.")


@router.message(Command("unban"))
async def cmd_unban(message: Message) -> None:
    """Foydalanuvchini blokdan chiqaradi. Format: /unban [user_id]"""
    if not is_admin(message.from_user.id):
        return

    try:
        parts = message.text.split()
        if len(parts) != 2 or not parts[1].isdigit():
            await message.answer("❗ Format: /unban [user_id]")
            return

        target_id = int(parts[1])
        await db.ban_user(target_id, False)
        await message.answer(f"✅ Foydalanuvchi {target_id} blokdan chiqarildi.")
        logger.info(f"Admin {message.from_user.id} -> blokdan chiqardi: {target_id}")
    except Exception as e:
        logger.error(f"cmd_unban xatolik: {e}")
        await message.answer("❌ Xatolik yuz berdi.")


@router.message(Command("logs"))
async def cmd_logs(message: Message) -> None:
    """Oxirgi log faylni yuboradi."""
    if not is_admin(message.from_user.id):
        return

    try:
        if os.path.exists(config.LOG_FILE):
            await message.answer_document(FSInputFile(config.LOG_FILE), caption="📋 Bot loglari")
        else:
            await message.answer("⚠️ Log fayl hali mavjud emas.")
    except Exception as e:
        logger.error(f"cmd_logs xatolik: {e}")
        await message.answer("❌ Xatolik yuz berdi.")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message) -> None:
    """Barcha foydalanuvchilarga xabar yuboradi. Format: /broadcast [xabar matni]"""
    if not is_admin(message.from_user.id):
        return

    try:
        text_parts = message.text.split(maxsplit=1)
        if len(text_parts) < 2:
            await message.answer("❗ Format: /broadcast [xabar matni]")
            return

        broadcast_text = text_parts[1]
        users = await db.get_all_users()

        sent, failed = 0, 0
        status_msg = await message.answer(f"📢 Yuborilmoqda... (0/{len(users)})")

        for user in users:
            try:
                await message.bot.send_message(user["telegram_id"], broadcast_text)
                sent += 1
            except Exception:
                failed += 1

        await status_msg.edit_text(f"✅ Xabar yuborildi!\n📤 Muvaffaqiyatli: {sent}\n❌ Xato: {failed}")
        logger.info(f"Broadcast yuborildi: {sent} muvaffaqiyatli, {failed} xato")
    except Exception as e:
        logger.error(f"cmd_broadcast xatolik: {e}")
        await message.answer("❌ Xatolik yuz berdi.")
