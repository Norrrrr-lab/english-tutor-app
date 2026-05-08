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

def clean_display_name(raw_name):
    cleaned = re.sub(r'\[.*?\]|\(.*?\)|\_내지|\_통합본|\_생략된 지문', '', raw_name)
    return cleaned.strip()

@st.cache_resource(show_spinner=False)
def load_permanent_pdfs_to_gemini():
    gemini_files_dict = {} 
    folder_path = "pdf_materials" 
    if os.path.exists(folder_path):
        for root, dirs, files in os.walk(folder_path):
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

# 🚨 골치 아팠던 book_config 삭제! 앱이 알아서 범용적으로 대응합니다.

st.set_page_config(page_title="English with Nora", page_icon="📚", layout="centered")
st.markdown("<h2 style='text-align: center;'>📚 English with Nora_Assistant system</h2><hr>", unsafe_allow_html=True)

if "user_db" not in st.session_state:
    st.session_state.user_db = {"nora": {"pw": "1234", "credits": 999}}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.current_student = ""

if not st.session_state.logged_in:
    tab_login, tab_signup, tab_find = st.tabs(["🔒 로그인", "📝 회원가입 (무료체험)", "🔍 ID/PW 찾기"])
    
    with tab_login:
        st.subheader("회원 로그인")
        input_id = st.text_input("아이디:")
        input_pw = st.text_input("비밀번호:", type="password")
        if st.button("로그인"):
            secret_pw = st.secrets.get(f"{input_id}_PW", None)
            if secret_pw and input_pw == secret_pw:
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
        st.write("아이디를 만들고 노라 쌤의 프리미엄 AI 튜터를 체험해 보세요!")
        new_id = st.text_input("사용할 아이디:")
        new_pw = st.text_input("사용할 비밀번호:", type="password")
        if st.button("가입하고 체험 시작하기"):
            if new_id in st.session_state.user_db or st.secrets.get(f"{new_id}_PW"):
                st.warning("이미 존재하는 아이디입니다.")
            elif new_id and new_pw:
                st.session_state.user_db[new_id] = {"pw": new_pw, "credits": 3}
                st.success("✅ 가입 완료! [로그인] 탭에서 로그인해 주세요. (무료 체험 3회 지급)")
            else:
                st.warning("아이디와 비밀번호를 모두 입력하세요.")
                
    with tab_find:
        st.info("비밀번호 분실 시 관리자(카카오톡 오픈채팅)에게 문의해 주세요.")
        payment_link = "https://toss.me/노라쌤결제링크"
        st.markdown(f"**체험이 끝났다면?** 👉 [월 7,000원 정기구독 신청하기]({payment_link})")
    
    st.stop()

with st.spinner("📚 자료 세팅 중... (최초 1회)"):
    permanent_pdf_files_dict = load_permanent_pdfs_to_gemini()

credits_left = st.session_state.user_db.get(st.session_state.current_student, {}).get("credits", "무제한")

col_logout1, col_logout2 = st.columns([8, 2])
with col_logout1:
    if credits_left != "무제한":
        st.success(f"환영합니다, {st.session_state.current_student} 님! 😊 (남은 무료 체험: {credits_left}회)")
    else:
        st.success(f"환영합니다, {st.session_state.current_student} 님! 😊 (정규 수강생)")
with col_logout2:
    if st.button("로그아웃"):
        st.session_state.logged_in = False
        st.rerun()
st.divider()

pdf_options = {}
pdf_display_mapping = {}

if os.path.exists("pdf_materials"):
    for root, dirs, files in os.walk("pdf_materials"):
        rel_path = os.path.relpath(root, "pdf_materials")
        category_name = "미분류 자료" if rel_path == "." else rel_path.replace("\\", "/")
        pdf_files = [f.replace('.pdf', '') for f in files if f.endswith(".pdf")]
        if pdf_files:
            pdf_options[category_name] = pdf_files
            for f in pdf_files:
                pdf_display_mapping[clean_display_name(f)] = f

st.subheader("🔍 1. 분석할 지문 불러오기")

if pdf_options:
    selected_category = st.selectbox("1) 출판사/분류 선택", list(pdf_options.keys()))
    raw_books = pdf_options[selected_category]
    display_books = [clean_display_name(b) for b in raw_books]
    selected_display_book = st.selectbox("2) 교재명 선택", display_books)
    selected_book = pdf_display_mapping[selected_display_book]
    
    # --- 🚨 [NEW] 유지보수 0%의 하이브리드 드롭다운 ---
    col_unit, col_q = st.columns(2)
    with col_unit:
        unit_list = [f"{i}강 (Unit {i})" for i in range(1, 31)] + ["Test/모의고사", "기타", "직접 입력 (타이핑)"]
        selected_unit = st.selectbox("3) 단원 선택", ["선택하세요"] + unit_list)
        
        # '직접 입력'을 고르면 타자 치는 칸이 마법처럼 나타남!
        final_unit = selected_unit
        if selected_unit == "직접 입력 (타이핑)":
            final_unit = st.text_input("단원을 직접 적어주세요 (예: Mini Test 1)")

    with col_q:
        q_list = [f"{i}번" for i in range(1, 21)] + ["전체 지문", "직접 입력 (타이핑)"]
        selected_q = st.selectbox("4) 지문 번호 선택", ["선택하세요"] + q_list)
        
        final_q = selected_q
        if selected_q == "직접 입력 (타이핑)":
            final_q = st.text_input("지문 번호를 직접 적어주세요 (예: Reading 1)")
    
    textbook_unit = f"{final_unit} {final_q}"
    
    if "extracted_text" not in st.session_state:
        st.session_state.extracted_text = ""

    if st.button("✅ 선택한 지문 텍스트 확인하기"):
        if selected_unit == "선택하세요" or selected_q == "선택하세요":
            st.warning("단원과 번호를 모두 선택해주세요!")
        elif selected_unit == "직접 입력 (타이핑)" and not final_unit.strip():
             st.warning("단원을 직접 입력해주세요!")
        else:
            with st.spinner("PDF에서 지문을 읽어오는 중입니다..."):
                try:
                    extract_prompt = f"'{textbook_unit}'에 해당하는 영어 지문 원문(Text)만 정확히 추출해. 해설 제외."
                    if selected_book in permanent_pdf_files_dict:
                        target_pdf = permanent_pdf_files_dict[selected_book]
                        response = model.generate_content([extract_prompt, target_pdf])
                        st.session_state.extracted_text = response.text
                        st.rerun()
                except Exception as e:
                    st.error("지문을 불러오는 데 실패했습니다.")
else:
    st.info("등록된 교재가 없습니다.")

if st.session_state.get("extracted_text"):
    st.success("✨ 지문 로딩 완료!")
    with st.expander("📖 불러온 지문 확인하기", expanded=True):
        st.write(st.session_state.extracted_text)
    
    st.divider()
    
    st.subheader("💡 2. 학습 모드 및 질문 입력")
    mode = st.radio("원하는 분석 모드를 선택하세요:", [
        "1. 구문 분석 + 초급 동음이의어/다의어 정리", 
        "2. 주요 문장 2개 + 중상급 유반의어 정리", 
        "3. 전체 줄거리 구조화 (도식/요약)",
        "4. 💬 조교에게 직접 질문하기 (하소연 및 자유 질문)"
    ])

    user_question = ""
