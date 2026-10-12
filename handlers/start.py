
"""
handlers/start.py
/start komandasi, /help, asosiy menu va referral tizimining kirish nuqtasi.
"""
 
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder
 
from database.db import db
from utils.logger import logger
 
router = Router(name="start")
 
 
def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Asosiy menu tugmalari (Reply keyboard)."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📄 Hujjatlar"),
        KeyboardButton(text="🤖 Gemini AI"),
    )
    builder.row(
        KeyboardButton(text="👤 Profil"),
    )
    builder.row(
        KeyboardButton(text="💎 PRO obuna"),
        KeyboardButton(text="📱 QR Kod"),
    )
    return builder.as_markup(resize_keyboard=True)
 
 
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """/start komandasi - foydalanuvchini ro'yxatdan o'tkazadi va menu ko'rsatadi."""
    try:
        await state.clear()
        telegram_id = message.from_user.id
        username = message.from_user.username
        full_name = message.from_user.full_name
 
 
        existing_user = await db.get_user(telegram_id)
 
        if not existing_user:
            await db.add_user(telegram_id, username, full_name, None)
        else:
            await db.update_user_info(telegram_id, username, full_name)
 
        text = (
            f"👋 Assalomu alaykum, <b>{full_name}</b>!\n\n"
            "🤖 <b>Yordamchi Bot</b>ga xush kelibsiz!\n\n"
            "Men sizga quyidagilarda yordam bera olaman:\n"
            "📄 PDF va hujjat konvertatsiyasi\n"
            "🤖 Gemini AI bilan suhbat (kuniga 200 ta so'rov)\n"
            "📱 Matn va kontakt uchun QR kod\n"
            "💎 PRO obuna: Telegram Stars yoki karta orqali\n"
            "🪙 Spin va Coin tizimi\n\n"
            "Quyidagi menudan kerakli bo'limni tanlang 👇"
        )
 
        await message.answer(text, reply_markup=main_menu_keyboard())
        logger.info(f"Foydalanuvchi /start bosdi: {telegram_id}")
    except Exception as e:
        logger.error(f"cmd_start xatolik: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
 
 
@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """/help komandasi."""
    text = (
        "📖 <b>Yordam va qo'llanma</b>\n\n"
        "<b>Bo'limlar:</b>\n"
        "📄 <b>Hujjatlar</b> — PDF va Office hujjatlari\n"
        "🤖 <b>Gemini AI</b> — AI bilan suhbat (kuniga 200 ta so'rov)\n"
        "📱 <b>QR Kod</b> — matn/link yoki kontakt vizitkasi\n"
        "🌍 <b>Tarjimon</b> — istalgan matnni tarjima qilish\n"
        "👤 <b>Profil</b> — hisobingiz va Coin balansi\n"
        "💎 <b>VIP</b> — qo'shimcha limit va imkoniyatlar\n"

        "<b>Buyruqlar:</b>\n"
        "/start - Botni ishga tushirish\n"
        "/profile - Profilim\n"
        "/coins - Coin balansim\n"
        "/daily - Kunlik mukofot\n"
        "/spin - Aylantirish\n"
        "/top - Eng faol foydalanuvchilar\n"
        "/vip - VIP imkoniyatlari\n"
        "/settings - Sozlamalar\n\n"
        "Savol bo'lsa, admin bilan bog'laning."
    )
    await message.answer(text)
 
 
@router.message(F.text == "🔙 Bosh menu")
async def back_to_main(message: Message) -> None:
    """Asosiy menuga qaytish."""
    await message.answer("🏠 Asosiy menu", reply_markup=main_menu_keyboard())
 