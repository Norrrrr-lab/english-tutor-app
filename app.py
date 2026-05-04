import streamlit as st
import google.generativeai as genai
from PIL import Image
import os
import pandas as pd

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

# 🚨 [수정됨] 모든 파일을 한 번에 주지 않기 위해, 파일 이름표를 달아서 보관!
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
                        gemini_files_dict[book_key] = uploaded_file # 책 이름을 키값으로 저장
                    except Exception as e:
                        print(f"업로드 실패 ({filename}): {e}")
    return gemini_files_dict

st.set_page_config(page_title="English with Nora", page_icon="📚", layout="centered")

st.markdown("<h2 style='white-space: nowrap; font-size: 26px; text-align: center;'>📚 English with Nora_Assistant system</h2>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center;'>
<b>수업 시간 중 다루었던 내신 시험 범위 내에서 헷갈리는 부분은 바로바로 질문해 보세요!</b><br>
</div>
<hr>
""", unsafe_allow_html=True)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.current_student = ""

if not st.session_state.logged_in:
    st.subheader("🔒 학생 로그인")
    input_id = st.text_input("아이디 (본인 이름)를 입력하세요:")
    input_pw = st.text_input("부여받은 비밀번호를 입력하세요:", type="password")

    if st.button("로그인"):
        expected_pw = st.secrets.get(f"{input_id}_PW", None)
        if expected_pw and input_pw == expected_pw:
            st.session_state.logged_in = True
            st.session_state.current_student = input_id
            st.rerun()
        else:
            st.error("아이디나 비밀번호가 틀렸습니다. 선생님께 확인해 주세요!")

    st.divider()
    with st.expander("⚙️ 관리자 전용 메뉴"):
        pw_input = st.text_input("선생님 비밀번호를 입력하세요", type="password", key="teacher_pw_out")
        if pw_input == st.secrets.get("TEACHER_PASSWORD", "nora"):
            st.success("인증 완료! 프리미엄 컨설팅 시스템이 활성화되었습니다.")
            consulting_student_name = st.text_input("대상 학생 이름 (예: 김이정, 예비고2)")
            consulting_feedback = st.text_area("1. 누적 피드백을 모두 붙여넣으세요.", height=150)
            excel_files = st.file_uploader("2. 수치 데이터 엑셀 파일 업로드 (.xlsx, .csv)", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True)
            
            if st.button("📝 보고서 자동 생성하기"):
                with st.spinner("데이터 분석 및 보고서 작성 중..."):
                    excel_data_text = ""
                    if excel_files:
                        for ex_file in excel_files:
                            try:
                                if ex_file.name.endswith('.csv'):
                                    df = pd.read_csv(ex_file)
                                else:
                                    df = pd.read_excel(ex_file)
                                excel_data_text += f"\n\n--- [{ex_file.name} 데이터] ---\n{df.to_csv(index=False)}"
                            except Exception as e:
                                st.warning(f"오류 발생: {e}")

                    consulting_prompt = f"""
                    너는 전문 입시 컨설턴트 '노경혜 강사'야. 
                    [목차] 1. 통합 성적 추이 및 향후 수업 내용 2. 수업방식 3. 예상 성취도 및 기간 4. 수업료 및 수업 정책
                    [대상 학생]: {consulting_student_name}
                    [피드백]: {consulting_feedback}
                    [엑셀 데이터]: {excel_data_text}
                    """
                    try:
                        report_response = model.generate_content(consulting_prompt)
                        st.markdown(report_response.text)
                    except Exception as e:
                        st.error(f"보고서 생성 중 오류 발생: {e}")
    st.stop() 

with st.spinner("📚 선생님 자료를 AI가 세팅 중입니다... (최초 1회)"):
    permanent_pdf_files_dict = load_permanent_pdfs_to_gemini()

st.success(f"환영합니다, {st.session_state.current_student} 학생! 😊")
if st.button("로그아웃"):
    st.session_state.logged_in = False
    st.session_state.messages = [] 
    st.rerun()

st.divider()

pdf_options = {}
if os.path.exists("pdf_materials"):
    for root, dirs, files in os.walk("pdf_materials"):
        category_name = "미분류 자료" if root == "pdf_materials" else os.path.basename(root)
        pdf_files = [f.replace('.pdf', '') for f in files if f.endswith(".pdf")]
        if pdf_files:
            pdf_options[category_name] = pdf_files

st.subheader("📂 1. 지문 찾기 (교재 선택 OR 사진 업로드)")

col1, col2 = st.columns(2)

with col1:
    st.write("📖 **선생님 교재에서 찾기**")
    if pdf_options:
        selected_category = st.selectbox("1) 교재 종류 선택", list(pdf_options.keys()))
        selected_book = st.selectbox("2) 교재명 선택", pdf_options[selected_category])
        textbook_unit = st.text_input("3) 지문 번호 (예: 3강 2번)")
    else:
        st.info("등록된 교재가 없습니다.")
        selected_category, selected_book, textbook_unit = "", "", ""

with col2:
    st.write("📷 **사진으로 찾기** (선택사항)")
    student_file = st.file_uploader("교재에 없는 자료라면 찍어 올려주세요!", type=['jpg', 'jpeg', 'png'])
    uploaded_content = None
    if student_file:
        image = Image.open(student_file)
        st.image(image, use_container_width=True)
        uploaded_content = image

st.divider()
st.subheader("💡 2. 학습 기능 선택")
mode = st.radio("분석 모드:", [
    "1. 구문 분석 + 초급 동음이의어/다의어 정리", 
    "2. 주요 문장 2개 + 중상급 유반의어 정리", 
    "3. 전체 줄거리 구조화 (도식/요약)",
    "4. 😭 시험공부 하다가 하소연하기 (위로가 필요할 때)"
])

st.divider()
st.subheader("💬 3. 조교에게 질문하기")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_question = st.chat_input("질문 또는 하소연을 자유롭게 입력하세요!")

if user_question:
    if "4." not in mode and uploaded_content is None and not textbook_unit:
        st.warning("⚠️ 지문을 분석하려면 교재 번호를 치거나 사진을 올려주세요!")
    else:
        st.chat_message("user").markdown(user_question)
        st.session_state.messages.append({"role": "user", "content": user_question})

        off_topic_rule = "영어 학습과 무관한 질문 시 짧게 거절해."
        location_prompt = f"학생이 질문한 위치: [{textbook_unit}]" if textbook_unit else ""

        if "1. 구문" in mode:
            system_prompt = f"전문 영어 조교야. {off_topic_rule} {location_prompt} PDF 자료에서 해당 지문을 찾아 1. 문법 분석 2. 다의어 설명. 질문: {user_question}"
        elif "2. 주요" in mode:
            system_prompt = f"전문 영어 조교야. {off_topic_rule} {location_prompt} PDF 자료에서 해당 지문을 찾아 1. 핵심 문장 해석 2. 고급 어휘 표 정리. 질문: {user_question}"
        elif "3. 전체" in mode:
            system_prompt = f"전문 영어 조교야. {off_topic_rule} {location_prompt} PDF 자료에서 해당 지문을 찾아 1. 논리 구조도 2. 핵심 키워드. 질문: {user_question}"
        else:
            system_prompt = f"심리 상담가야. 학생 이름은 '{st.session_state.current_student}'. 공감하고 위로해. 하소연: {user_question}"

        with st.chat_message("assistant"):
            with st.spinner("노라 조교가 답변을 준비 중입니다..."):
                try:
                    ai_input_contents = [system_prompt]
                    
                    # 🚨 [수정됨] 전체 PDF를 다 넣지 않고, '선택한 교재 딱 1권'만 골라서 AI에게 전달!
                    if selected_book and selected_book in permanent_pdf_files_dict:
                        ai_input_contents.append(permanent_pdf_files_dict[selected_book])
                        
                    if uploaded_content:
                        ai_input_contents.append(uploaded_content)

                    response = model.generate_content(ai_input_contents)
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"분석 중 오류가 발생했습니다: {e}")
