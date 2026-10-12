import urllib.parse
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()

# Rasm yaratish uchun holat
class ImageGenState(StatesGroup):
    waiting_for_prompt = State()

# Foydalanuvchi "🎨 AI Rasm" tugmasini bosganda
@router.message(F.text == "🎨 AI Rasm")
async def ask_prompt_handler(message: Message, state: FSMContext):
    await message.answer(
        "📝 Qanday rasm yaratmoqchisiz? Ta'rifini (prompt) matn ko'rinishida yuboring:\n\n"
        "*(Masalan: 'Futuristic city at night with neon lights')*",
        parse_mode="Markdown"
    )
    await state.set_state(ImageGenState.waiting_for_prompt)

# Prompt qabul qilib rasm generative qilish
@router.message(ImageGenState.waiting_for_prompt)
async def process_image_gen(message: Message, state: FSMContext):
    # Bekor qilish tugmasi yoki matni bosilsa (agar menyuga qaytish kerak bo'lsa)
    if message.text in ["⬅️ Orqaga", "/cancel"]:
        await state.clear()
        await message.answer("Rasm yaratish bekor qilindi.")
        return

    prompt = message.text.strip()
    wait_msg = await message.answer("🎨 Rasm yaratilmoqda, bir oz kuting...")

    try:
        # URL uchun matnni xavfsiz kodlash
        encoded_prompt = urllib.parse.quote(prompt)
        
        # Pollinations API (Flux modeli, logotipsiz)
        image_url = f"https://pollinations.ai/p/{encoded_prompt}?width=1024&height=1024&model=flux&nologo=true"

        await message.answer_photo(
            photo=image_url,
            caption=f"✨ **Natija:** `{prompt}`",
            parse_mode="Markdown"
        )
        await wait_msg.delete()

    except Exception:
        await wait_msg.edit_text("❌ Rasmni yaratishda xatolik yuz berdi. Qaytadan urinib ko'ring.")
    
    # Ish tugagach state'dan chiqaramiz
    await state.clear()