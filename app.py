import streamlit as st
import google.generativeai as genai
from PIL import Image
import os
import pandas as pd
import re # 글자 청소를 위한 마법 부품

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

# --- 1. 파일 이름 깔끔하게 청소하는 함수 ---
def clean_display_name(raw_name):
    # [어쩌구], (어쩌구), _어쩌구 같은 불필요한 교사용 꼬리표를 싹 지웁니다.
    cleaned = re.sub(r'\[.*?\]|\(.*?\)|\_내지|\_통합본|\_생략된 지문', '', raw_name)
    # 지우고 남은 앞뒤 공백 제거
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

st.set_page_config(page_title="English with Nora", page_icon="📚", layout="centered")
st.markdown("<h2 style='text-align: center;'>📚 English with Nora_Assistant system</h2><hr>", unsafe_allow_html=True)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.current_student = ""

# --- 2. 로그인 및 유료 결제 유도 화면 ---
if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["🔒 수강생 & 구독자 로그인", "💳 일반 학생 이용권 구매"])
    
    with tab1:
        st.subheader("회원 로그인")
        input_id = st.text_input("아이디:")
        input_pw = st.text_input("비밀번호:", type="password")

        if st.button("로그인"):
            expected_pw = st.secrets.get(f"{input_id}_PW", None)
            if expected_pw and input_pw == expected_pw:
                st.session_state.logged_in = True
                st.session_state.current_student = input_id
                st.rerun()
            else:
                st.error("정보가 틀렸습니다. 구독자라면 관리자에게 문의하세요.")
                
    with tab2:
        st.subheader("🚀 노라 쌤의 프리미엄 AI 튜터 구독")
        st.markdown("""
        **현재 수강생이 아니신가요?**
        월 7,000원으로 수능/내신 영어를 완벽하게 뜯어먹을 수 있는 AI 튜터 이용권을 구매해 보세요!
        
        * 📚 수많은 부교재 완벽 분석
        * 💬 무제한 질의응답 및 구문 분석
        * 🎯 1타 강사의 로직이 담긴 핵심 풀이
        """)
        
        # 🚨 여기에 쌤의 토스 익명 송금 링크나 카카오 오픈프로필 링크를 넣으세요!
        payment_link = "https://toss.me/노라쌤결제링크" # 이 부분을 실제 링크로 수정!
        st.link_button("👉 월 7,000원 결제하고 계정 발급받기", payment_link)
        st.caption("결제 후 송금 화면을 캡처하여 오픈채팅으로 보내주시면 즉시 전용 ID/PW를 발급해 드립니다.")
        
    st.stop()

with st.spinner("📚 자료 세팅 중... (최초 1회)"):
    permanent_pdf_files_dict = load_permanent_pdfs_to_gemini()

col_logout1, col_logout2 = st.columns([8, 2])
with col_logout1:
    st.success(f"환영합니다, {st.session_state.current_student} 님! 😊")
