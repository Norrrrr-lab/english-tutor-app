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

# --- 🚨 타이틀 및 헤더 변경 완료 ---
st.set_page_config(page_title="English with Nora_혼자서도 할 수 있다! 중/고등학생 내신대비 자습실", page_icon="📚", layout="centered")
st.markdown("<h2 style='text-align: center;'>📚 English with Nora_혼자서도 할 수 있다!<br>중/고등학생 내신대비 자습실</h2><hr>", unsafe_allow_html=True)

    }

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
            if category_name not in pdf_options:
                pdf_options[category_name] = []
            for f in pdf_files:
                clean_name = clean_display_name(f)
                # --- 🚨 교재명 선택 시 중복 노출 전면 제거 ---
                if clean_name not in pdf_options[category_name]:
                    pdf_options[category_name].append(clean_name)
                    pdf_display_mapping[clean_name] = f 

st.subheader("🔍 1. 분석할 지문 불러오기")

if pdf_options:
    selected_category = st.selectbox("1) 출판사/분류 선택", list(pdf_options.keys()))
    display_books = pdf_options[selected_category]
    selected_display_book = st.selectbox("2) 교재명 선택", display_books)
    selected_book = pdf_display_mapping[selected_display_book]
    
    col_unit, col_q = st.columns(2)
    with col_unit:
        unit_list = [f"{i}강 (Unit {i})" for i in range(1, 31)] + ["Test/모의고사", "기타", "직접 입력 (타이핑)"]
        selected_unit = st.selectbox("3) 단원 선택", ["선택하세요"] + unit_list)
        
        final_unit = selected_unit
        if selected_unit == "직접 입력 (타이핑)":
            final_unit = st.text_input("단원을 직접 적어주세요")

    with col_q:
        q_list = [f"{i}번" for i in range(1, 21)] + ["전체 지문", "직접 입력 (타이핑)"]
        selected_q = st.selectbox("4) 지문 번호 선택", ["선택하세요"] + q_list)
        
        final_q = selected_q
        if selected_q == "직접 입력 (타이핑)":
            final_q = st.text_input("지문 번호를 직접 적어주세요")
    
    textbook_unit = f"{final_unit} {final_q}"
    
    if "extracted_text" not in st.session_state:
        st.session_state.extracted_text = ""

    if st.button("✅ 선택한 지문 텍스트 확인하기"):
        if selected_unit == "선택하세요" or selected_q == "선택하세요":
            st.warning("단원과 번호를 모두 선택해주세요!")
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
        "4. 💬 자습 도우미에게 직접 질문하기 (하소연 및 자유 질문)"
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
                    st.error("🚨 무료 체험 횟수를 소진했습니다 이용권 결제가 필요합니다!")
                    st.stop()
                else:
                    st.session_state.user_db[st.session_state.current_student]["credits"] -= 1

            # --- 🚨 [Wording & 명칭 변경 완료] 자습 도우미 지정 ---
            base_instruction = f"""
            당신은 학생들의 자습을 완벽하게 서포트하는 유능한 '자습 도우미'입니다. 
            반드시 제공된 [영어 지문] 내용만을 바탕으로 답변해야 하며, 존댓말을 사용하세요.
            [영어 지문]:
            {st.session_state.extracted_text}
            """

            # --- 🚨 [구조 개편] 시중 워크북/인포그래픽 스타일 레이아웃 프롬프트 ---
            if "1. 구문" in mode:
                system_prompt = base_instruction + """
                [출력 명령 - 시중 최고급 구문 워크북 스타일]
                1. 지문의 모든 영문장을 한 줄씩 나열하고 바로 밑에 깔끔한 한글 해석을 붙이세요.
                2. 줄글로 주절주절 분석하지 마세요. 각 문장마다 핵심 구조(절, 수식어구)를 대괄호([ ]), 소괄호(( )) 등으로 명확히 구획화하여 표기하고 구조적 특징을 단답형식으로 정돈하여 표기하세요.
                3. 지문에서 다의어 성격이 강한 기초 어휘 3개를 엄선하여 단어의 본질적 개념과 본 지문에서 쓰인 의미, 그리고 다른 핵심 다의어 뜻을 일목요연한 마크다운 표(Table)로 정리하세요.
                """
            elif "2. 주요" in mode:
                system_prompt = base_instruction + """
                [출력 명령 - 2대 핵심 지문 픽 및 Merriam-Webster 유반의어]
                1. 지문 전체 해석은 과감히 생략하세요. 오직 딱 2개의 핵심 문장만 선정하여 분석 박스를 만드세요.
                   - 문장 1 (줄거리 핵심): 지문의 주제 및 스토리를 관통하는 가장 중요한 문장
                   - 문장 2 (문법 복잡): 구조적으로 가장 까다롭고 문법 요소가 밀집된 문장
                2. 선정한 각 문장은 아래 형태로 마크다운 코드 블록이나 가독성 높은 구획화 표기를 사용하여 시각적으로 완벽히 뜯어내세요.
                   - [원본 문장] -> [구조 격파 분할 분석] -> [핵심 문법적 포인트 요약]
                3. 지문의 핵심 키워드 3개를 선정하고, 미국 최정상 사전인 'Merriam-Webster' 기준에 맞추어 관련도가 가장 깊은(가장 진하게 표시되는 핵심 단어들) 동의어(Synonyms)와 반의어(Antonyms)를 체계적인 표로 구성하세요.
                """
            elif "3. 전체" in mode:
                system_prompt = base_instruction + """
                [출력 명령 - 한글 인포그래픽 블록 흐름도]
                1. 영어나 아이콘 나열식 요약은 학생들의 직관적 인지를 방해하므로 절대 금지합니다. 철저히 '한글 중심'으로 작성하세요.
                2. 지문의 스토리 전개 과정을 마치 노트북LM이나 캔바의 포스터처럼 한눈에 들어오는 가로/세로 방향의 블록 다이어그램 형태로 텍스트 구조화 마크다운을 만드세요.
                   - 예시: [ 도입 단계 ] ➔ [ 전개/원인 발생 ] ➔ [ 핵심 심화 ] ➔ [ 최종 결론 ]
                   - 각 단계 내부에는 핵심 사건과 논리 구조를 1~2줄 요약형태로 꽉 차게 정리하세요.
                3. 마지막 하단에는 이 지문의 핵심 테마 단어 3개를 선별하여 배치하고, 각 단어의 핵심 유반의어를 1~2개씩 곁들여 키워드 블록 리스트를 만드세요.
                """
            else:
                system_prompt = base_instruction + f"\n[명령]: 학생의 다음 자유 질문이나 자습 하소연에 대하여 정성을 다해 해결책과 공감을 제공하세요. \n[학생 질문]: {user_question}"

            with st.spinner("자습 도우미가 분석지를 정교하게 생성 중입니다..."):
                try:
                    response = model.generate_content(system_prompt)
                    # --- 🚨 [Wording 변경 완료] 조교의 답변 -> 해설 ---
                    st.info("📌 **자습실 해설:**")
                    st.markdown(response.text, unsafe_allow_html=True)
                except Exception as e:
                    st.error("해설 생성 중 오류가 발생했습니다.")
