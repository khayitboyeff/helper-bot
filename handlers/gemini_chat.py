
"""Gemini AI bilan suhbat: FREE uchun kunlik limit, PRO uchun cheksiz so'rov."""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from google import genai
from google.genai import types

from config import config
from database.db import db
from utils.logger import logger

router = Router(name="gemini_chat")


class GeminiState(StatesGroup):
    chatting = State()


@router.message(F.text == "🤖 Gemini AI")
async def start_chat(message: Message, state: FSMContext):
    await state.set_state(GeminiState.chatting)
    await state.update_data(gemini_history=[])

    await message.answer(
        "🤖 <b>Gemini AI suhbat</b>\n\n"
        "Savolingizni yozing.\n"
        "🆓 FREE: kuniga 5 ta so'rov.\n"
        "💎 PRO: kunlik limitsiz AI muloqoti.\n\n"
        "Suhbatni to'xtatish uchun /start bosing."
    )


@router.message(GeminiState.chatting, F.text, ~F.text.startswith("/"))
async def chat(message: Message, state: FSMContext):
    if not config.GEMINI_API_KEY:
        await message.answer(
            "⚠️ Gemini API hali sozlanmagan. "
            "Admin .env faylida GEMINI_API_KEY ni kiritsin."
        )
        return

    user_id = message.from_user.id

    try:
        # VIP muddati tugagan bo'lsa, bazada yangilashga urinadi.
        await db.check_and_expire_vip(user_id)

        user = await db.get_user(user_id)

        if not user:
            await message.answer("Avval /start bosing.")
            return

        if user.get("is_banned"):
            await message.answer("Hisobingiz vaqtincha bloklangan.")
            return

        # Bazadagi mavjud VIP holatini tekshirish.
        is_pro = bool(user.get("vip"))

        used = 0
        limit = config.GEMINI_DAILY_LIMIT

        # Faqat FREE foydalanuvchilar uchun kunlik limit.
        if not is_pro:
            used = await db.get_gemini_daily_usage(user_id)

            if used >= limit:
                await message.answer(
                    f"⛔ Bugungi bepul AI limitingiz ({limit} ta) tugadi.\n\n"
                    "💎 Cheksiz AI muloqoti uchun /vip orqali PRO oling."
                )
                return

        status = await message.answer("🤔 O'ylayapman...")

        data = await state.get_data()
        history = data.get("gemini_history", [])[-12:]

        client = genai.Client(api_key=config.GEMINI_API_KEY)

        contents = []

        for item in history:
            contents.append(
                types.Content(
                    role=item["role"],
                    parts=[
                        types.Part.from_text(text=item["text"])
                    ],
                )
            )

        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=message.text.strip()
                    )
                ],
            )
        )

        response = await client.aio.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=(
                    "Sen Yordamchi Bot ichidagi foydali, muloyim "
                    "va aniq AI yordamchisan. Foydalanuvchiga uning "
                    "tilida javob ber, odatda o'zbek tilida. "
                    "Kerak bo'lsa kod va bosqichma-bosqich "
                    "tushuntirish ber."
                ),
                temperature=0.7,
            ),
        )

        answer = (
            response.text
            or "Javob tayyorlab bo'lmadi. Boshqacha so'rab ko'ring."
        ).strip()

        # So'rov muvaffaqiyatli bajarilgandan keyin FREE hisoblagichi.
        if not is_pro:
            await db.increment_gemini_daily_usage(user_id)

        history.extend(
            [
                {
                    "role": "user",
                    "text": message.text.strip(),
                },
                {
                    "role": "model",
                    "text": answer,
                },
            ]
        )

        await state.update_data(
            gemini_history=history[-12:]
        )

        await status.delete()

        # Telegram xabar uzunligi chegarasini hisobga olish.
        for i in range(0, len(answer), 3900):
            await message.answer(answer[i:i + 3900])

        # Faqat FREE foydalanuvchiga qolgan limitni ko'rsatish.
        if not is_pro:
            left = max(0, limit - used - 1)

            if left <= 2:
                await message.answer(
                    f"ℹ️ Bugun yana {left} ta bepul so'rov qoldi."
                )

    except Exception as exc:
        logger.exception("Gemini chat xatosi: %s", exc)

        err = str(exc).lower()

        if any(
            term in err
            for term in (
                "api key not valid",
                "invalid api key",
                "unauthorized",
                "api_key_invalid",
                "401",
            )
        ):
            hint = (
                "❌ Gemini API kaliti noto'g'ri yoki bekor qilingan.\n\n"
                "Google AI Studio'dan yangi kalit oling va .env "
                "faylida GEMINI_API_KEY qiymatini tekshiring."
            )

        elif any(
            term in err
            for term in (
                "permission_denied",
                "permission denied",
                "403",
                "forbidden",
            )
        ):
            hint = (
                "❌ API kalitiga ruxsat berilmagan. Gemini API "
                "yoqilganini va kalit sozlamalarini tekshiring."
            )

        elif any(
            term in err
            for term in ("not found", "404", "model")
        ):
            hint = (
                f"❌ Model topilmadi: {config.GEMINI_MODEL}.\n"
                ".env faylidagi GEMINI_MODEL qiymatini tekshiring."
            )

        elif any(
            term in err
            for term in (
                "quota",
                "resource_exhausted",
                "429",
                "rate limit",
            )
        ):
            hint = (
                "⏳ Gemini API kvotasi yoki tezlik limiti tugagan. "
                "Google AI Studio'dagi kvotani tekshiring."
            )

        else:
            hint = (
                "❌ Gemini bilan bog'lanib bo'lmadi. "
                "Internetni va terminaldagi xato logini tekshiring."
            )

        try:
            await status.edit_text(hint)
        except Exception:
            await message.answer(hint)
