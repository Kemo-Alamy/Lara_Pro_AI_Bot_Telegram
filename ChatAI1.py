
import logging
import os
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputFile
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import google.generativeai as genai
from gtts import gTTS
import speech_recognition as sr

# ================== CONFIG ==================
TELEGRAM_TOKEN = "7961354788:AAFweQqLPAGPMzLlSKf1MZOstkIXCnupV18"
GEMINI_API_KEY = "AIzaSyA2rhT9nj08Yis3f_pkduDBt2KSWm1MxTY"
FORCE_CHANNEL = "@Kemo_ALamy_23 , @Kemo_Alamy"
ADMIN_ID = 6520549428
MAX_MEMORY = 200
# ============================================

logging.basicConfig(level=logging.INFO)

# ============ Gemini ============
genai.configure(api_key=GEMINI_API_KEY)
text_model = genai.GenerativeModel("models/gemini-1.5-flash")
vision_model = genai.GenerativeModel("models/gemini-1.5-flash")

# ============ Runtime Memory ============
users = set()
banned = set()
admins = {ADMIN_ID}
chats = {}

# ============ Keyboards ============
def sub_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأكيد الاشتراك", callback_data="check_sub")]
    ])

def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎓 تعليمي", callback_data="edu"),
            InlineKeyboardButton("🩺 طبي", callback_data="medical")
        ],
        [
            InlineKeyboardButton("🎤 رد صوتي", callback_data="voice_on"),
            InlineKeyboardButton("📝 رد نصي", callback_data="voice_off")
        ]
    ])

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 عدد المستخدمين", callback_data="count")],
        [InlineKeyboardButton("📢 رسالة جماعية", callback_data="broadcast")],
        [InlineKeyboardButton("🚫 حظر", callback_data="ban"),
         InlineKeyboardButton("✅ فك حظر", callback_data="unban")]
    ])

# ============ /start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if u.id in banned:
        return
    users.add(u.id)
    context.user_data["voice_reply"] = False
    await update.message.reply_text(
        "👋 أهلاً بك في **Lara V1** 🤖\n"
        "ذكاء اصطناعي عربي ذكي\n\n"
        "🔒 اشترك في القناة ثم أكد الاشتراك",
        reply_markup=sub_keyboard(),
        parse_mode="Markdown"
    )

# ============ Callbacks ============
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data == "check_sub":
        try:
            member = await context.bot.get_chat_member(FORCE_CHANNEL, uid)
            if member.status in ("member", "administrator", "creator"):
                await q.message.reply_text(
                    "✅ تم التحقق بنجاح\n"
                    "اختر وضعك 👇",
                    reply_markup=main_keyboard()
                )
            else:
                await q.message.reply_text("❌ اشترك في القناة أولاً")
        except:
            await q.message.reply_text("⚠️ خطأ في التحقق")

    if q.data == "edu":
        context.user_data["mode"] = "edu"
        await q.message.reply_text("🎓 تم تفعيل الوضع التعليمي")

    elif q.data == "medical":
        context.user_data["mode"] = "medical"
        await q.message.reply_text("🩺 تم تفعيل الوضع الطبي")

    elif q.data == "voice_on":
        context.user_data["voice_reply"] = True
        await q.message.reply_text("🎤 سيتم الرد بالصوت")

    elif q.data == "voice_off":
        context.user_data["voice_reply"] = False
        await q.message.reply_text("📝 سيتم الرد بالنص")

    # ===== أدمن =====
    if uid not in admins:
        return

    if q.data == "count":
        await q.message.reply_text(f"👥 المستخدمين: {len(users)}")

    elif q.data == "broadcast":
        context.user_data["broadcast"] = True
        await q.message.reply_text("✍️ اكتب الرسالة")

    elif q.data == "ban":
        context.user_data["ban"] = True
        await q.message.reply_text("🚫 ابعت ID")

    elif q.data == "unban":
        context.user_data["unban"] = True
        await q.message.reply_text("✅ ابعت ID")

# ============ Admin Input ============
async def admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    if uid not in admins:
        return

    if context.user_data.get("broadcast"):
        for u in users:
            try:
                await context.bot.send_message(u, text)
            except:
                pass
        context.user_data.clear()
        await update.message.reply_text("✅ تم الإرسال")

    elif context.user_data.get("ban"):
        banned.add(int(text))
        context.user_data.clear()
        await update.message.reply_text("🚫 تم الحظر")

    elif context.user_data.get("unban"):
        banned.discard(int(text))
        context.user_data.clear()
        await update.message.reply_text("✅ تم فك الحظر")

# ============ تحليل الصور ============
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = await update.message.photo[-1].get_file()
    image_path = "image.jpg"
    await photo.download_to_drive(image_path)

    response = vision_model.generate_content(
        ["اشرح الصورة بالتفصيل بالعربية", open(image_path, "rb")]
    )
    await update.message.reply_text(response.text)

# ============ الصوت → نص ============
async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = await update.message.voice.get_file()
    voice_path = "voice.ogg"
    await voice.download_to_drive(voice_path)

    r = sr.Recognizer()
    with sr.AudioFile(voice_path) as source:
        audio = r.record(source)
        text = r.recognize_google(audio, language="ar-EG")

    await update.message.reply_text(f"📝 تم تحويل الصوت:\n{text}")

# ============ الرد ============
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in banned:
        return

    chats.setdefault(uid, []).append(update.message.text)
    chats[uid] = chats[uid][-MAX_MEMORY:]

    mode = context.user_data.get("mode", "normal")
    prompt = "أجب بالعربية فقط.\n"
    if mode == "edu":
        prompt += "اشرح كمعلم.\n"
    elif mode == "medical":
        prompt += "معلومات طبية عامة بدون تشخيص.\n"

    prompt += "\n".join(chats[uid])

    response = text_model.generate_content(prompt)
    reply = response.text

    if context.user_data.get("voice_reply"):
        tts = gTTS(reply, lang="ar")
        tts.save("reply.mp3")
        await update.message.reply_voice(voice=open("reply.mp3", "rb"))
    else:
        await update.message.reply_text(reply)

# ============ Main ============
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler(
        "admin",
        lambda u, c: u.message.reply_text("👑 لوحة الأدمن", reply_markup=admin_keyboard())
        if u.effective_user.id in admins else None
    ))

    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(lambda u: u.id in admins), admin_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    app.run_polling()

if __name__ == "__main__":
    main()