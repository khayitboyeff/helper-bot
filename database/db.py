"""
database/db.py
SQLite database bilan ishlash uchun asosiy Database klassi.
"""
 
import os
from datetime import datetime, timedelta
 
import aiosqlite
 
from config import config
from database.models import ALL_TABLES
from utils.helpers import today_str
from utils.logger import logger
 
 
class Database:
    def __init__(self, db_path: str = config.DB_PATH):
        self.db_path = db_path
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
 
    async def init_db(self) -> None:
        """Database va barcha jadvallarni yaratadi."""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                for table_sql in ALL_TABLES:
                    await conn.execute(table_sql)
 
                # Spin (aylantirish) jadvali
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS coin_spins (
                        telegram_id INTEGER PRIMARY KEY,
                        spin_date TEXT NOT NULL,
                        daily_spins INTEGER DEFAULT 0,
                        extra_spins INTEGER DEFAULT 0,
                        FOREIGN KEY (telegram_id)
                            REFERENCES users (telegram_id)
                    )
                    """
                )
 
                # Gemini uchun alohida kunlik so'rov hisoblagichi
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS gemini_daily_usage (
                        user_id INTEGER NOT NULL,
                        date TEXT NOT NULL,
                        count INTEGER NOT NULL DEFAULT 0,
                        PRIMARY KEY (user_id, date)
                    )
                    """
                )

                # Kunlik mukofot (/daily) jadvali
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS daily_rewards (
                        telegram_id INTEGER PRIMARY KEY,
                        claim_date TEXT NOT NULL,
                        FOREIGN KEY (telegram_id)
                            REFERENCES users (telegram_id)
                    )
                    """
                )
 
                await conn.commit()
 
            logger.info(f"Database muvaffaqiyatli initsializatsiya qilindi: {self.db_path}")
 
        except Exception as e:
            logger.exception(f"Database init xatolik: {e}")
            raise
 
    # USER OPERATSIYALARI
 
    async def add_user(
        self,
        telegram_id: int,
        username: str | None,
        full_name: str | None,
        referral_id: int | None = None,
    ) -> bool:
        try:
            existing = await self.get_user(telegram_id)
            if existing:
                return False
 
            # O'zini o'zi taklif qilish yoki mavjud bo'lmagan odamni
            # referral sifatida yozishning oldini olish
            if referral_id:
                if referral_id == telegram_id:
                    referral_id = None
                elif not await self.get_user(referral_id):
                    referral_id = None
 
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    """
                    INSERT INTO users
                    (telegram_id, username, full_name, referral_id, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        telegram_id,
                        username,
                        full_name,
                        referral_id,
                        datetime.now().isoformat(),
                    ),
                )
                await conn.commit()
 
            if referral_id:
                await self.increment_referral_count(referral_id)
 
            logger.info(f"Yangi foydalanuvchi qo'shildi: {telegram_id}")
            return True
        except Exception as e:
            logger.exception(f"add_user xatolik: {e}")
            return False
 
    async def get_user(self, telegram_id: int) -> dict | None:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    "SELECT * FROM users WHERE telegram_id = ?",
                    (telegram_id,),
                )
                row = await cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.exception(f"get_user xatolik: {e}")
            return None
 
    async def update_user_info(
        self,
        telegram_id: int,
        username: str | None,
        full_name: str | None,
    ) -> None:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    """
                    UPDATE users
                    SET username = ?, full_name = ?
                    WHERE telegram_id = ?
                    """,
                    (username, full_name, telegram_id),
                )
                await conn.commit()
        except Exception as e:
            logger.exception(f"update_user_info xatolik: {e}")
 
    # COIN VA SPIN OPERATSIYALARI
 
    async def get_user_coins(self, telegram_id: int) -> int:
        user = await self.get_user(telegram_id)
        return int(user["coins"] or 0) if user else 0
 
    async def add_coins(self, telegram_id: int, amount: int) -> None:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    """
                    UPDATE users
                    SET coins = COALESCE(coins, 0) + ?
                    WHERE telegram_id = ?
                    """,
                    (amount, telegram_id),
                )
                await conn.commit()
        except Exception as e:
            logger.exception(f"add_coins xatolik: {e}")
            raise
 
    async def deduct_coins(
        self,
        telegram_id: int,
        amount: int,
        reason: str | None = None,
    ) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    """
                    UPDATE users
                    SET coins = coins - ?
                    WHERE telegram_id = ? AND coins >= ?
                    """,
                    (amount, telegram_id, amount),
                )
                await conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.exception(f"deduct_coins xatolik: {e}")
            raise
 
    async def claim_daily_reward(self, telegram_id: int, amount: int) -> bool:
        """
        Kunlik mukofotni beradi (/daily).
        Bugun allaqachon olingan bo'lsa False qaytaradi.
        Tekshirish va yozish bitta amalda bajariladi, shuning uchun
        tez-tez bosilganda ham ikki marta berilmaydi.
        """
        try:
            today = today_str()
 
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    """
                    INSERT INTO daily_rewards (telegram_id, claim_date)
                    VALUES (?, ?)
                    ON CONFLICT(telegram_id) DO UPDATE
                    SET claim_date = excluded.claim_date
                    WHERE daily_rewards.claim_date != excluded.claim_date
                    """,
                    (telegram_id, today),
                )
 
                if cursor.rowcount == 0:
                    return False
 
                await conn.execute(
                    """
                    UPDATE users
                    SET coins = COALESCE(coins, 0) + ?
                    WHERE telegram_id = ?
                    """,
                    (amount, telegram_id),
                )
                await conn.commit()
                return True
        except Exception as e:
            logger.exception(f"claim_daily_reward xatolik: {e}")
            raise
 
    async def get_top_users(self, limit: int = 10) -> list[dict]:
        """Eng ko'p coin to'plagan foydalanuvchilar (/top)."""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    """
                    SELECT telegram_id, username, full_name,
                           COALESCE(coins, 0) AS coins
                    FROM users
                    WHERE COALESCE(is_banned, 0) = 0
                    ORDER BY coins DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.exception(f"get_top_users xatolik: {e}")
            return []
 
    async def get_daily_spins(self, telegram_id: int) -> int:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    """
                    SELECT spin_date, daily_spins
                    FROM coin_spins
                    WHERE telegram_id = ?
                    """,
                    (telegram_id,),
                )
                row = await cursor.fetchone()
 
                if not row or row[0] != today_str():
                    return 0
 
                return int(row[1] or 0)
        except Exception as e:
            logger.exception(f"get_daily_spins xatolik: {e}")
            raise
 
    async def get_extra_spins(self, telegram_id: int) -> int:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    "SELECT extra_spins FROM coin_spins WHERE telegram_id = ?",
                    (telegram_id,),
                )
                row = await cursor.fetchone()
                return int(row[0] or 0) if row else 0
        except Exception as e:
            logger.exception(f"get_extra_spins xatolik: {e}")
            raise
 
    async def add_extra_spins(self, telegram_id: int, amount: int = 1) -> None:
        """Qo'shimcha spin beradi (qator hali yo'q bo'lsa yaratadi)."""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    """
                    INSERT INTO coin_spins
                    (telegram_id, spin_date, daily_spins, extra_spins)
                    VALUES (?, ?, 0, ?)
                    ON CONFLICT(telegram_id) DO UPDATE
                    SET extra_spins = COALESCE(extra_spins, 0) + excluded.extra_spins
                    """,
                    (telegram_id, today_str(), amount),
                )
                await conn.commit()
        except Exception as e:
            logger.exception(f"add_extra_spins xatolik: {e}")
            raise
 
    async def use_extra_spin(self, telegram_id: int) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    """
                    UPDATE coin_spins
                    SET extra_spins = extra_spins - 1
                    WHERE telegram_id = ? AND extra_spins > 0
                    """,
                    (telegram_id,),
                )
                await conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.exception(f"use_extra_spin xatolik: {e}")
            raise
 
    async def increment_daily_spins(self, telegram_id: int) -> None:
        try:
            today = today_str()
 
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    """
                    SELECT spin_date
                    FROM coin_spins
                    WHERE telegram_id = ?
                    """,
                    (telegram_id,),
                )
                row = await cursor.fetchone()
 
                if row is None:
                    await conn.execute(
                        """
                        INSERT INTO coin_spins
                        (telegram_id, spin_date, daily_spins, extra_spins)
                        VALUES (?, ?, 1, 0)
                        """,
                        (telegram_id, today),
                    )
                elif row[0] == today:
                    await conn.execute(
                        """
                        UPDATE coin_spins
                        SET daily_spins = daily_spins + 1
                        WHERE telegram_id = ?
                        """,
                        (telegram_id,),
                    )
                else:
                    await conn.execute(
                        """
                        UPDATE coin_spins
                        SET spin_date = ?, daily_spins = 1
                        WHERE telegram_id = ?
                        """,
                        (today, telegram_id),
                    )
 
                await conn.commit()
        except Exception as e:
            logger.exception(f"increment_daily_spins xatolik: {e}")
            raise
 
    # VIP OPERATSIYALARI
 
    async def set_vip(self, telegram_id: int, days: int = 30) -> None:
        try:
            user = await self.get_user(telegram_id)
            if not user:
                logger.warning(f"VIP berilmadi: foydalanuvchi topilmadi {telegram_id}")
                return
 
            now = datetime.now()
            current_expiry = user.get("vip_expire_at")
            start_date = now
 
            if user.get("vip") == 1 and current_expiry:
                try:
                    expiry = datetime.fromisoformat(current_expiry)
                    if expiry > now:
                        start_date = expiry
                except ValueError:
                    pass
 
            expire_at = (start_date + timedelta(days=days)).isoformat()
 
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    """
                    UPDATE users
                    SET vip = 1, vip_expire_at = ?
                    WHERE telegram_id = ?
                    """,
                    (expire_at, telegram_id),
                )
                await conn.commit()
 
            logger.info(f"VIP faollashtirildi: {telegram_id}, {days} kun")
        except Exception as e:
            logger.exception(f"set_vip xatolik: {e}")
            raise
 
    async def check_and_expire_vip(self, telegram_id: int) -> None:
        try:
            user = await self.get_user(telegram_id)
            if user and user["vip"] == 1 and user["vip_expire_at"]:
                expire_dt = datetime.fromisoformat(user["vip_expire_at"])
 
                if datetime.now() > expire_dt:
                    async with aiosqlite.connect(self.db_path) as conn:
                        await conn.execute(
                            "UPDATE users SET vip = 0 WHERE telegram_id = ?",
                            (telegram_id,),
                        )
                        await conn.commit()
                    logger.info(f"VIP muddati tugadi: {telegram_id}")
        except Exception as e:
            logger.exception(f"check_and_expire_vip xatolik: {e}")
 
    # REFERRAL OPERATSIYALARI
 
    async def increment_referral_count(self, telegram_id: int) -> None:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    """
                    UPDATE users
                    SET referral_count = referral_count + 1
                    WHERE telegram_id = ?
                    """,
                    (telegram_id,),
                )
                await conn.commit()
        except Exception as e:
            logger.exception(f"increment_referral_count xatolik: {e}")
 
    async def mark_referral_rewarded(self, telegram_id: int) -> None:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    """
                    UPDATE users SET referral_rewarded = 1
                    WHERE telegram_id = ?
                    """,
                    (telegram_id,),
                )
                await conn.commit()
        except Exception as e:
            logger.exception(f"mark_referral_rewarded xatolik: {e}")
 
    # FOYDALANUVCHI BOSHQARUVI
 
    async def ban_user(self, telegram_id: int, banned: bool = True) -> None:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    """
                    UPDATE users SET is_banned = ?
                    WHERE telegram_id = ?
                    """,
                    (1 if banned else 0, telegram_id),
                )
                await conn.commit()
        except Exception as e:
            logger.exception(f"ban_user xatolik: {e}")
 
    async def get_all_users(self) -> list[dict]:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute("SELECT * FROM users")
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.exception(f"get_all_users xatolik: {e}")
            return []
 
    async def count_users(self) -> int:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute("SELECT COUNT(*) FROM users")
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.exception(f"count_users xatolik: {e}")
            return 0
 
    async def count_vip_users(self) -> int:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM users WHERE vip = 1"
                )
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.exception(f"count_vip_users xatolik: {e}")
            return 0
 
    # DOWNLOADS OPERATSIYALARI
 
    async def log_download(
        self, user_id: int, download_type: str, url: str = ""
    ) -> None:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    """
                    INSERT INTO downloads (user_id, type, url, date)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, download_type, url, datetime.now().isoformat()),
                )
                await conn.commit()
        except Exception as e:
            logger.exception(f"log_download xatolik: {e}")
 
    async def count_downloads(self) -> int:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute("SELECT COUNT(*) FROM downloads")
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.exception(f"count_downloads xatolik: {e}")
            return 0
 
    # TO'LOV OPERATSIYALARI
 
    async def add_payment(
        self, user_id: int, amount: float, status: str = "pending"
    ) -> None:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    """
                    INSERT INTO payments (user_id, amount, status, date)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, amount, status, datetime.now().isoformat()),
                )
                await conn.commit()
        except Exception as e:
            logger.exception(f"add_payment xatolik: {e}")
 
    # GEMINI KUNLIK SO'ROV LIMITI

    async def get_gemini_daily_usage(self, user_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                "SELECT count FROM gemini_daily_usage WHERE user_id = ? AND date = ?",
                (user_id, today_str()),
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def increment_gemini_daily_usage(self, user_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """INSERT INTO gemini_daily_usage (user_id, date, count) VALUES (?, ?, 1)
                   ON CONFLICT(user_id, date) DO UPDATE SET count = count + 1""",
                (user_id, today_str()),
            )
            await conn.commit()

    # KUNLIK FOYDALANISH LIMITI
 
    async def get_daily_usage(self, user_id: int) -> int:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    """
                    SELECT count FROM daily_usage
                    WHERE user_id = ? AND date = ?
                    """,
                    (user_id, today_str()),
                )
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.exception(f"get_daily_usage xatolik: {e}")
            return 0
 
    async def increment_daily_usage(self, user_id: int) -> None:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    """
                    INSERT INTO daily_usage (user_id, date, count)
                    VALUES (?, ?, 1)
                    ON CONFLICT(user_id, date)
                    DO UPDATE SET count = count + 1
                    """,
                    (user_id, today_str()),
                )
                await conn.commit()
        except Exception as e:
            logger.exception(f"increment_daily_usage xatolik: {e}")
 
 
db = Database()