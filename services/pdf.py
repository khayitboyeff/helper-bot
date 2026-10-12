"""
services/pdf.py
Matn/audio transkriptdan PDF fayl yaratish uchun servis.
FPDF2 kutubxonasi ishlatiladi.
"""

import asyncio

from fpdf import FPDF

from utils.helpers import generate_temp_filename
from utils.logger import logger


class PDFService:
    """Matndan PDF fayl yaratish uchun servis klassi."""

    @staticmethod
    async def text_to_pdf(text: str, title: str = "Hujjat") -> str | None:
        """Berilgan matndan PDF fayl yaratadi va fayl yo'lini qaytaradi."""
        output_path = generate_temp_filename("pdf")

        try:
            loop = asyncio.get_event_loop()

            def build_pdf():
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Helvetica", "B", 16)
                pdf.multi_cell(0, 10, title)
                pdf.ln(5)
                pdf.set_font("Helvetica", "", 12)

                # Matnni PDF encoding uchun moslashtirish (lotin bo'lmagan belgilar uchun)
                safe_text = text.encode("latin-1", "replace").decode("latin-1")
                pdf.multi_cell(0, 8, safe_text)
                pdf.output(output_path)

            await loop.run_in_executor(None, build_pdf)
            return output_path
        except Exception as e:
            logger.error(f"PDF yaratishda xatolik: {e}")
            return None
