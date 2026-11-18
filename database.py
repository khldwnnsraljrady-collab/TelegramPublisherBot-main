# database.py
import os
from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import (
    BigInteger,
    String,
    Integer,
    DateTime,
    Boolean,
    Text,
    select,
    func,
    or_,
)
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
# الجداول
# =========================================================

class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    username: Mapped[str] = mapped_column(String(255), default="")
    referrals: Mapped[int] = mapped_column(Integer, default=0)
    language: Mapped[str] = mapped_column(String(5), default="ar")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # اسم الزر الذي يراه المستخدم
    button_text: Mapped[str] = mapped_column(String(64), default="")

    # نص المنشور
    content: Mapped[str] = mapped_column(Text, default="")

    # رابط اختياري + نص زر الرابط
    url: Mapped[str] = mapped_column(String(512), default="")
    url_button_text: Mapped[str] = mapped_column(String(64), default="")

    # الحالة
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # المدة (اختيارية)
    start_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

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
# دوال المستخدمين
# =========================================================

async def get_or_create_user(
    telegram_id: int,
    name: str,
    username: str,
) -> tuple[User, bool]:
    """
    يرجع (المستخدم, هل هو جديد؟)
    محمي ضد race condition.
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
            await session.rollback()
            user = await session.get(User, telegram_id)
            if user:
                return user, False
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


# =========================================================
# دوال المنشورات
# =========================================================

async def create_post(
    button_text: str,
    content: str,
    url: str = "",
    url_button_text: str = "",
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
) -> Post:
    """
    ينشئ منشوراً جديداً.
    يوقف أي منشور آخر مفعّل (منشور واحد فقط مفعّل في أي وقت).
    """
    async with SessionLocal() as session:
        # أوقف كل المنشورات المفعّلة
        result = await session.execute(
            select(Post).where(Post.is_active == True)
        )
        for p in result.scalars().all():
            p.is_active = False

        post = Post(
            button_text=button_text,
            content=content,
            url=url or "",
            url_button_text=url_button_text or "",
            is_active=True,
            start_at=start_at,
            end_at=end_at,
            created_at=datetime.utcnow(),
        )
        session.add(post)
        await session.commit()
        await session.refresh(post)
        return post


async def get_active_posts() -> List[Post]:
    """يرجع المنشورات المفعّلة حالياً (ضمن المدة)."""
    now = datetime.utcnow()
    async with SessionLocal() as session:
        result = await session.execute(
            select(Post)
            .where(Post.is_active == True)
            .where(or_(Post.start_at.is_(None), Post.start_at <= now))
            .where(or_(Post.end_at.is_(None), Post.end_at >= now))
            .order_by(Post.created_at.desc())
        )
        return list(result.scalars().all())


async def get_all_posts() -> List[Post]:
    """يرجع كل المنشورات (للأدمن)."""
    async with SessionLocal() as session:
        result = await session.execute(
            select(Post).order_by(Post.created_at.desc())
        )
        return list(result.scalars().all())


async def get_post(post_id: int) -> Optional[Post]:
    async with SessionLocal() as session:
        return await session.get(Post, post_id)


async def update_post(post_id: int, **kwargs) -> bool:
    """يعدل حقول المنشور (فقط الحقول المسموحة)."""
    allowed = {
        "button_text", "content", "url", "url_button_text",
        "is_active", "start_at", "end_at",
    }
    async with SessionLocal() as session:
        post = await session.get(Post, post_id)
        if not post:
            return False
        for key, value in kwargs.items():
            if key in allowed:
                setattr(post, key, value)
        await session.commit()
        return True


async def delete_post(post_id: int) -> bool:
    async with SessionLocal() as session:
        post = await session.get(Post, post_id)
        if not post:
            return False
        await session.delete(post)
        await session.commit()
        return True


async def toggle_post(post_id: int) -> Optional[bool]:
    """يوقف/يفعّل المنشور. يرجع الحالة الجديدة أو None لو لم يوجد."""
    async with SessionLocal() as session:
        post = await session.get(Post, post_id)
        if not post:
            return None
        post.is_active = not post.is_active
        await session.commit()
        return post.is_active