with col_logout2:
    if st.button("로그아웃"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
st.divider()

# 폴더 인식 및 딕셔너리 생성
pdf_options = {}
pdf_display_mapping = {} # 화면에 예쁘게 보일 이름 -> 진짜 파일 이름 매핑 상자

if os.path.exists("pdf_materials"):
    for root, dirs, files in os.walk("pdf_materials"):
        rel_path = os.path.relpath(root, "pdf_materials")
        category_name = "미분류 자료" if rel_path == "." else rel_path.replace("\\", "/")
        
        pdf_files = [f.replace('.pdf', '') for f in files if f.endswith(".pdf")]
        if pdf_files:
            pdf_options[category_name] = pdf_files
            for f in pdf_files:
                pdf_display_mapping[clean_display_name(f)] = f # 예쁜이름:진짜이름 저장

# --- 3. 드롭다운으로 변경된 지문 선택기 ---
st.subheader("🔍 1. 분석할 지문 불러오기")

if pdf_options:
    selected_category = st.selectbox("1) 출판사/분류 선택", list(pdf_options.keys()))
    
    # 해당 카테고리의 진짜 파일 이름들을 예쁜 이름으로 바꿔서 드롭다운에 표시
    raw_books = pdf_options[selected_category]
    display_books = [clean_display_name(b) for b in raw_books]
    selected_display_book = st.selectbox("2) 교재명 선택", display_books)
    
    # 쌤이 고른 예쁜 이름을 다시 진짜 파일 이름으로 번역
    selected_book = pdf_display_mapping[selected_display_book]
    
    # --- [수정됨] 단원/번호 드롭다운 생성 ---
    col_unit, col_q = st.columns(2)
    with col_unit:
        unit_list = [f"{i}강 (Unit {i})" for i in range(1, 31)] + ["Test/모의고사", "기타"]
        selected_unit = st.selectbox("3) 단원 선택", ["선택하세요"] + unit_list)
    with col_q:
        q_list = [f"{i}번" for i in range(1, 21)] + ["전체 지문"]
        selected_q = st.selectbox("4) 지문 번호 선택", ["선택하세요"] + q_list)
    
    # 선택값을 하나로 합침 (예: "3강 (Unit 3) 2번")
    textbook_unit = f"{selected_unit} {selected_q}"
    
    if "extracted_text" not in st.session_state:
        st.session_state.extracted_text = ""

    if st.button("✅ 선택한 지문 텍스트 확인하기"):
        if selected_unit == "선택하세요" or selected_q == "선택하세요":
            st.warning("단원과 번호를 모두 선택해주세요!")
        else:
            with st.spinner("PDF에서 해당 지문을 눈으로 읽어오는 중입니다... (약 5초 소요)"):
                try:
                    extract_prompt = f"당신이 가지고 있는 PDF 자료에서 '{textbook_unit}'에 해당하는 영어 지문 원문(Text)만 정확히 추출해서 보여주세요. 해설이나 인사말은 빼고 지문 내용만 출력하세요."
                    
                    if selected_book in permanent_pdf_files_dict:
                        target_pdf = permanent_pdf_files_dict[selected_book]
                        response = model.generate_content([extract_prompt, target_pdf])
                        
                        st.session_state.extracted_text = response.text
                        st.rerun()
                except Exception as e:
                    st.error("지문을 불러오는 데 실패했습니다. 범위를 다시 확인해주세요.")
else:
    st.info("등록된 교재가 없습니다.")

if st.session_state.get("extracted_text"):
    st.success("✨ 지문 로딩 완료!")
    with st.expander("📖 불러온 지문 확인하기", expanded=True):
        st.write(st.session_state.extracted_text)
    
    st.divider()
    st.subheader("💡 2. 학습 모드 선택")
    mode = st.radio("원하는 분석 모드를 선택하세요:", [
        "1. 구문 분석 + 초급 동음이의어/다의어 정리", 
        "2. 주요 문장 2개 + 중상급 유반의어 정리", 
        "3. 전체 줄거리 구조화 (도식/요약)"
    ])

    st.divider()
    st.subheader("💬 3. 조교에게 질문하기")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_question = st.chat_input("위 지문에 대해 궁금한 점을 입력하세요!")

    if user_question:
        st.chat_message("user").markdown(user_question)
        st.session_state.messages.append({"role": "user", "content": user_question})

        base_instruction = f"""
        당신은 친절한 영어 조교입니다. 학생이 아래의 [영어 지문]에 대해 질문했습니다.
        반드시 제공된 [영어 지문] 내용만을 바탕으로 대답하세요.
        
        [영어 지문]:
        {st.session_state.extracted_text}
        """

        if "1. 구문" in mode:
            system_prompt = base_instruction + f"\n[지시사항]: 지문을 바탕으로 1. 문법/구문 분석 2. 다의어 설명을 작성하세요. \n[질문]: {user_question}"
        elif "2. 주요" in mode:
            system_prompt = base_instruction + f"\n[지시사항]: 지문을 바탕으로 1. 핵심 문장 해석 2. 유반의어 표를 작성하세요. \n[질문]: {user_question}"
        else:
            system_prompt = base_instruction + f"\n[지시사항]: 지문을 바탕으로 1. 논리 구조도 2. 핵심 키워드를 정리하세요. \n[질문]: {user_question}"

        with st.chat_message("assistant"):
            with st.spinner("답변을 준비 중입니다..."):
                try:
                    response = model.generate_content(system_prompt)
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error("답변 생성 중 오류가 발생했습니다.")
