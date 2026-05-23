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

# --- 🚨 저작권 보호 및 중복 방지용 이름 세탁기 ---
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
            # 분석노트 등 핵심 자료가 먼저 덮어써지도록 정렬
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

# --- 🚨 [NEW] 교재별 단원 및 번호 맞춤 설정 ---
# 여기에 쌤이 쓰시는 책의 특성을 적어두면 드롭다운이 알아서 변합니다!
book_custom_settings = {
    "2025 올림포스 영어독해의 기본2": {"u_label": "강", "u_max": 18, "q_label": "번", "q_max": 10},
    "2026 올림포스 9대 변유형": {"u_label": "Unit", "u_max": 10, "q_label": "번", "q_max": 8},
    "수능특강light 영어독해연습": {"u_label": "강", "u_max": 12, "q_label": "번", "q_max": 12},
    "수능특강 영어": {"u_label": "강", "u_max": 33, "q_label": "번", "q_max": 28},
    "모의고사": {"q_label": "번","q_min": 18, "q_max": 45},
    # 설정에 없는 책이 선택되면 아래 '기본값'이 적용됩니다.
    "기본값": {"u_label": "Unit", "u_max": 20, "q_label": "번", "q_max": 30}
}

# 1. 페이지 세팅
st.set_page_config(page_title="English with Nora_혼자서도 할 수 있다! 중/고등학생 내신대비 자습실", page_icon="📚", layout="centered")
st.markdown("<h2 style='text-align: center;'>📚 English with Nora_혼자서도 할 수 있다!<br>중/고등학생 내신대비 자습실</h2><hr>", unsafe_allow_html=True)

# 2. 신규 학생 DB 추가
if "user_db" not in st.session_state:
    st.session_state.user_db = {
        "nora": {"pw": "1234", "credits": 999},
        "오찬희": {"pw": "1234", "credits": 999},
        "이은수": {"pw": "1234", "credits": 999},
        "최창민": {"pw": "1234", "credits": 999}
    }

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.current_student = ""

# 3. 로그인 및 결제
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
        new_id = st.text_input("사용할 아이디:")
        new_pw = st.text_input("사용할 비밀번호:", type="password")
        if st.button("가입하고 체험 시작하기"):
            if new_id in st.session_state.user_db or st.secrets.get(f"{new_id}_PW"):
                st.warning("이미 존재하는 아이디입니다.")
            elif new_id and new_pw:
                st.session_state.user_db[new_id] = {"pw": new_pw, "credits": 3}
                st.success("✅ 가입 완료! [로그인] 탭에서 로그인해 주세요.")
            else:
                st.warning("정보를 모두 입력하세요.")
                
    with tab_find:
        payment_link = "https://toss.me/노라쌤결제링크"
        st.markdown(f"**체험이 끝났다면?** 👉 [월 3,000원 정기구독 신청하기]({payment_link})")
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
            pdf_options[category_name] = []
            for f in pdf_files:
                clean_name = clean_display_name(f)
                # 중복 제거 로직: 화면에는 딱 하나만 뜨도록 처리
                if clean_name not in pdf_options[category_name]:
                    pdf_options[category_name].append(clean_name)
                    pdf_display_mapping[clean_name] = f 

st.subheader("🔍 1. 분석할 지문 불러오기")

