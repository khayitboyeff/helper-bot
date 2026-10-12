# 🤖 Yordamchi Bot

Production darajadagi, to'liq funksional Telegram bot — hujjat vositalari, prompt yaratish, PRO to'lovlari va coin tizimi bilan.

## 📁 Loyiha strukturasi

```
YordamchiBot/
│
├── bot.py                 # Botni ishga tushirish nuqtasi
├── config.py               # Barcha sozlamalar (.env dan o'qiydi)
├── requirements.txt         # Python kutubxonalari
├── .env                     # Maxfiy tokenlar (BU FAYLNI HECH KIMGA BERMANG)
├── README.md
│
├── database/
│   ├── db.py                # Database bilan ishlash (CRUD)
│   └── models.py             # SQL jadval sxemalari
│
├── handlers/
│   ├── start.py              # /start, asosiy menu
│   ├── tools.py               # Video->Audio, OCR, PDF, Tarjimon
│   ├── profile.py             # Profil, referral, coin olish
│   ├── vip.py                 # VIP obuna
│   └── admin.py               # Admin panel
│
├── services/
│   ├── ocr.py                  # Tesseract OCR + FFmpeg video->audio
│   ├── translator.py           # 100+ tilga tarjima
│   └── pdf.py                  # Matndan PDF yaratish
│
└── utils/
    ├── logger.py                # Logging tizimi
    └── helpers.py                # Yordamchi funksiyalar
```

## ⚙️ Talab qilinadigan dasturlar

Botni ishga tushirishdan oldin quyidagilar kompyuteringizda o'rnatilgan bo'lishi kerak:

1. **Python 3.12+**
2. **FFmpeg** — video/audio konvertatsiya uchun
3. **Tesseract OCR** — rasmdan matn olish uchun

### FFmpeg o'rnatish

**Windows:**
1. https://www.gyan.dev/ffmpeg/builds/ saytidan yuklab oling
2. Arxivdan chiqarib, `bin` papkasini PATH'ga qo'shing
3. Tekshirish: `ffmpeg -version`

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg -y
```

**Mac:**
```bash
brew install ffmpeg
```

### Tesseract OCR o'rnatish

**Windows:**
1. https://github.com/UB-Mannheim/tesseract/wiki dan installer yuklab oling
2. O'rnatish jarayonida "Additional language data" bo'limidan kerakli tillarni (rus, o'zbek) tanlang
3. `.env` faylida `TESSERACT_CMD` ni to'liq yo'lga o'zgartiring:
   ```
   TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
   ```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install tesseract-ocr -y
sudo apt install tesseract-ocr-rus tesseract-ocr-uzb -y   # qo'shimcha tillar
```

**Mac:**
```bash
brew install tesseract
brew install tesseract-lang   # qo'shimcha tillar
```

## 🚀 O'rnatish va ishga tushirish

### 1. Loyihani yuklab oling va papkaga o'ting

```bash
cd YordamchiBot
```

### 2. Virtual muhit yarating (tavsiya etiladi)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Kutubxonalarni o'rnating

```bash
pip install -r requirements.txt
```

### 4. `.env` faylini sozlang

`.env` faylini oching va quyidagilarni to'ldiring:

```env
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_IDS=your_telegram_id
```

**Bot token olish:**
1. Telegram'da [@BotFather](https://t.me/BotFather) ga o'ting
2. `/newbot` buyrug'ini yuboring
3. Bot nomi va username'ni kiriting
4. Olingan tokenni `.env` fayliga qo'ying

