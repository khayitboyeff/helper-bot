
"""Yordamchi Bot PRO obunasi: Telegram Stars va karta orqali to'lov."""

import sqlite3
from pathlib import Path

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    LabeledPrice,
    PreCheckoutQuery,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import config
from database.db import db
from utils.helpers import is_admin
from utils.logger import logger


router = Router(name="vip")


class CardReceiptState(StatesGroup):
    waiting_receipt = State()


# PRO tariflari
PLANS = {
    "1m": {
        "name": "PRO — 1 oy",
        "days": 30,
        "uzs": 10000,
        "stars": 20,
    },
    "3m": {
        "name": "PRO — 3 oy",
        "days": 90,
        "uzs": 29000,
        "stars": 50,
    },
    "6m": {
        "name": "PRO — 6 oy",
        "days": 180,
        "uzs": 48000,
        "stars": 70,
    },
    "12m": {
        "name": "PRO — 12 oy",
        "days": 365,
        "uzs": 84000,
        "stars": 100,
    },
}


# Cheklarning holatini mavjud bot bazasida alohida jadvalda saqlash.
# Foydalanuvchilar va chat tarixlari jadvallariga tegilmaydi.
def receipt_connection():
    db_path = Path(config.DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path), timeout=10)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS pro_card_receipts (
            receipt_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            plan_key TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.commit()
    return connection


def save_receipt(receipt_id: str, user_id: int, plan_key: str) -> bool:
    """Chekni pending holatida saqlaydi. Takroriy ID qabul qilinmaydi."""
    connection = receipt_connection()
    try:
        connection.execute(
            """
            INSERT INTO pro_card_receipts
                (receipt_id, user_id, plan_key, status)
            VALUES (?, ?, ?, 'pending')
            """,
            (receipt_id, user_id, plan_key),
        )
        connection.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        connection.close()


def get_receipt(receipt_id: str):
    connection = receipt_connection()
    try:
        row = connection.execute(
            """
            SELECT user_id, plan_key, status
            FROM pro_card_receipts
            WHERE receipt_id = ?
            """,
            (receipt_id,),
        ).fetchone()

        if not row:
            return None

        return {
            "user_id": row[0],
            "plan_key": row[1],
            "status": row[2],
        }
    finally:
        connection.close()


def change_receipt_status(
    receipt_id: str,
    expected_status: str,
    new_status: str,
) -> bool:
    """Faqat kutilgan holatdagi chekni bir marta o'zgartiradi."""
    connection = receipt_connection()
    try:
        cursor = connection.execute(
            """
            UPDATE pro_card_receipts
            SET status = ?
            WHERE receipt_id = ? AND status = ?
            """,
            (new_status, receipt_id, expected_status),
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()


# ─────────────────────────────────────────────
# PRO tariflari
# ─────────────────────────────────────────────

@router.message(Command("vip"))
@router.message(F.text.in_({"💎 VIP", "💎 PRO obuna"}))
async def show_vip_info(message: Message):
    user_id = message.from_user.id

    await db.check_and_expire_vip(user_id)
    user = await db.get_user(user_id)

    if not user:
        await message.answer("Avval /start buyrug'ini bosing.")
        return

    status = "Faol" if user.get("vip") else "Faol emas"

    builder = InlineKeyboardBuilder()

    for key, plan in PLANS.items():
        builder.button(
            text=(
                f"{plan['name']} · "
                f"{plan['uzs']:,} so'm · "
                f"{plan['stars']} ⭐"
            ),
            callback_data=f"pro_stars_{key}",
        )

    builder.button(
        text="💳 Karta orqali to'lov",
        callback_data="pro_card_payment",
    )
    builder.adjust(1)

    await message.answer(
        "💎 <b>Yordamchi PRO</b>\n\n"
        f"Obuna holati: <b>{status}</b>\n\n"
        "PRO imkoniyatlari:\n"
        "• AI suhbatida botning kunlik limiti yo'q\n"
        "• Qo'shimcha imkoniyatlar va qulay foydalanish\n"
        "• PDF/Office vositalari, agar botda mavjud bo'lsa\n\n"
        "📅 <b>PRO tariflari:</b>\n"
        + "\n".join(
            f"• {plan['name']} — {plan['uzs']:,} so'm"
            for plan in PLANS.values()
        )
        + "\n\n⭐ Telegram Stars yoki 💳 karta orqali to'lang.\n"
        "Karta to'lovi admin tekshiruvidan keyin faollashtiriladi.\n"
        "Obuna avtomatik yangilanmaydi.",
        reply_markup=builder.as_markup(),
    )


# ─────────────────────────────────────────────
# Karta to'lovi
# ─────────────────────────────────────────────

@router.callback_query(F.data == "pro_card_payment")
async def show_card_payment(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()

    for key, plan in PLANS.items():
        builder.button(
            text=f"{plan['name']} · {plan['uzs']:,} so'm",
            callback_data=f"pro_card_{key}",
        )

    builder.adjust(1)

    await callback.message.answer(
        "💳 <b>Karta orqali to'lov</b>\n\n"
        "PRO muddatini tanlang:",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^pro_card_(1m|3m|6m|12m)$"))
async def show_card_details(callback: CallbackQuery):
    key = callback.data.removeprefix("pro_card_")
    plan = PLANS[key]

    card_number = getattr(config, "CARD_NUMBER", "")
    card_holder = getattr(config, "CARD_HOLDER", "")
    admin_contact = getattr(config, "PAYMENT_ADMIN_CONTACT", "")

    if not card_number:
        await callback.message.answer(
            "⚠️ Karta rekvizitlari sozlanmagan.\n"
            "Admin .env faylida CARD_NUMBER va CARD_HOLDER ni sozlashi kerak."
        )
        await callback.answer()
        return

    text = (
        f"💳 <b>{plan['name']}</b>\n"
        f"To'lov: <b>{plan['uzs']:,} so'm</b>\n\n"
        f"Karta: <code>{card_number}</code>\n"
        f"Qabul qiluvchi: {card_holder or 'ko‘rsatilmagan'}\n\n"
        "To'lovni amalga oshiring, so'ng chekni yuboring. "
        "Admin to'lovni tekshirgach, PRO faollashtiriladi."
    )

    if admin_contact:
        text += f"\nAdmin bilan aloqa: {admin_contact}"

    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ To'lov qilindi",
        callback_data=f"pro_card_paid_{key}",
    )

    await callback.message.answer(
        text,
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^pro_card_paid_(1m|3m|6m|12m)$"))
async def card_paid(callback: CallbackQuery, state: FSMContext):
    key = callback.data.removeprefix("pro_card_paid_")

    await state.set_state(CardReceiptState.waiting_receipt)
    await state.update_data(card_plan=key)

    await callback.message.answer(
        f"📎 <b>{PLANS[key]['name']}</b>\n\n"
        "To'lov chekining rasmini yoki PDF hujjatini yuboring."
    )
    await callback.answer()


@router.message(
    CardReceiptState.waiting_receipt,
    F.photo | F.document,
)
async def receive_card_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    key = data.get("card_plan")
    plan = PLANS.get(key)

    if not plan:
        await state.clear()
        await message.answer(
            "Tarif topilmadi. /vip orqali qaytadan urinib ko'ring."
        )
        return

    admin_ids = config.ADMIN_IDS

    if not admin_ids:
        await message.answer(
            "⚠️ Admin ID sozlanmagan. Chekni tekshirtirish imkoni yo'q."
        )
        await state.clear()
        return

    # Bir xil foydalanuvchi xabaridan hosil bo'ladigan noyob chek ID.
    receipt_id = f"{message.from_user.id}_{message.message_id}"

    try:
        saved = save_receipt(
            receipt_id,
            message.from_user.id,
            key,
        )
    except Exception:
        logger.exception("Chekni bazaga yozishda xato")
        await message.answer(
            "❌ Chekni saqlashda xatolik. Keyinroq qayta urinib ko'ring."
        )
        await state.clear()
        return

    if not saved:
        await message.answer(
            "⚠️ Bu chek allaqachon qabul qilingan."
        )
        await state.clear()
        return

    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ To'lovni tasdiqlash",
        callback_data=f"receipt_ok:{receipt_id}:{key}",
    )
    builder.button(
        text="❌ Rad etish",
        callback_data=f"receipt_no:{receipt_id}",
    )
    builder.adjust(1)

    caption = (
        "💳 <b>Yangi PRO to'lovi — tekshirish kerak</b>\n\n"
        f"👤 Foydalanuvchi: {message.from_user.full_name}\n"
        f"🆔 Telegram ID: <code>{message.from_user.id}</code>\n"
        f"📦 Tarif: {plan['name']}\n"
        f"💰 Summa: {plan['uzs']:,} so'm\n"
        f"🧾 Chek ID: <code>{receipt_id}</code>\n\n"
        "Chekni va pul tushumini tekshiring. "
        "To'lov tasdiqlangandagina PRO bering."
    )

    sent = 0

    for admin_id in admin_ids:
        try:
            await message.bot.send_message(
                admin_id,
                caption,
                reply_markup=builder.as_markup(),
            )
            await message.bot.copy_message(
                chat_id=admin_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )
            sent += 1
        except Exception:
            logger.exception(
                "Chekni adminga yuborishda xato: %s",
                admin_id,
            )

    if sent:
        await message.answer(
            "✅ Chekingiz adminga yuborildi. "
            "To'lov tekshirilgach, sizga xabar beriladi."
        )
    else:
        change_receipt_status(receipt_id, "pending", "delivery_failed")
        await message.answer(
            "⚠️ Chek adminga yetkazilmadi. Admin botni ochib, "
            "ADMIN_IDS sozlamasini tekshirishi kerak."
        )

    await state.clear()


@router.message(CardReceiptState.waiting_receipt)
async def receipt_must_be_file(message: Message):
    await message.answer(
        "Iltimos, chek rasmini yoki PDF/faylini yuboring."
    )


# ─────────────────────────────────────────────
# Admin chekni tasdiqlaydi yoki rad etadi
# ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("receipt_ok:"))
async def approve_card_receipt(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Bu tugma faqat admin uchun.",
            show_alert=True,
        )
        return

    try:
        _, receipt_id, key = callback.data.split(":", 2)
        receipt = get_receipt(receipt_id)

        if not receipt:
            await callback.answer(
                "Chek bazada topilmadi.",
                show_alert=True,
            )
            return

        if receipt["status"] != "pending":
            await callback.answer(
                f"Chek holati: {receipt['status']}. Qayta ishlanmaydi.",
                show_alert=True,
            )
            return

        if receipt["plan_key"] != key or key not in PLANS:
            await callback.answer(
                "Chek tarifi mos kelmadi.",
                show_alert=True,
            )
            return

        user_id = receipt["user_id"]
        user = await db.get_user(user_id)

        if not user:
            await callback.answer(
                "Foydalanuvchi bazada topilmadi.",
                show_alert=True,
            )
            return

        # Bazada pending -> processing o'zgarishi bir marta amalga oshadi.
        if not change_receipt_status(
            receipt_id,
            "pending",
            "processing",
        ):
            await callback.answer(
                "Bu chek boshqa admin tomonidan ko'rib chiqilmoqda yoki ishlangan.",
                show_alert=True,
            )
            return

        plan = PLANS[key]

        try:
            await db.set_vip(user_id, days=plan["days"])
            change_receipt_status(
                receipt_id,
                "processing",
                "approved",
            )
        except Exception:
            logger.exception("PRO berishda xato: user=%s", user_id)
            change_receipt_status(
                receipt_id,
                "processing",
                "pending",
            )
            await callback.answer(
                "PRO berilmadi. Loglarni tekshiring va qayta urinib ko'ring.",
                show_alert=True,
            )
            return

        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "✅ <b>To'lov tasdiqlandi</b>\n\n"
            f"Foydalanuvchi: <code>{user_id}</code>\n"
            f"Tarif: {plan['name']}\n"
            f"Muddat: {plan['days']} kun."
        )

        try:
            await callback.bot.send_message(
                user_id,
                "🎉 <b>PRO obunangiz faollashtirildi!</b>\n\n"
                f"Tarif: {plan['name']}\n"
                f"Muddat: {plan['days']} kun.\n\n"
                "Yordamchi Botdan foydalanishingiz mumkin.",
            )
        except Exception:
            logger.exception(
                "PRO xabarini foydalanuvchiga yuborib bo'lmadi: %s",
                user_id,
            )

        logger.info(
            "Card PRO approved: admin=%s user=%s plan=%s receipt=%s",
            callback.from_user.id,
            user_id,
            key,
            receipt_id,
        )
        await callback.answer("PRO faollashtirildi!")

    except Exception:
        logger.exception("Chekni tasdiqlashda xato")
        await callback.answer(
            "Tasdiqlashda xatolik. Loglarni tekshiring.",
            show_alert=True,
        )


@router.callback_query(F.data.startswith("receipt_no:"))
async def reject_card_receipt(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Bu tugma faqat admin uchun.",
            show_alert=True,
        )
        return

    try:
        _, receipt_id = callback.data.split(":", 1)
        receipt = get_receipt(receipt_id)

        if not receipt:
            await callback.answer(
                "Chek topilmadi.",
                show_alert=True,
            )
            return

        if not change_receipt_status(
            receipt_id,
            "pending",
            "rejected",
        ):
            await callback.answer(
                "Bu chek allaqachon ko'rib chiqilgan.",
                show_alert=True,
            )
            return

        await callback.message.edit_reply_markup(reply_markup=None)

        user_id = receipt["user_id"]

        await callback.message.answer(
            f"❌ Chek rad etildi.\nFoydalanuvchi ID: <code>{user_id}</code>"
        )

        try:
            await callback.bot.send_message(
                user_id,
                "❌ Yuborgan to'lov chekingiz tasdiqlanmadi. "
                "To'lov tafsilotlarini admin bilan tekshiring.",
            )
        except Exception:
            logger.exception(
                "Rad etish xabarini yuborib bo'lmadi: %s",
                user_id,
            )

        await callback.answer("Chek rad etildi.")

    except Exception:
        logger.exception("Chekni rad etishda xato")
        await callback.answer(
            "Xatolik yuz berdi.",
            show_alert=True,
        )


# ─────────────────────────────────────────────
# Telegram Stars
# ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("pro_stars_"))
async def create_stars_invoice(callback: CallbackQuery):
    key = callback.data.removeprefix("pro_stars_")
    plan = PLANS.get(key)

    if not plan:
        await callback.answer(
            "Paket topilmadi.",
            show_alert=True,
        )
        return

    payload = f"yordamchi_pro:{key}:{callback.from_user.id}"

    try:
        await callback.message.answer_invoice(
            title=f"Yordamchi PRO — {plan['name']}",
            description=(
                f"{plan['days']} kunlik PRO obuna. "
                "Avtomatik yangilanish yo'q."
            ),
            payload=payload,
            provider_token="",
            currency="XTR",
            prices=[
                LabeledPrice(
                    label=f"PRO {plan['name']}",
                    amount=plan["stars"],
                )
            ],
        )
        await callback.answer()

    except Exception:
        logger.exception("Stars invoice yaratishda xatolik")
        await callback.answer(
            "To'lov oynasini ochib bo'lmadi.",
            show_alert=True,
        )


@router.pre_checkout_query()
async def confirm_pre_checkout(query: PreCheckoutQuery):
    try:
        parts = query.invoice_payload.split(":")

        valid = (
            len(parts) == 3
            and parts[0] == "yordamchi_pro"
            and parts[1] in PLANS
            and parts[2].isdigit()
            and int(parts[2]) == query.from_user.id
            and query.currency == "XTR"
            and query.total_amount == PLANS[parts[1]]["stars"]
        )

        await query.answer(
            ok=valid,
            error_message=(
                None if valid else "To'lov ma'lumotlari noto'g'ri."
            ),
        )

    except Exception:
        logger.exception("Pre-checkout tekshiruvi xatosi")
        await query.answer(
            ok=False,
            error_message="To'lovni tekshirib bo'lmadi.",
        )


@router.message(F.successful_payment)
async def successful_pro_payment(message: Message):
    payment = message.successful_payment

    try:
        parts = payment.invoice_payload.split(":")

        if (
            len(parts) != 3
            or parts[0] != "yordamchi_pro"
            or not parts[2].isdigit()
        ):
            await message.answer(
                "To'lov qabul qilindi, ammo paketni tekshirishda xato. "
                "Admin bilan bog'laning."
            )
            return

        key = parts[1]
        user_id = int(parts[2])
        plan = PLANS.get(key)

        if (
            not plan
            or user_id != message.from_user.id
            or payment.currency != "XTR"
            or payment.total_amount != plan["stars"]
        ):
            await message.answer(
                "To'lov qabul qilindi, lekin paket ma'lumotlari mos kelmadi. "
                "Admin bilan bog'laning."
            )
            return

        await db.set_vip(user_id, days=plan["days"])

        await message.answer(
            "🎉 <b>PRO faollashtirildi!</b>\n\n"
            f"Tarif: {plan['name']}\n"
            f"Muddat: {plan['days']} kun\n"
            f"To'lov: {payment.total_amount} ⭐\n\n"
            "Obuna muddati tugaganda yana paket tanlashingiz mumkin."
        )

        logger.info(
            "PRO Stars payment: user=%s plan=%s charge=%s",
            user_id,
            key,
            payment.telegram_payment_charge_id,
        )

    except Exception:
        logger.exception("Successful payment handler xatosi")
        await message.answer(
            "To'lov kelib tushdi, ammo PRO faollashtirishda xato. "
            "Admin bilan bog'laning."
        )
