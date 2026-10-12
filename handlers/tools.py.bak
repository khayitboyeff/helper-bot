
import asyncio
import html
import os
from pathlib import Path

from docx import Document as DocxDocument
from openpyxl import Workbook
from pptx import Presentation

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from config import config
from database.db import db
from services.ocr import OCRService, MediaService
from services.pdf import PDFService
from services.translator import TranslatorService
from utils.helpers import generate_temp_filename, cleanup_file
from utils.logger import logger

router = Router(name="tools")


class ToolStates(StatesGroup):
    waiting_for_audio_text = State()
    waiting_for_image = State()
    waiting_for_translate_text = State()
    waiting_for_translate_lang = State()
    waiting_for_office_file = State()


def tools_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📄 Matn → PDF"))
    builder.row(KeyboardButton(text="📝 DOCX → PDF"), KeyboardButton(text="📊 DOCX → Excel"))
    builder.row(KeyboardButton(text="📽 PowerPoint → PDF"))
    builder.row(KeyboardButton(text="🔙 Bosh menu"))
    return builder.as_markup(resize_keyboard=True)


async def check_and_charge(message: Message, cost: int) -> bool:
    """Foydalanuvchidan xizmat narxini yechish (agar limit tugagan bo'lsa)."""
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)
    if not user:
        await message.answer("❌ Avval /start buyrug'ini bosing.")
        return False
    if user["is_banned"]:
        await message.answer("🚫 Siz bloklangansiz.")
        return False

    daily_used = await db.get_daily_usage(telegram_id)
    limit = config.VIP_DAILY_LIMIT if user["vip"] else config.FREE_DAILY_LIMIT

    if daily_used >= limit:
        if user["coins"] < cost:
            await message.answer(
                f"⚠️ Kunlik limitingiz tugadi va coin yetarli emas ({cost} coin kerak).\n"
                "🎁 Coin yig'ing yoki 💎 VIP oling."
            )
            return False
        await db.deduct_coins(telegram_id, cost)
    else:
        await db.increment_daily_usage(telegram_id)

    return True


@router.message(F.text.in_({"🛠 Media Tools", "📄 Hujjatlar"}))
async def show_tools_menu(message: Message) -> None:
    await message.answer("🛠 Media Tools bo'limi. Kerakli vositani tanlang 👇", reply_markup=tools_menu_keyboard())

# ---------------------------------------------------------------
# MATN -> PDF (Audio->PDF o'rniga umumlashtirilgan: matn transkriptdan PDF)
# ---------------------------------------------------------------

@router.message(F.text == "📄 Matn → PDF")
async def ask_text_for_pdf(message: Message, state: FSMContext) -> None:
    await state.set_state(ToolStates.waiting_for_audio_text)
    await message.answer("📄 PDF qilib olmoqchi bo'lgan matningizni yuboring:")


@router.message(ToolStates.waiting_for_audio_text, F.text)
async def process_text_to_pdf(message: Message, state: FSMContext) -> None:
    if not await check_and_charge(message, config.OCR_COST):
        await state.clear()
        return

    status_msg = await message.answer("⏳ PDF tayyorlanmoqda...")
    pdf_path = None

    try:
        pdf_path = await PDFService.text_to_pdf(message.text, title="Yordamchi Bot - Hujjat")
        if not pdf_path:
            await status_msg.edit_text("❌ PDF yaratishda xatolik yuz berdi.")
            return

        await message.answer_document(FSInputFile(pdf_path), caption="📄 Tayyor!")
        await status_msg.delete()
        await db.log_download(message.from_user.id, "text_to_pdf")
    except Exception as e:
        logger.error(f"process_text_to_pdf xatolik: {e}")
        await status_msg.edit_text("❌ Xatolik yuz berdi.")
    finally:
        cleanup_file(pdf_path)
        await state.clear()

# ---------------------------------------------------------------
# TRANSLATOR (Tarjimon)
# ---------------------------------------------------------------

@router.message(F.text == "🌍 Tarjimon")
async def ask_translate_text(message: Message, state: FSMContext) -> None:
    await state.set_state(ToolStates.waiting_for_translate_text)
    await message.answer("🌍 Tarjima qilmoqchi bo'lgan matningizni yuboring:")


@router.message(ToolStates.waiting_for_translate_text, F.text)
async def ask_target_language(message: Message, state: FSMContext) -> None:
    await state.update_data(translate_source_text=message.text)
    await state.set_state(ToolStates.waiting_for_translate_lang)
    await message.answer(
        "🌐 Qaysi tilga tarjima qilay?\n\n"
        "Til kodini yuboring, masalan:\n"
        "<code>uz</code> - O'zbekcha\n"
        "<code>en</code> - Inglizcha\n"
        "<code>ru</code> - Ruscha\n"
        "<code>tr</code> - Turkcha\n"
        "<code>ar</code> - Arabcha\n\n"
        "(100+ til qo'llab-quvvatlanadi, ISO kod bilan yuboring)"
    )