**O'z Telegram ID'ingizni bilish:**
1. [@userinfobot](https://t.me/userinfobot) ga `/start` yuboring
2. Ko'rsatilgan ID'ni `ADMIN_IDS` ga qo'ying

### 5. Botni ishga tushiring

```bash
python bot.py
```

Agar hammasi to'g'ri sozlangan bo'lsa, konsolda quyidagi xabarni ko'rasiz:

```
2026-08-01 12:00:00 | INFO | YordamchiBot | Database muvaffaqiyatli initsializatsiya qilindi.
2026-08-01 12:00:00 | INFO | YordamchiBot | Yordamchi Bot ishga tushmoqda...
```

Endi Telegram'da botingizga `/start` yuboring! ✅

## 🧩 Asosiy funksiyalar

### ⬇️ Downloader
- Havolani to'g'ridan-to'g'ri yuborish orqali avtomatik aniqlash

### 🛠 Media Tools
- Matn → PDF
- Rasmdan matn olish (OCR — Tesseract)
- Matndan AI-prompt yaratish

### 🌍 Tarjimon
- 100+ tilga tarjima (Google Translate asosida)
- Avtomatik manba tilni aniqlash

### 👤 Profil
- Coin va PRO/VIP statusi
- Referral bonus taklifi olib tashlangan

### 💎 VIP tizimi
- Hujjat vositalari uchun kengaytirilgan limit
- To'lov so'rovi orqali (admin tasdiqlaydi)

### 🪙 Coin tizimi
- Reklama ko'rib coin ishlash
- Coin bilan limitdan tashqari xizmatlardan foydalanish

### 🛠 Admin panel

| Buyruq | Tavsif |
|---|---|
| `/admin` | Admin panel menusi |
| `/stats` | Umumiy statistika |
| `/give_vip [id] [kunlar]` | VIP berish |
| `/add_coins [id] [miqdor]` | Coin qo'shish |
| `/ban [id]` | Foydalanuvchini bloklash |
| `/unban [id]` | Blokdan chiqarish |
| `/logs` | Log faylni ko'rish |
| `/broadcast [matn]` | Barchaga xabar yuborish |

## 🗄 Database sxemasi (SQLite)

**users**
| ustun | tavsif |
|---|---|
| id | avtomatik ID |
| telegram_id | Telegram foydalanuvchi ID |
| username | Telegram username |
| coins | coin balansi |
| vip | VIP holati (0/1) |
| referral_id | kim taklif qilgani |
| referral_count | nechta odam taklif qilgani |
| created_at | ro'yxatdan o'tgan sana |

**downloads**
| ustun | tavsif |
|---|---|
| user_id | foydalanuvchi ID |
| type | yuklash turi |
| date | sana |

**payments**
| ustun | tavsif |
|---|---|
| user_id | foydalanuvchi ID |
| amount | summa |
| status | holati (pending/approved) |

## ⚠️ Muhim eslatmalar

- Telegram bot orqali fayl yuborish limiti ~50MB. Katta videolar yuklanmasligi mumkin — bu servislarda `max_filesize` cheklovi shuning uchun qo'yilgan.
- Instagram/TikTok/Facebook ba'zan login/cookie talab qilishi mumkin (platformalar tez-tez o'zgaradi). Kerak bo'lsa, `yt-dlp` uchun cookies faylini qo'shish mumkin.
- Real to'lov tizimi (Payme, Click, Stripe) ulash uchun `handlers/vip.py` va `services/` ichiga tegishli integratsiya qo'shilishi kerak — hozircha admin qo'lda tasdiqlaydi.
- AI image generator funksiyasi kelajakda `services/` ichiga alohida modul sifatida qo'shilishi mumkin (`handlers/tools.py`dagi prompt generatori shu uchun tayyorlab qo'yilgan).

## 🩹 Muammolarni bartaraf etish

**"ModuleNotFoundError" xatoligi:**
```bash
pip install -r requirements.txt
```

**FFmpeg topilmadi xatoligi:**
`.env` faylida `FFMPEG_PATH` to'g'ri ko'rsatilganini tekshiring, yoki FFmpeg PATH'ga qo'shilganini tasdiqlang: `ffmpeg -version`

**Tesseract topilmadi xatoligi:**
`.env` faylida `TESSERACT_CMD` to'g'ri yo'lni ko'rsatishini tekshiring (ayniqsa Windows'da).

**Bot javob bermayapti:**
- `BOT_TOKEN` to'g'riligini tekshiring
- Internet aloqasini tekshiring
- Konsoldagi xatolik loglarini o'qing (`logs/bot.log`)

## 📄 Litsenziya

Bu loyiha shaxsiy va tijorat maqsadlarida erkin ishlatilishi mumkin.

---

Savol yoki muammo bo'lsa, kod ichidagi izohlarni (comments) o'qing — har bir funksiya batafsil izohlangan.


## Yangilangan funksiyalar
- Soddalashtirilgan asosiy menyu: hujjatlar, prompt, profil, PRO va spin/coin. Video yuklab olish olib tashlangan.
- Hujjatlar: matn -> PDF, DOCX -> PDF, DOCX -> Excel (XLSX), PowerPoint (PPTX) -> PDF.
- Teskari konvertatsiyalar ataylab qo'shilmagan.
- PRO paketlari Telegram Stars (XTR) orqali to'lanadi: 1 oy 70 ⭐, 3 oy 189 ⭐, 6 oy 336 ⭐, 12 oy 588 ⭐. Paketlar avtomatik yangilanmaydi. Karta o'tkazmasi Stars to'lovidan alohida va admin tasdig'i bilan faollashadi.
- UZS ko'rsatkichi yo'naltiruvchi narx; Stars miqdori alohida ko'rsatiladi va kurs o'zgarishi mumkin.

### Office PDF eksporti
DOCX/PPTX fayllarini PDF qilish uchun kompyuter/serverga LibreOffice o'rnatilgan va `soffice` yoki `libreoffice` PATH orqali topiladigan bo'lishi kerak.
Windows'da LibreOffice o'rnatilgach terminalni qayta ochib botni ishga tushiring.
DOCX -> Excel uchun `python-docx` va `openpyxl` Python kutubxonalari ishlatiladi.


## Yangilangan funksiyalar
- Gemini AI suhbat: `GEMINI_API_KEY` sozlang; kuniga 200 ta so'rov limiti.
- QR generator: oddiy matn/havola QR va kontakt vizitkasi (ism, telefon, email).
- PRO karta to'lovi: foydalanuvchi `To'lov qilindi` tugmasini bosib chek yuboradi; chek `ADMIN_IDS` dagi adminlarga yuboriladi. PRO avtomatik berilmaydi.
- Telegram Stars to'lovi alohida qoladi.
- Video yuklash va matndan prompt yaratish menyudan olib tashlandi.

`.env` faylida `BOT_TOKEN`, `ADMIN_IDS`, `CARD_NUMBER`, `CARD_HOLDER`, `PAYMENT_ADMIN_CONTACT` va `GEMINI_API_KEY` qiymatlarini sozlang. Gemini API kaliti Google AI Studio'dan olinadi.
