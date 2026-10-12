"""Ikki xil QR: oddiy matn/URL va kontakt vizitkasi."""
import io
import qrcode
from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

router = Router(name="qr_code")

class QRCodeState(StatesGroup):
    waiting_for_text = State()
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_email = State()

def qr_menu():
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text="🔤 Matn/Link QR"), KeyboardButton(text="👤 Kontakt QR"))
    b.row(KeyboardButton(text="🔙 Bosh menu"))
    return b.as_markup(resize_keyboard=True)

def send_qr_payload(payload: str) -> BufferedInputFile:
    img = qrcode.make(payload)
    buff = io.BytesIO(); img.save(buff, format="PNG")
    return BufferedInputFile(buff.getvalue(), filename="yordamchi_qr.png")

@router.message(F.text == "📱 QR Kod")
@router.message(F.text == "📱 QR Kod Yaratish")
async def qr_code_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("📱 <b>QR kod yaratish</b>\nIkki turdan birini tanlang:", reply_markup=qr_menu())

@router.message(F.text == "🔤 Matn/Link QR")
async def ask_text(message: Message, state: FSMContext):
    await state.set_state(QRCodeState.waiting_for_text)
    await message.answer("QR kodga aylantirish uchun matn yoki havolani yuboring:")

@router.message(QRCodeState.waiting_for_text, F.text)
async def process_text(message: Message, state: FSMContext):
    payload = message.text.strip()
    if not payload or len(payload) > 2500:
        await message.answer("Matn bo'sh yoki juda uzun. 2500 belgigacha yuboring."); return
    try:
        await message.answer_photo(send_qr_payload(payload), caption="✅ Matn/Link QR kodingiz tayyor.")
    except Exception:
        await message.answer("QR yaratishda xatolik yuz berdi.")
    finally:
        await state.clear()

@router.message(F.text == "👤 Kontakt QR")
async def ask_name(message: Message, state: FSMContext):
    await state.set_state(QRCodeState.waiting_for_name)
    await message.answer("👤 Vizitka uchun ism va familiyangizni yuboring:")

@router.message(QRCodeState.waiting_for_name, F.text)
async def save_name(message: Message, state: FSMContext):
    await state.update_data(contact_name=message.text.strip())
    await state.set_state(QRCodeState.waiting_for_phone)
    await message.answer("📞 Telefon raqamingizni yuboring (yoki — belgisi):")

@router.message(QRCodeState.waiting_for_phone, F.text)
async def save_phone(message: Message, state: FSMContext):
    await state.update_data(contact_phone=message.text.strip())
    await state.set_state(QRCodeState.waiting_for_email)
    await message.answer("✉️ Email manzilingizni yuboring (yoki — belgisi):")

@router.message(QRCodeState.waiting_for_email, F.text)
async def save_email(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data.get("contact_name", "").replace(";", " ").replace("\n", " ")
    phone = data.get("contact_phone", "").strip()
    email = message.text.strip()
    lines = ["BEGIN:VCARD", "VERSION:3.0", f"FN:{name}"]
    if phone and phone != "—": lines.append(f"TEL;TYPE=CELL:{phone}")
    if email and email != "—": lines.append(f"EMAIL:{email}")
    lines.append("END:VCARD")
    try:
        await message.answer_photo(send_qr_payload("\r\n".join(lines)), caption="✅ Kontakt vizitkangiz QR ko'rinishida tayyor.")
    except Exception:
        await message.answer("QR yaratishda xatolik yuz berdi.")
    finally:
        await state.clear()
