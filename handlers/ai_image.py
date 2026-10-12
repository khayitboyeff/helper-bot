from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile

from services.ai_image import create_ai_image


router = Router()


@router.message(F.text.startswith("/image"))
async def ai_image_command(
    message: Message,
) -> None:

    prompt = message.text[6:].strip()

    if not prompt:

        await message.answer(
            "🎨 <b>AI Rasm Generator</b>\n\n"
            "Rasm yaratish uchun:\n\n"
            "<code>/image qora Malibu kechasi "
            "Toshkent ko'chalarida</code>"
        )

        return

    status = await message.answer(
        "🎨 <b>Rasm tayyorlanmoqda...</b>\n\n"
        "⏳ Biroz kuting..."
    )

    try:

        image_bytes = await create_ai_image(
            prompt=prompt,
            source_lang="uz",
        )

        if not image_bytes:

            await status.edit_text(
                "❌ Rasm yaratib bo'lmadi.\n\n"
                "Keyinroq qayta urinib ko'ring."
            )

            return

        photo = BufferedInputFile(
            image_bytes,
            filename="ai_image.jpg",
        )

        try:
            await status.delete()
        except Exception:
            pass

        await message.answer_photo(
            photo=photo,
            caption=(
                "🎨 <b>AI Image</b>\n\n"
                f"📝 <b>Prompt:</b> {prompt}"
            ),
        )

    except Exception as error:

        print(
            f"AI IMAGE ERROR: {error}"
        )

        await status.edit_text(
            "❌ AI rasm yaratishda "
            "texnik xatolik yuz berdi."
        )