"""
services/ai_image.py

AI rasm yaratish service layer.
Bu faylda Telegram/aiogram routerlari yo'q.
"""

import random
import urllib.parse

import aiohttp

from utils.logger import logger


TRANSLATE_URL = "https://api.mymemory.translated.net/get"
IMAGE_BASE_URL = "https://image.pollinations.ai/prompt"

DEFAULT_ATTEMPTS = 3
IMAGE_WIDTH = 1024
IMAGE_HEIGHT = 1024

QUALITY_SUFFIX = (
    "highly detailed, realistic, high quality, 4k"
)


async def translate_to_english(
    text: str,
    source_lang: str = "uz",
) -> str:

    if not text:
        return text

    params = {
        "q": text,
        "langpair": f"{source_lang}|en",
    }

    try:
        timeout = aiohttp.ClientTimeout(total=15)

        connector = aiohttp.TCPConnector(
            ssl=False
        )

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
        ) as session:

            async with session.get(
                TRANSLATE_URL,
                params=params,
            ) as response:

                if response.status != 200:
                    logger.warning(
                        f"MyMemory API status: "
                        f"{response.status}"
                    )
                    return text

                data = await response.json()

                translated = (
                    data
                    .get("responseData", {})
                    .get("translatedText")
                )

                if translated:
                    return translated

    except Exception as error:

        logger.warning(
            f"Tarjima xatolik: {error}"
        )

    return text


async def generate_image(
    prompt_en: str,
    attempts: int = DEFAULT_ATTEMPTS,
) -> bytes | None:

    if not prompt_en:
        return None

    encoded_prompt = urllib.parse.quote(
        prompt_en,
        safe="",
    )

    for attempt in range(
        1,
        attempts + 1
    ):

        seed = random.randint(
            1,
            999_999_999,
        )

        image_url = (
            f"{IMAGE_BASE_URL}/{encoded_prompt}"
            f"?width={IMAGE_WIDTH}"
            f"&height={IMAGE_HEIGHT}"
            f"&seed={seed}"
            f"&model=flux"
            f"&nologo=true"
            f"&enhance=true"
        )

        try:

            connector = aiohttp.TCPConnector(
                ssl=False
            )

            timeout = aiohttp.ClientTimeout(
                total=90
            )

            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
            ) as session:

                async with session.get(
                    image_url
                ) as response:

                    if response.status == 200:

                        image_bytes = (
                            await response.read()
                        )

                        if len(image_bytes) > 5000:

                            logger.info(
                                f"AI rasm yaratildi. "
                                f"Urinish: {attempt}"
                            )

                            return image_bytes

                    logger.warning(
                        f"AI rasm urinish "
                        f"{attempt}: "
                        f"HTTP {response.status}"
                    )

        except Exception as error:

            logger.warning(
                f"AI rasm urinish {attempt} "
                f"xatolik: {error}"
            )

    return None


async def create_ai_image(
    prompt: str,
    source_lang: str = "uz",
) -> bytes | None:

    if not prompt:
        return None

    prompt_en = await translate_to_english(
        prompt,
        source_lang=source_lang,
    )

    enhanced_prompt = (
        f"{prompt_en}, {QUALITY_SUFFIX}"
    )

    logger.info(
        f"AI image prompt: {enhanced_prompt}"
    )

    return await generate_image(
        enhanced_prompt
    )