# database.py
import os
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger, String, Integer, DateTime, select, func
from sqlalchemy.exc import IntegrityError


# =========================================================
# إعداد قاعدة البيانات المحلية (SQLite)
# =========================================================
# الملف سيُنشأ تلقائياً في: ./data/bot.db
# =========================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./data/bot.db",
)

# تأكد أن مجلد data موجود
if DATABASE_URL.startswith("sqlite"):
    db_path = DATABASE_URL.split("///")[-1]
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# =========================================================
# جدول المستخدمين
# =========================================================

class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    username: Mapped[str] = mapped_column(String(255), default="")
    referrals: Mapped[int] = mapped_column(Integer, default=0)
    language: Mapped[str] = mapped_column(String(5), default="ar")  # ← جديد
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

# =========================================================
# إنشاء الجداول
# =========================================================

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# =========================================================
# الدوال المساعدة (تستخدم في server.py)
# =========================================================

async def get_or_create_user(
    telegram_id: int,
    name: str,
    username: str,
) -> tuple[User, bool]:
    """
    يرجع (المستخدم, هل هو جديد؟)

    محمي ضد race condition:
    لو أرسل المستخدم /start مرتين في نفس اللحظة،
    الطلب الثاني سيجد المستخدم موجوداً ويعيده بدل رمي خطأ.
    """
    async with SessionLocal() as session:
        user = await session.get(User, telegram_id)
        if user:
            return user, False

        user = User(
            telegram_id=telegram_id,
            name=name,
            username=username or "",
            referrals=0,
            created_at=datetime.utcnow(),
        )
        session.add(user)

        try:
            await session.commit()
            await session.refresh(user)
            return user, True

        except IntegrityError:
            # مستخدم آخر أضافه في نفس اللحظة → أعد جلبه
            await session.rollback()
            user = await session.get(User, telegram_id)
            if user:
                return user, False
            # حالة نادرة جداً: فشل الإدخال ولم يوجد المستخدم
            raise


async def get_user(telegram_id: int) -> Optional[User]:
    async with SessionLocal() as session:
        return await session.get(User, telegram_id)


async def increment_referrals(telegram_id: int) -> bool:
    """يزيد عدّاد الإحالات بمقدار 1"""
    async with SessionLocal() as session:
        user = await session.get(User, telegram_id)
        if not user:
            return False
        user.referrals += 1
        await session.commit()
        return True


async def get_total_users() -> int:
    async with SessionLocal() as session:
        total = await session.scalar(select(func.count()).select_from(User))
        return total or 0


async def get_stats() -> dict:
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    start_of_month = now.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    async with SessionLocal() as session:
        total = await session.scalar(select(func.count()).select_from(User))
        last_7 = await session.scalar(
            select(func.count()).select_from(User)
            .where(User.created_at >= seven_days_ago)
        )
        this_month = await session.scalar(
            select(func.count()).select_from(User)
            .where(User.created_at >= start_of_month)
        )

    return {
        "total": total or 0,
        "last_7_days": last_7 or 0,
        "this_month": this_month or 0,
    }

async def set_user_language(telegram_id: int, language: str) -> bool:
    """تحديث لغة المستخدم"""
    async with SessionLocal() as session:
        user = await session.get(User, telegram_id)
        if not user:
            return False
        user.language = language
        await session.commit()
        return True
