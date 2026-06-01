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

# --- 🚨 1. 저작권 보호 및 '상세분석', '지문분석' 글씨 완전 세탁기 ---
def clean_display_name(raw_name):
    blacklist = ['이그잼포유', 'exam4you', '아잉카', '리카수니', '황인영', '기출비', '족보닷컴', '나무아카데미', '상세분석', '지문분석']
    cleaned = raw_name
    for word in blacklist:
        cleaned = re.sub(word, '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\[.*?\]|\(.*?\)|\_내지|\_통합본|\_생략된 지문|\_분석노트|\_정답', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
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

# --- 🚨 2. 스마트 교재 맞춤형 드롭다운 (폴더명까지 체크!) ---
def get_dynamic_dropdowns(book_name, category_name="", selected_u=None):
    clean_name = book_name.replace(" ", "")
    clean_cat = category_name.replace(" ", "")
    
    if "수능특강light영어독해연습" in clean_name or "수특light" in clean_name:
        units = [f"{i}강" for i in range(1, 13)] + [f"Mini Test {i}" for i in range(1, 4)] + ["직접 입력 (타이핑)"]
        if selected_u and "Mini Test" in selected_u:
            qs = [f"{i}번" for i in range(1, 29)] + ["전체 지문", "직접 입력 (타이핑)"]
        else:
            qs = [f"{i}번" for i in range(1, 8)] + ["5-6번", "6-7번", "전체 지문", "직접 입력 (타이핑)"]
        return units, qs
        
    elif "올림포스영어독해의기본1" in clean_name or "올림포스영어독해의기본2" in clean_name:
        units = [f"Unit {i}" for i in range(1, 19)] + ["직접 입력 (타이핑)"]
        qs = ["Analysis", "1번", "2번", "3번", "서술형", "논술형", "1-2번", "2-3번", "전체 지문", "직접 입력 (타이핑)"]
        return units, qs
        
    elif "올림포스9대변형유형" in clean_name:
        units = [f"Unit {i}" for i in range(1, 11)] + ["Test", "직접 입력 (타이핑)"]
        qs = [f"{i}번" for i in range(1, 9)] + ["전체 지문", "직접 입력 (타이핑)"]
        return units, qs
        
    # [강화된 모의고사/학력평가 로직: 폴더명이나 교재명에 단어가 있으면 발동]
    elif "모의고사" in clean_name or "모의고사" in clean_cat or "학력평가" in clean_name:
        units = [f"{i}번" for i in range(18, 46)] + ["41-42번", "43-45번", "전체 지문", "직접 입력 (타이핑)"]
        qs = [] # 4번 지문 번호 창을 비워버립니다.
        return units, qs
        
    else:
        units = [f"Unit {i}" for i in range(1, 26)] + ["Test/모의고사", "직접 입력 (타이핑)"]
        qs = [f"{i}번" for i in range(1, 16)] + ["전체 지문", "직접 입력 (타이핑)"]
        return units, qs

st.set_page_config(page_title="English with Nora_혼자서도 할 수 있다! 중/고등학생 내신대비 자습실", page_icon="📚", layout="centered")
st.markdown("<h2 style='text-align: center;'>📚 English with Nora_혼자서도 할 수 있다!<br>중/고등학생 내신대비 자습실</h2><hr>", unsafe_allow_html=True)

if "user_db" not in st.session_state:
    st.session_state.user_db = {}

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

with st.spinner("📚 자습실 자료 동기화 중..."):
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
                if clean_name not in pdf_options[category_name]:
                    pdf_options[category_name].append(clean_name)
                    pdf_display_mapping[clean_name] = f 

st.subheader("🔍 1. 분석할 지문 불러오기")

if pdf_options:
    selected_category = st.selectbox("1) 출판사/분류 선택", list(pdf_options.keys()))
    display_books = pdf_options[selected_category]
    selected_display_book = st.selectbox("2) 교재명 선택", display_books)
    selected_book = pdf_display_mapping[selected_display_book]
    
    # --- 🚨 [수정됨] 폴더명(selected_category)과 교재명을 동시 체크하여 모의고사 여부 판단 ---
    is_mock_test = "모의고사" in selected_category.replace(" ", "") or "모의고사" in selected_display_book.replace(" ", "") or "학력평가" in selected_display_book.replace(" ", "")
    
    if is_mock_test:
        units, _ = get_dynamic_dropdowns(selected_display_book, selected_category)
        selected_unit = st.selectbox("3) 문항 번호 선택", ["선택하세요"] + units)
        final_unit = selected_unit
        if selected_unit == "직접 입력 (타이핑)":
            final_unit = st.text_input("문항 번호를 직접 적어주세요")
        final_q = "" # 모의고사는 4번 창이 사라짐
    else:
        units, _ = get_dynamic_dropdowns(selected_display_book, selected_category)
        col_unit, col_q = st.columns(2)
        with col_unit:
            selected_unit = st.selectbox("3) 단원 선택", ["선택하세요"] + units)
            final_unit = selected_unit
            if selected_unit == "직접 입력 (타이핑)":
                final_unit = st.text_input("단원을 직접 적어주세요")

        _, qs = get_dynamic_dropdowns(selected_display_book, selected_category, selected_unit)
        with col_q:
            selected_q = st.selectbox("4) 지문 번호 선택", ["선택하세요"] + qs)
            final_q = selected_q
            if selected_q == "직접 입력 (타이핑)":
                final_q = st.text_input("지문 번호를 직접 적어주세요")
    
    textbook_unit = f"{final_unit} {final_q}".strip()
    
    if "extracted_text" not in st.session_state:
        st.session_state.extracted_text = ""
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = ""

    if st.button("✅ 선택한 지문 텍스트 확인하기"):
        if "선택하세요" in textbook_unit:
            st.warning("단원이나 번호를 정확히 선택해주세요!")
        else:
            with st.spinner("PDF에서 지문을 읽어오는 중입니다..."):
                try:
                    extract_prompt = f"'{textbook_unit}'에 해당하는 영어 지문 원문(Text)만 정확히 추출해. 다른 사설이나 번역은 절대 포함하지 말고 영어 원문만 출력해."
                    if selected_book in permanent_pdf_files_dict:
                        target_pdf = permanent_pdf_files_dict[selected_book]
                        response = model.generate_content([extract_prompt, target_pdf])
                        st.session_state.extracted_text = response.text
                        st.session_state.analysis_result = "" 
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
    
    with st.form("analysis_form"):
        st.subheader("💡 2. 학습 모드 및 질문 입력")
        mode = st.radio("원하는 분석 모드를 선택하세요:", [
            "1. 구문 분석 + 초급 다의어 설명", 
            "2. 주요 지문 2개 분석 + 중상급 유반의어 정리", 
            "3. 전체 줄거리 시각화 구조도",
            "4. 💬 자습 도우미에게 직접 질문하기 (자유 질문)"
        ])

        user_question = st.text_input("궁금한 점을 자유롭게 적어주세요 (4번 모드 선택 시 필수):")
        submitted = st.form_submit_button("🚀 분석 실행 (확인)")

    if submitted:
        if "4." in mode and not user_question.strip():
            st.warning("질문 내용을 입력해 주세요!")
        else:
            if credits_left != "무제한":
                if st.session_state.user_db[st.session_state.current_student]["credits"] <= 0:
                    st.error("🚨 무료 체험 횟수를 소진했습니다. 월 3,000원 이용권 결제가 필요합니다!")
                    st.stop()
                else:
                    st.session_state.user_db[st.session_state.current_student]["credits"] -= 1

            base_instruction = "당신은 학생들의 자습을 완벽하게 서포트하는 유능한 '자습 도우미'입니다. 반드시 제공된 [영어 지문] 내용만을 바탕으로 답변해야 하며, 존댓말을 사용하세요.\n[영어 지문]:\n" + st.session_state.extracted_text

            if "1. 구문" in mode:
                system_prompt = base_instruction + "\n[출력 명령 - 시중 최고급 구문 워크북 스타일]\n1. 지문에 존재하는 모든 영문장을 한 문장씩 행 단위로 깔끔히 격리 배치하고 바로 아래에 1:1 대응하는 한글 번역을 쌍으로 매칭하세요.\n2. 줄글로 풀어쓰는 난잡한 분석은 절대 엄금합니다. 영문장 내부의 핵심 구조(명사절, 형용사구, 부사절 등)를 명확한 기호구획([ ], ( ))으로 가두어 시각화하고, 복잡한 구문 성분을 기호 하단이나 우측에 표 형태로 깔끔하게 단답형으로 쪼개서 정리하세요.\n3. 지문 내에서 다의어 성격이 매우 강한 기초 핵심 단어 3개를 엄선하여, '단어 본질적 개념', '본 지문 내 문맥적 의미', '기타 핵심 다의어 확장 의미'를 마크다운 표(Table)로 완벽히 구조화하여 나열하세요."
            elif "2. 주요" in mode:
                system_prompt = base_instruction + "\n[출력 명령 - 2대 핵심 문장 픽 박스 & Merriam-Webster 유반의어 데이터]\n1. 지문 전체 문장 해석은 과감하게 누락시키고, 오직 단 2개의 극대화된 핵심 문장만 엄선하여 전용 분석 박스를 구현하세요. (문장1: 줄거리 핵심, 문장2: 문법 복잡)\n2. 이 2개의 문장은 절대로 텍스트 줄글 해설로 뭉뚱그리지 말고, 시중의 프리미엄 유료 분석지 레이아웃을 벤치마킹하여 아래의 가독성 높은 구획화 구조로 완전히 해체하여 표기하세요. [원본 영문장 명시] -> [구조 격파 기호 분할 및 성분 파싱 단락] -> [핵심 어법적 킬러 포인트 핵심 요약]\n3. 지문의 핵심 키워드 3개를 추출하고, 미국의 세계적인 권위 사전인 'Merriam-Webster' 기준에 명확히 입각하여, 가장 관련도가 조밀하고 진하게 처리되는 최우선 순위의 동의어(Synonyms)와 반의어(Antonyms)를 체계적인 정돈 표(Table)로 가공해 내세요."
            elif "3. 전체" in mode:
                system_prompt = base_instruction + "\n[출력 명령 - 철저한 한글 중심 인포그래픽 흐름도 디자인]\n1. 영어 중심의 나열이나 단순 아이콘 배치는 자습 능률을 심각하게 저하시키므로 절대로 금지합니다. 해설 구조 전체를 철저하게 '한글 중심'으로 가공하세요.\n2. 캔바(Canva)나 노트북LM의 핵심 요약 인포그래픽 포스터를 보듯, 지문의 흐름 및 논리 구조를 가로 혹은 세로형태의 마크다운 다이어그램 서식 블록으로 가시화하세요. 예시 흐름 레이아웃: [ 배경/도입 ] ➔ [ 전개 및 원인 발발 ] ➔ [ 핵심 갈등/심화 단락 ] ➔ [ 최종 결론 및 요약 ]\n3. 최종 하단 영역에는 해당 지문의 대의를 관통하는 핵심 테마 키워드 3개를 선정하고, 각 단어별 핵심 유반의어를 1~2개씩 촘촘하게 곁들인 '한글 키워드 블록 리스트'를 만들어 자습 마무리를 도우세요."
            else:
                system_prompt = base_instruction + "\n[명령]: 학생의 다음 구체적인 자유 질문이나 자습 중 애로사항에 대해 명쾌한 해결책과 따뜻한 격려를 건네세요. \n[학생 질문]: " + user_question

            with st.spinner("자습실 도우미가 분석지를 정교하게 빌드 중입니다..."):
                try:
                    response = model.generate_content(system_prompt)
                    st.session_state.analysis_result = response.text
                except Exception as e:
                    st.error("해설을 생성하는 과정에서 에러가 발생했습니다.")
    
    if st.session_state.get("analysis_result"):
        st.info("📌 **자습실 해설:**")
        st.markdown(st.session_state.analysis_result, unsafe_allow_html=True)

# ==== 코드의 끝입니다. 여기까지 모두 복사되었는지 꼭 확인하세요! ====