if pdf_options:
    selected_category = st.selectbox("1) 출판사/분류 선택", list(pdf_options.keys()))
    display_books = pdf_options[selected_category]
    selected_display_book = st.selectbox("2) 교재명 선택", display_books)
    selected_book = pdf_display_mapping[selected_display_book]
    
    # --- 🚨 [NEW] 교재 맞춤형 단원/번호 자동 생성 로직 ---
    book_setting = book_custom_settings.get(selected_display_book, book_custom_settings["기본값"])
    
    col_unit, col_q = st.columns(2)
    with col_unit:
        unit_list = [f"{i}{book_setting['u_label']}" for i in range(1, book_setting['u_max'] + 1)] + ["Test/모의고사", "직접 입력 (타이핑)"]
        selected_unit = st.selectbox(f"3) 단원 ({book_setting['u_label']}) 선택", ["선택하세요"] + unit_list)
        
        final_unit = selected_unit
        if selected_unit == "직접 입력 (타이핑)":
            final_unit = st.text_input("단원을 직접 적어주세요 (예: Mini Test 1)")

    with col_q:
        q_list = [f"{i}{book_setting['q_label']}" for i in range(1, book_setting['q_max'] + 1)] + ["전체 지문", "직접 입력 (타이핑)"]
        selected_q = st.selectbox(f"4) 지문 번호 ({book_setting['q_label']}) 선택", ["선택하세요"] + q_list)
        
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
        "1. 구문 분석 + 초급 다의어 설명", 
        "2. 주요 지문 2개 분석 + 중상급 유반의어 정리", 
        "3. 전체 줄거리 시각화 구조도",
        "4. 💬 조교에게 직접 질문하기 (하소연 및 자유 질문)"
    ])

    user_question = ""
    if "4." in mode:
        user_question = st.text_input("궁금한 점이나 하소연을 자유롭게 적어주세요!")

    if st.button("🚀 분석 실행 (확인)"):
        if "4." in mode and not user_question.strip():
            st.warning("질문 내용을 입력해 주세요!")
        else:
            if credits_left != "무제한":
                if st.session_state.user_db[st.session_state.current_student]["credits"] <= 0:
                    st.error("🚨 무료 체험 횟수를 모두 소진했습니다. 월 3,000원 이용권 결제가 필요합니다!")
                    st.stop()
                else:
                    st.session_state.user_db[st.session_state.current_student]["credits"] -= 1

            # --- 🚨 [NEW] 시각적/디자인적 분석 프롬프트 세팅 ---
            base_instruction = f"""
            당신은 친절한 영어 1타 강사 조교입니다. 제공된 [영어 지문] 내용만을 바탕으로 답변하세요.
            [영어 지문]:
            {st.session_state.extracted_text}
            """

            if "1. 구문" in mode:
                system_prompt = base_instruction + """
                [명령]
                1. 학생이 전체 지문을 한 줄 씩 읽을 수 있도록 번역을 제공하되, 반드시 HTML 색상 태그를 사용하여 문장 성분을 시각적으로 쪼개서 분석하세요. 절대 줄글로 길게 쓰지 마세요.
                * 예시 규칙: <font color='blue'>주어(S)</font>, <font color='red'>동사(V)</font>, <font color='green'>목적어/보어(O/C)</font>, <font color='gray'>수식어(M)</font>
                2. 지문 내의 핵심 기초 단어를 3개 선정하여 '초급 다의어(다양한 의미)'를 쉽게 설명해 주세요.
                """
            elif "2. 주요" in mode:
                system_prompt = base_instruction + """
                [명령]
                1. 전체 지문의 한 줄 해석은 생략하세요. 대신, 지문에서 딱 2개의 문장만 꼽아서 분석하세요.
                   - 문장 A: 줄거리와 주제를 관통하는 핵심 문장
                   - 문장 B: 문법적으로 가장 복잡하고 어려운 구문
                2. 이 2개의 문장은 절대 줄글로 설명하지 말고, 시중 고급 분석지처럼 HTML 색상 태그(<font color='blue'>S</font>, <font color='red'>V</font> 등)를 떡칠하여 성분을 시각적으로 명확하게 뜯어주세요.
                3. 지문의 핵심 단어 3개를 뽑고, 미국 Merriam-Webster 사전 기준 가장 연관성이 높은(가장 진하게 표시되는) '중상급 수준'의 동의어(Synonyms)와 반의어(Antonyms)를 표로 정리해 주세요.
                """
            elif "3. 전체" in mode:
                system_prompt = base_instruction + """
                [명령]
                1. 줄글 요약은 금지합니다. Canva나 인포그래픽 포스터를 보듯, 마크다운의 표, 인용구(>), 이모지를 적극 활용하여 지문의 전체 흐름을 '시각적 구조도'로 한 장에 그려주세요.
                2. 주제를 관통하는 핵심 키워드 3~4개를 뽑아 눈에 띄게 배치하고, 각 키워드의 유반의어 1개씩만 곁들여 주세요.
                """
            else:
                system_prompt = base_instruction + f"\n[명령]: 학생의 다음 질문/하소연에 다정하고 전문적으로 답변하세요. \n[학생 질문]: {user_question}"

            with st.spinner("답변을 생성 중입니다..."):
                try:
                    response = model.generate_content(system_prompt)
                    st.info("💡 **조교의 답변:**")
                    st.markdown(response.text, unsafe_allow_html=True)
                except Exception as e:
                    st.error("답변 생성 중 오류가 발생했습니다.")
