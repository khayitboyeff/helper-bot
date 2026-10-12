"""
"""

from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from config import config
from database.db import db
from services.youtube import YouTubeService
from services.instagram import InstagramService
from utils.helpers import detect_platform, is_valid_url, cleanup_file
from utils.logger import logger

router = Router(name="downloader")


class DownloadStates(StatesGroup):
    waiting_for_link = State()


def downloader_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🎥 YouTube Video"),
    )
    builder.row(
        KeyboardButton(text="📸 Instagram"),
    )
    builder.row(KeyboardButton(text="🔙 Bosh menu"))
    return builder.as_markup(resize_keyboard=True)


async def check_user_limit(message: Message) -> bool:
    """Foydalanuvchi kunlik limitini tekshiradi. Ruxsat bo'lsa True qaytaradi."""
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)

    if not user:
        await message.answer("❌ Avval /start buyrug'ini bosing.")
        return False

    if user["is_banned"]:
        await message.answer("🚫 Siz bloklangansiz. Admin bilan bog'laning.")
        return False

    await db.check_and_expire_vip(telegram_id)
    user = await db.get_user(telegram_id)

    daily_used = await db.get_daily_usage(telegram_id)
    limit = config.VIP_DAILY_LIMIT if user["vip"] else config.FREE_DAILY_LIMIT

    if daily_used >= limit:
        # Coin orqali qoplashga ruxsat berish
        if user["coins"] >= config.DOWNLOAD_COST:
            return True
        await message.answer(
            f"⚠️ Kunlik bepul limitingiz ({limit}) tugadi.\n"
            f"💎 VIP oling yoki 🎁 coin yig'ing (har yuklash uchun {config.DOWNLOAD_COST} coin)."
        )
        return False

    return True


@router.message(F.text == "⬇️ Yuklab olish")
async def show_downloader_menu(message: Message) -> None:
    """Yuklab olish bo'limi menusi."""
    await message.answer(
        "⬇️ Qaysi platformadan yuklab olmoqchisiz?\n\n"
        "Tugmani tanlang yoki to'g'ridan-to'g'ri havolani yuboring 👇",
        reply_markup=downloader_menu_keyboard(),
    )


@router.message(F.text.in_(["🎥 YouTube Video", "🎵 YouTube MP3", "📸 Instagram", "🎬 TikTok", "📘 Facebook"]))
async def ask_for_link(message: Message, state: FSMContext) -> None:
    """Foydalanuvchidan havola so'raladi."""
    mapping = {
        "🎥 YouTube Video": "youtube_video",
        "📸 Instagram": "instagram",
    }
    mode = mapping[message.text]
    await state.update_data(download_mode=mode)
    await state.set_state(DownloadStates.waiting_for_link)
    await message.answer("🔗 Endi havolani (link) yuboring:")


@router.message(DownloadStates.waiting_for_link)
async def process_link(message: Message, state: FSMContext) -> None:
    """Foydalanuvchi yuborgan havolani qayta ishlash."""
    url = message.text.strip()
    data = await state.get_data()
    mode = data.get("download_mode")

    if not is_valid_url(url):
        await message.answer("❌ Noto'g'ri havola. Iltimos, to'g'ri link yuboring.")
        return

    if not await check_user_limit(message):
        await state.clear()
        return

    status_msg = await message.answer("⏳ Yuklab olinmoqda, biroz kuting...")
    filepath = None

    try:
        if mode == "youtube_video":
            filepath = await YouTubeService.download_video(url)
        elif mode == "youtube_audio":
            filepath = await YouTubeService.download_audio(url)
        elif mode == "instagram":
            filepath = await InstagramService.download_video(url)
        if not filepath:
            await status_msg.edit_text(
                "❌ Yuklab olishda xatolik yuz berdi. Havola noto'g'ri yoki video mavjud emas."
            )
            await state.clear()
            return

        telegram_id = message.from_user.id
        user = await db.get_user(telegram_id)
        daily_used = await db.get_daily_usage(telegram_id)
        limit = config.VIP_DAILY_LIMIT if user["vip"] else config.FREE_DAILY_LIMIT

        # Limitdan oshgan bo'lsa, coin yechish
        if daily_used >= limit:
            await db.deduct_coins(telegram_id, config.DOWNLOAD_COST)
        else:
            await db.increment_daily_usage(telegram_id)

        input_file = FSInputFile(filepath)

        if mode == "youtube_audio":
            await message.answer_audio(input_file, caption="🎵 Mana sizning musiqangiz!")
        else:
            await message.answer_video(input_file, caption="✅ Mana sizning videongiz!")

        await status_msg.delete()
        await db.log_download(telegram_id, mode, url)
        logger.info(f"Yuklab olindi: {telegram_id} -> {mode} -> {url}")

    except Exception as e:
        logger.error(f"process_link xatolik: {e}")
        await status_msg.edit_text("❌ Xatolik yuz berdi. Keyinroq qayta urinib ko'ring.")
    finally:
        cleanup_file(filepath)
        await state.clear()


@router.message(F.text.regexp(r"https?://\S+"))
async def auto_detect_link(message: Message, state: FSMContext) -> None:
    """Foydalanuvchi to'g'ridan-to'g'ri havola yuborsa, platformani avtomatik aniqlaydi."""
    url = message.text.strip()
    platform = detect_platform(url)

    if not platform:
        await message.answer(
            "❓ Bu havola qaysi platformaga tegishli ekanligini aniqlay olmadim.\n"
            "YouTube, Instagram, TikTok yoki Facebook havolasini yuboring."
        )
        return

    mode_map = {
        "youtube": "youtube_video",
        "instagram": "instagram",
    }
    await state.update_data(download_mode=mode_map[platform])
    await process_link(message, state)
