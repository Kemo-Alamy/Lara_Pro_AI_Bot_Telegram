import telebot
import google.generativeai as genai
from PIL import Image
from gtts import gTTS
import io
import os
import json
import re

# ================= الإعدادات =================
GEMINI_API_KEY = "AIzaSyDK74lrKLfyrErqJ1tM0ByRSKBYV39OCTs"
TELEGRAM_BOT_TOKEN = "7961354788:AAFweQqLPAGPMzLlSKf1MZOstkIXCnupV18" 
ADMIN_ID = 6520549428  # استبدله برقمك الـ ID

genai.configure(api_key=GEMINI_API_KEY)
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_FILE = os.path.join(BASE_DIR, "lara_admin_rules.txt")
DATABASE_FILE = os.path.join(BASE_DIR, "users_history.json")

# ================= تحميل الذاكرة =================
users_database = {}
if os.path.exists(DATABASE_FILE):
    try:
        with open(DATABASE_FILE, "r", encoding="utf-8") as f:
            users_database = json.load(f)
    except json.JSONDecodeError:
        users_database = {}

active_chats = {}

def save_database():
    with open(DATABASE_FILE, "w", encoding="utf-8") as f:
        json.dump(users_database, f, ensure_ascii=False, indent=4)

def get_admin_rules():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "لا توجد قواعد إضافية."

def get_model():
    base_instructions = """
    أنتِ مساعدة ذكية متطورة جداً اسمك 'لارا' (Lara).
    لديك ذاكرة قوية جداً. اربطي سياق الكلام ببعضه.
    إذا كان المتحدث هو 'المدير'، كوني في قمة الطاعة.
    تحدثي دائماً بأسلوب طبيعي ومريح.
    """
    full_instructions = base_instructions + f"\n\n--- قواعد المدير ---\n{get_admin_rules()}"
    return genai.GenerativeModel(model_name="gemini-1.5-pro", system_instruction=full_instructions)

model = get_model()

def get_user_chat(user_id):
    user_id_str = str(user_id)
    if user_id_str in active_chats:
        return active_chats[user_id_str]
    
    history = []
    if user_id_str in users_database:
        for msg in users_database[user_id_str][-30:]:
            history.append({"role": msg["role"], "parts": [msg["parts"]]})
            
    chat_session = model.start_chat(history=history)
    active_chats[user_id_str] = chat_session
    return chat_session

def update_user_history(user_id, user_text, bot_response):
    user_id_str = str(user_id)
    if user_id_str not in users_database:
        users_database[user_id_str] = []
    users_database[user_id_str].append({"role": "user", "parts": user_text})
    users_database[user_id_str].append({"role": "model", "parts": bot_response})
    save_database()

# ================= أدوات الصوت =================
def clean_text_for_speech(text):
    """تنظيف النص من النجوم والرموز لكي ينطقها الصوت بشكل طبيعي"""
    text = re.sub(r'\*|\#|\_|\-', '', text)
    return text

def send_voice_message(chat_id, text):
    """دالة لتحويل النص إلى صوت وإرساله للمستخدم"""
    try:
        clean_text = clean_text_for_speech(text)
        tts = gTTS(text=clean_text, lang='ar', slow=False) # lang='ar' للتحدث بالعربية
        audio_file = os.path.join(BASE_DIR, f"reply_{chat_id}.ogg")
        tts.save(audio_file)
        
        with open(audio_file, 'rb') as voice:
            bot.send_voice(chat_id, voice)
            
        os.remove(audio_file) # حذف الملف بعد الإرسال لتوفير المساحة
    except Exception as e:
        print(f"Error in TTS: {e}")

# ================= أوامر المدير =================
@bot.message_handler(commands=['train'])
def train_lara(message):
    if message.from_user.id != ADMIN_ID: return
    new_rule = message.text.replace('/train', '').strip()
    if not new_rule: return
    with open(MEMORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"- {new_rule}\n")
    global model
    model = get_model()
    active_chats.clear() 
    bot.reply_to(message, "تم حفظ التدريب يا سيدي!")

