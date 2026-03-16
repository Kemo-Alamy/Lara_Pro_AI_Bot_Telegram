import streamlit as st
import google.generativeai as genai
import os
from PIL import Image
import tempfile
import time

# --- إعدادات شكل الموقع ---
st.set_page_config(page_title="Gemini Pro - المساعد الجبار", page_icon="🤖", layout="wide")

st.markdown("""
    <h1 style='text-align: center; color: #2e6c80;'>🤖 موقع الذكاء الاصطناعي الشامل (Gemini 1.5 Pro)</h1>
    <p style='text-align: center;'>ارفع صور، فيديوهات، أو ملفات PDF واسأل أي سؤال.. حتى لو مسائل حسابية معقدة!</p>
""", unsafe_allow_html=True)

# --- إدخال مفتاح جوجل (API Key) ---
api_key = st.sidebar.text_input("AIzaSyA2rhT9nj08Yis3f_pkduDBt2KSWm1MxTY", type="password")
if api_key:
    genai.configure(api_key=api_key)

# --- قسم رفع الملفات ---
st.write("### 📂 ارفع ملفك هنا (صورة، PDF، أو فيديو mp4)")
uploaded_file = st.file_uploader("", type=['png', 'jpg', 'jpeg', 'pdf', 'mp4'])

# --- قسم كتابة السؤال ---
prompt = st.text_area("✍️ اكتب سؤالك أو المسألة الحسابية هنا:", height=150, placeholder="مثال: قم بحل هذه المسألة الرياضية الموجودة في الصورة واشرح الخطوات...")

# --- زر التشغيل والتحليل ---
if st.button("🚀 تحليل وحل"):
    if not api_key:
        st.error("⚠️ الرجاء إدخال مفتاح API في القائمة الجانبية أولاً.")
    elif not prompt and not uploaded_file:
        st.warning("⚠️ الرجاء كتابة سؤال أو رفع ملف.")
    else:
        # نستخدم أحدث وأقوى موديل من جوجل
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        with st.spinner('⏳ جاري فحص الملفات والتفكير في الحل... (الفيديوهات قد تستغرق وقتاً أطول)'):
            try:
                contents = [prompt] if prompt else[]

                # لو المستخدم رفع ملف
                if uploaded_file is not None:
                    file_extension = uploaded_file.name.split('.')[-1].lower()
                    
                    # 1. التعامل مع الصور
                    if file_extension in ['png', 'jpg', 'jpeg']:
                        image = Image.open(uploaded_file)
                        st.image(image, caption="الصورة المرفوعة", width=300)
                        contents.append(image)
                    
                    # 2. التعامل مع الـ PDF والفيديوهات (تحتاج رفع لخوادم جوجل مؤقتاً للتحليل)
                    else:
                        # حفظ الملف مؤقتاً
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
                            temp_file.write(uploaded_file.read())
                            temp_path = temp_file.name
                        
                        # رفع الملف لجوجل
                        gemini_file = genai.upload_file(path=temp_path)
                        
                        # لو الملف فيديو، جوجل بتحتاج ثواني لمعالجته
                        while gemini_file.state.name == 'PROCESSING':
                            time.sleep(2)
                            gemini_file = genai.get_file(gemini_file.name)
                            
                        contents.append(gemini_file)

                # إرسال الطلب لجوجل
                response = model.generate_content(contents)
                
                # عرض النتيجة
                st.success("✅ تم الحل!")
                st.write("### 💡 الإجابة:")
                st.markdown(response.text)

            except Exception as e:
                st.error(f"❌ حدث خطأ أثناء المعالجة: {e}")
