import streamlit as st
import google.generativeai as genai
import os
import re

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

valid_model_name = 'gemini-2.5-flash'
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            if 'flash' in m.name:
                valid_model_name = m.name.replace("models/", "")
                break
except Exception:
    pass

model = genai.GenerativeModel(valid_model_name)

# --- 저작권 보호를 위한 교재명 세탁기 ---
def clean_display_name(raw_name):
    blacklist = ['이그잼포유', 'exam4you', '아잉카', '리카수니', '황인영', '기출비', '족보닷컴', '나무아카데미']
    cleaned = raw_name
    for word in blacklist:
        cleaned = re.sub(word, '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\[.*?\]|\(.*?\)|\_내지|\_통합본|\_생략된 지문|\_분석노트|\_정답', '', cleaned)
    return cleaned.strip()

@st.cache_resource(show_spinner=False)
def load_permanent_pdfs_to_gemini():
    gemini_files_dict = {} 
    folder_path = "pdf_materials" 
    if os.path.exists(folder_path):
        for root, dirs, files in os.walk(folder_path):
            files.sort(reverse=True) 
            for filename in files:
                if filename.endswith(".pdf"):
                    file_path = os.path.join(root, filename)
                    try:
                        uploaded_file = genai.upload_file(file_path)
                        book_key = filename.replace('.pdf', '')
                        gemini_files_dict[book_key] = uploaded_file
                    except Exception as e:
                        pass
    return gemini_files_dict

# --- 🚨 [교재별 실제 단원/번호 매핑 사전] ---
book_custom_settings = {
    "올림포스 영어독해의 기본1": {"u_label": "강", "u_max": 18, "q_label": "번", "q_max": 12},
    "올림포스 영어독해의 기본2": {"u_label": "강", "u_max": 18, "q_label": "번", "q_max": 10},
    "올림포스 영어독해의 기본2_내지": {"u_label": "강", "u_max": 18, "q_label": "번", "q_max": 10},
    "올림포스 9대 변형유형": {"u_label": "Unit", "u_max": 10, "q_label": "번", "q_max": 8},
    "수능특강light 영어독해연습": {"u_label": "강", "u_max": 12, "q_label": "번", "q_max": 12},
    "기본값": {"u_label": "Unit", "u_max": 25, "q_label": "번", "q_max": 15}
}

# --- 🚨 타이틀 명칭 전면 개편 완료 ---
st.set_page_config(page_title="English with Nora_혼자서도 할 수 있다! 중/고등학생 내신대비 자습실", page_icon="📚", layout="centered")
st.markdown("<h2 style='text-align: center;'>📚 English with Nora_혼자서도 할 수 있다!<br>중/고등학생 내신대비 자습실</h2><hr>", unsafe_allow_html=True)

# 블로그 체험자용 임시 보관소 (정규 수강생은 Secrets 금고에서 판독)
if "user_db" not in st.session_state:
    st.session_state.user_db = {}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.current_student = ""

# 로그인 시스템
if not st.session_state.logged_in:
    tab_login, tab_signup, tab_find = st.tabs(["🔒 로그인", "📝 회원가입 (무료체험)", "🔍 ID/PW 찾기"])
    
    with tab_login:
        st.subheader("회원 로그인")
        input_id = st.text_input("아이디:")
        input_pw = st.text_input("비밀번호:", type="password")
        if st.button("로그인"):
            secret_pw = st.secrets.get(f"{input_id}_PW", None)
            if secret_pw and str(input_pw) == str(secret_pw):
                st.session_state.logged_in = True
                st.session_state.current_student = input_id
                st.rerun()
            elif input_id in st.session_state.user_db and st.session_state.user_db[input_id]["pw"] == input_pw:
                st.session_state.logged_in = True
                st.session_state.current_student = input_id
                st.rerun()
            else:
                st.error("아이디나 비밀번호가 틀렸습니다.")
                
    with tab_signup:
        st.subheader("🚀 3회 무료 체험하기")
        new_id = st.text_input("사용할 아이디:")
        new_pw = st.text_input("사용할 비밀번호:", type="password")
        if st.button("가입하고 체험 시작하기"):
            if new_id in st.session_state.user_db or st.secrets.get(f"{new_id}_PW"):
                st.warning("이미 존재하는 아이디