def format_prompt(message, user_text):
    if message.from_user.id == ADMIN_ID:
        return f"[المدير يقول]: {user_text}"
    return f"[{message.from_user.first_name} يقول]: {user_text}"

# ================= معالجة الرسائل الصوتية (الجديد) =================
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    bot.send_chat_action(message.chat.id, 'record_audio') # يظهر للمستخدم أن البوت يسجل صوتاً
    try:
        user_id = message.from_user.id
        
        # 1. تحميل المقطع الصوتي من تليجرام
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        audio_file_path = os.path.join(BASE_DIR, f"user_voice_{user_id}.ogg")
        with open(audio_file_path, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        # 2. رفع المقطع الصوتي لجوجل جيميناي ليسمعه
        gemini_audio = genai.upload_file(path=audio_file_path, mime_type="audio/ogg")
        
        # 3. إرسال الصوت في سياق المحادثة
        final_prompt = format_prompt(message, "استمعي إلى هذه الرسالة الصوتية وردي عليها بشكل طبيعي.")
        chat = get_user_chat(user_id)
        response = chat.send_message([final_prompt, gemini_audio])
        
        # 4. الرد بالنص أولاً
        bot.reply_to(message, response.text)
        
        # 5. الرد بالصوت (لارا تتحدث)
        bot.send_chat_action(message.chat.id, 'record_audio')
        send_voice_message(message.chat.id, response.text)
        
        # 6. تحديث الذاكرة وحذف الملفات المؤقتة
        update_user_history(user_id, final_prompt + " [أرسل رسالة صوتية]", response.text)
        genai.delete_file(gemini_audio.name)
        os.remove(audio_file_path)
        
    except Exception as e:
        bot.reply_to(message, f"عذراً يا سيدي، لم أتمكن من سماع الصوت بوضوح: {e}")

# ================= معالجة النصوص =================
@bot.message_handler(content_types=['text'])
def handle_text(message):
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        user_id = message.from_user.id
        final_prompt = format_prompt(message, message.text)
        chat = get_user_chat(user_id)
        response = chat.send_message(final_prompt)
        bot.reply_to(message, response.text)
        update_user_history(user_id, final_prompt, response.text)
    except Exception as e:
        pass

# ================= معالجة الصور =================
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.reply_to(message, "جاري الفحص...")
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        user_id = message.from_user.id
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        image = Image.open(io.BytesIO(downloaded_file))
        user_caption = message.caption if message.caption else "اشرحي الصورة."
        final_prompt = format_prompt(message, user_caption)
        chat = get_user_chat(user_id)
        response = chat.send_message([final_prompt, image])
        bot.reply_to(message, response.text)
        update_user_history(user_id, final_prompt + " [أرسل صورة]", response.text)
    except Exception:
        pass

# ================= معالجة الـ PDF =================
@bot.message_handler(content_types=['document'])
def handle_document(message):
    if message.document.mime_type != 'application/pdf': return
    bot.reply_to(message, "جاري التحليل...")
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        user_id = message.from_user.id
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_name = os.path.join(BASE_DIR, message.document.file_name)
        with open(file_name, 'wb') as new_file:
            new_file.write(downloaded_file)
        gemini_file = genai.upload_file(path=file_name, display_name=message.document.file_name)
        user_caption = message.caption if message.caption else "لخصي المستند."
        final_prompt = format_prompt(message, user_caption)
        chat = get_user_chat(user_id)
        response = chat.send_message([final_prompt, gemini_file])
        bot.reply_to(message, response.text)
        update_user_history(user_id, final_prompt + " [أرسل PDF]", response.text)
        genai.delete_file(gemini_file.name)
        os.remove(file_name)
    except Exception:
        pass

print("لارا تعمل الآن (تدعم الصوتيات والاستماع)...")
bot.infinity_polling(timeout=10, long_polling_timeout=5)