@router.message(ToolStates.waiting_for_translate_lang, F.text)
async def process_translation(message: Message, state: FSMContext) -> None:
    if not await check_and_charge(message, config.TRANSLATE_COST):
        await state.clear()
        return

    data = await state.get_data()
    source_text = data.get("translate_source_text", "")
    target_lang = message.text.strip().lower()

    status_msg = await message.answer("⏳ Tarjima qilinmoqda...")

    try:
        result = await TranslatorService.translate(source_text, target_lang=target_lang)

        if not result:
            await status_msg.edit_text(
                "❌ Tarjima qilishda xatolik. Til kodi to'g'riligini tekshiring (masalan: uz, en, ru)."
            )
            return

        await status_msg.edit_text(f"🌍 <b>Tarjima:</b>\n\n{result}")
        await db.log_download(message.from_user.id, "translate")
    except Exception as e:
        logger.error(f"process_translation xatolik: {e}")
        await status_msg.edit_text("❌ Xatolik yuz berdi.")
    finally:
        await state.clear()


# Office conversions: DOCX -> PDF/XLSX and PPTX -> PDF only.
OFFICE_CONVERSIONS = {
    "📝 DOCX → PDF": ("docx", "pdf"),
    "📊 DOCX → Excel": ("docx", "xlsx"),
    "📽 PowerPoint → PDF": ("pptx", "pdf"),
}


def _register_pdf_font() -> str:
    """Register a Unicode font when available; fall back to ReportLab Helvetica."""
    font_candidates = [
        # Windows
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arial.ttf",
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "calibri.ttf",
        # Common Linux / Railway / Render locations
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    ]
    for font_path in font_candidates:
        if font_path.is_file():
            try:
                if "YordamchiUnicode" not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont("YordamchiUnicode", str(font_path)))
                return "YordamchiUnicode"
            except Exception:
                logger.exception("PDF shriftini ro'yxatdan o'tkazib bo'lmadi")
    return "Helvetica"


def _pdf_text(value: str) -> str:
    """Escape text for ReportLab Paragraph and preserve line breaks."""
    return html.escape(value or "").replace("\n", "<br/>")


def _make_office_pdf(input_path: Path, output_path: Path, source_ext: str) -> None:
    """Build a text-focused PDF without requiring LibreOffice."""
    font_name = _register_pdf_font()
    styles = getSampleStyleSheet()
    styles["Normal"].fontName = font_name
    styles["Normal"].fontSize = 9
    styles["Normal"].leading = 12
    styles["Title"].fontName = font_name
    styles["Heading1"].fontName = font_name
    styles["Heading2"].fontName = font_name

    story = []
    if source_ext == "docx":
        document = DocxDocument(str(input_path))
        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if not text:
                story.append(Spacer(1, 2 * mm))
                continue
            style_name = (paragraph.style.name or "").lower() if paragraph.style else ""
            if "title" in style_name:
                para_style = styles["Title"]
            elif "heading 1" in style_name:
                para_style = styles["Heading1"]
            elif "heading" in style_name:
                para_style = styles["Heading2"]
            else:
                para_style = styles["Normal"]
            story.append(Paragraph(_pdf_text(text), para_style))
            story.append(Spacer(1, 2 * mm))

        for doc_table in document.tables:
            rows = []
            for doc_row in doc_table.rows:
                rows.append([
                    Paragraph(_pdf_text(cell.text), styles["Normal"])
                    for cell in doc_row.cells
                ])
            if rows:
                table = Table(rows, repeatRows=1, hAlign="LEFT")
                table.setStyle(TableStyle([
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(table)
                story.append(Spacer(1, 4 * mm))

    elif source_ext == "pptx":
        presentation = Presentation(str(input_path))
        for slide_number, slide in enumerate(presentation.slides, start=1):
            story.append(Paragraph(f"Slayd {slide_number}", styles["Heading1"]))
            story.append(Spacer(1, 2 * mm))
            for shape in slide.shapes:
                if getattr(shape, "has_text_frame", False):
                    text = shape.text.strip()
                    if text:
                        story.append(Paragraph(_pdf_text(text), styles["Normal"]))
                        story.append(Spacer(1, 2 * mm))
                if getattr(shape, "has_table", False):
                    rows = []
                    for ppt_row in shape.table.rows:
                        rows.append([
                            Paragraph(_pdf_text(cell.text), styles["Normal"])
                            for cell in ppt_row.cells
                        ])
                    if rows:
                        table = Table(rows, repeatRows=1, hAlign="LEFT")
                        table.setStyle(TableStyle([
                            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ]))
                        story.append(table)
                        story.append(Spacer(1, 3 * mm))
            story.append(Spacer(1, 5 * mm))
    else:
        raise ValueError(f"Qo'llab-quvvatlanmaydigan PDF manba turi: {source_ext}")

    if not story:
        story.append(Paragraph("Hujjatda chiqarish mumkin bo'lgan matn topilmadi.", styles["Normal"]))

    pdf = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Yordamchi Bot - Hujjat",
    )
    pdf.build(story)


@router.message(F.text.in_(set(OFFICE_CONVERSIONS)))
async def ask_office_file(message: Message, state: FSMContext) -> None:
    label = message.text
    source_ext, _ = OFFICE_CONVERSIONS[label]
    await state.update_data(conversion=label)
    await state.set_state(ToolStates.waiting_for_office_file)
    await message.answer(f"📎 {label} uchun .{source_ext} faylni yuboring.")


@router.message(ToolStates.waiting_for_office_file, F.document)
async def convert_office_file(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    label = data.get("conversion")
    if label not in OFFICE_CONVERSIONS:
        await state.clear()
        await message.answer("Konvertatsiya tanlovi topilmadi. Qaytadan tanlang.")
        return

    source_ext, target_ext = OFFICE_CONVERSIONS[label]
    doc = message.document
    filename = doc.file_name or f"document.{source_ext}"

    if not filename.lower().endswith("." + source_ext):
        await message.answer(f"❌ Faqat .{source_ext} fayl qabul qilinadi.")
        return
    if doc.file_size and doc.file_size > 15 * 1024 * 1024:
        await message.answer("❌ Fayl hajmi 15 MB dan oshmasin.")
        return

    temp_dir = Path(config.TEMP_DIR)
    temp_dir.mkdir(parents=True, exist_ok=True)
    input_path = temp_dir / f"{message.from_user.id}_{doc.file_unique_id}.{source_ext}"
    output_path = input_path.with_suffix("." + target_ext)
    status = await message.answer("⏳ Hujjat aylantirilmoqda...")

    try:
        telegram_file = await message.bot.get_file(doc.file_id)
        await message.bot.download_file(telegram_file.file_path, destination=input_path)

        if source_ext == "docx" and target_ext == "xlsx":
            document = DocxDocument(str(input_path))
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Hujjat"
            row = 1

            for paragraph in document.paragraphs:
                if paragraph.text.strip():
                    sheet.cell(row=row, column=1, value=paragraph.text)
                    row += 1

            for doc_table in document.tables:
                for doc_row in doc_table.rows:
                    for col, cell in enumerate(doc_row.cells, start=1):
                        sheet.cell(row=row, column=col, value=cell.text)
                    row += 1

            # Make the Excel file easier to read.
            for column_cells in sheet.columns:
                column_letter = column_cells[0].column_letter
                max_length = max(
                    (len(str(cell.value or "")) for cell in column_cells),
                    default=0,
                )
                sheet.column_dimensions[column_letter].width = min(max(max_length + 2, 12), 50)
            sheet.freeze_panes = "A1"
            workbook.save(output_path)
        elif target_ext == "pdf" and source_ext in {"docx", "pptx"}:
            await asyncio.wait_for(
                asyncio.to_thread(_make_office_pdf, input_path, output_path, source_ext),
                timeout=90,
            )
        else:
            raise ValueError(f"Qo'llab-quvvatlanmaydigan konvertatsiya: {source_ext} → {target_ext}")

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("Konvertatsiya natijasi bo'sh")

        await message.answer_document(
            FSInputFile(str(output_path)),
            caption=f"✅ Tayyor: {filename.rsplit('.', 1)[0]}.{target_ext}",
        )
        await db.log_download(message.from_user.id, f"{source_ext}_to_{target_ext}")
        await status.delete()
    except asyncio.TimeoutError:
        await status.edit_text("❌ Konvertatsiya vaqti tugadi. Qayta urinib ko'ring.")
    except Exception:
        logger.exception("Office konvertatsiya xatosi")
        await status.edit_text(
            "❌ Faylni aylantirib bo'lmadi. Fayl turi yoki yaxlitligini tekshiring. "
            "Xatolik tafsiloti server logida saqlandi."
        )
    finally:
        for path in (input_path, output_path):
            try:
                path.unlink(missing_ok=True)
            except Exception:
                logger.warning("Vaqtinchalik faylni o'chirib bo'lmadi: %s", path)
        await state.clear()
