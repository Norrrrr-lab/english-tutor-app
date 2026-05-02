import streamlit as st
import google.generativeai as genai
import PyPDF2
from PIL import Image

# 1. API 키 설정
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# 2. 최신 AI 모델 자동 연결
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

# 3. 페이지 기본 설정
st.set_page_config(page_title="English with Nora", page_icon="📚", layout="centered")

# 제목 및 안내 멘트
st.markdown("<h2 style='white-space: nowrap; font-size: 26px; text-align: center;'>📚 English with Nora_Assistant system</h2>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center;'>
<b>수업 시간 중 다루었던 내신 시험 범위 내에서 헷갈리는 부분은 바로바로 질문해 보세요!</b><br><br>
</div>
<b>📌 [질문 방법]</b><br>
- 질문 할 구문을 문제만 잘 보이도록 사진을 찍어서, 한 구문만 올립니다.<br>
- 구문을 올린 후 번호를 선택해서 구체적인 사항을 질문합니다.<br>
<hr>
""", unsafe_allow_html=True)

# 4. 학생 로그인 시스템 (직접 입력 방식)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.current_student = ""

if not st.session_state.logged_in:
    st.subheader("🔒 학생 로그인")
    input_id = st.text_input("아이디 (본인 이름)를 입력하세요:")
    input_pw = st.text_input("부여받은 비밀번호를 입력하세요:", type="password")

    if st.button("로그인"):
        # 입력한 아이디(이름)에 맞는 비밀번호를 Secrets에서 찾아옴
        expected_pw = st.secrets.get(f"{input_id}_PW", None)
        
        if expected_pw and input_pw == expected_pw:
            st.session_state.logged_in = True
            st.session_state.current_student = input_id
            st.rerun()
        else:
            st.error("아이디나 비밀번호가 틀렸습니다. 선생님께 확인해 주세요!")

    # 5. 선생님 전용 비밀 공간 (로그인 전 화면 맨 아래에 배치)
    st.divider()
    with st.expander("⚙️"):
        st.caption("🔒 관리자 전용 메뉴")
        pw_input = st.text_input("선생님 비밀번호를 입력하세요", type="password", key="teacher_pw_out")
        
        if pw_input == st.secrets.get("TEACHER_PASSWORD", "nora"):
            st.success("인증 완료! 보조재료를 업로드하세요.")
            st.caption(f"🤖 현재 연결된 AI 모델: {valid_model_name}")
            teacher_file = st.file_uploader("교사용 교재/변형문제 업로드 (PDF/TXT - 해당 범위만 잘라서 올리세요!)", type=['pdf', 'txt'])
            
            if teacher_file:
                if teacher_file.name.endswith('.pdf'):
                    pdf_reader = PyPDF2.PdfReader(teacher_file)
                    extracted = "".join([page.extract_text() or "" for page in pdf_reader.pages])
                    st.session_state.teacher_context = extracted
                else:
                    st.session_state.teacher_context = teacher_file.read().decode("utf-8")
                st.info("✅ 선생님 자료가 AI의 뇌에 저장되었습니다!")
    st.stop() # 로그인을 안 하면 여기서 화면 멈춤

# --- 여기서부터는 로그인 성공 시 보여지는 화면 ---

st.success(f"환영합니다, {st.session_state.current_student} 학생! 😊")
if st.button("로그아웃"):
    st.session_state.logged_in = False
    st.session_state.messages = [] 
    st.rerun()

if "teacher_context" not in st.session_state:
    st.session_state.teacher_context = ""

st.divider()

# 6. 파일 업로드 영역
st.subheader("📂 질문할 구문 사진/파일 업로드")
student_file = st.file_uploader("핸드폰으로 찍은 사진이나 파일을 올려주세요", type=['jpg', 'jpeg', 'png', 'pdf', 'txt'])

uploaded_content = None

if student_file:
    if student_file.type.startswith('image/'):
        image = Image.open(student_file)
        st.image(image, caption="업로드한 사진", use_container_width=True)
        uploaded_content = image
    elif student_file.name.endswith('.pdf'):
        pdf_reader = PyPDF2.PdfReader(student_file)
        uploaded_content = "".join([page.extract_text() or "" for page in pdf_reader.pages])
        st.text_area("업로드한 텍스트", uploaded_content, height=150)
    else:
        uploaded_content = student_file.read().decode("utf-8")
        st.text_area("업로드한 텍스트", uploaded_content, height=150)

# 7. 기능 선택 및 채팅 영역
st.divider()
st.subheader("💡 학습 기능 선택")
st.write("원하는 분석 모드를 선택한 후 질문을 입력하세요.")

mode = st.radio("분석 모드:", [
    "1. 구문 분석 + 초급 동음이의어/다의어 정리", 
    "2. 주요 문장 2개 + 중상급 유반의어 정리", 
    "3. 전체 줄거리 구조화 (도식/요약)"
])

st.divider()
st.subheader("💬 조교에게 질문하기")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_question = st.chat_input("질문 또는 요청사항을 입력하세요 (예: 이 지문 분석해 줘)")

if user_question and uploaded_content:
    st.chat_message("user").markdown(user_question)
    st.session_state.messages.append({"role": "user", "content": user_question})

    # 모드에 따른 AI 프롬프트(지시어) 설정
    if "1. 구문" in mode:
        system_prompt = f"""
        너는 전문적인 영어 조교야. 학생이 올린 자료를 바탕으로 다음을 수행해.
        1. 질문한 구문에 대한 정확한 문법 및 구조 분석.
        2. 지문에 사용된 기초 단어(예: flow, run, matter 등 다의어)를 1~2개 뽑아, 해당 지문에서의 뜻과 다른 품사/상황에서의 뜻을 예문과 함께 쉽게 설명해 줄 것.
        [참고 자료]: {st.session_state.teacher_context}
        [질문]: {user_question}
        """
    elif "2. 주요" in mode:
        system_prompt = f"""
        너는 전문적인 영어 조교야. 학생이 올린 자료를 바탕으로 다음을 수행해.
        1. 지문의 주제를 관통하는 핵심 문장(Topic Sentence) 2개를 뽑아 해석할 것.
        2. 지문 속 동사, 형용사, 부사 중 고급 어휘를 추출해, 토플 해커스보카/보카바이블 수준의 고급 유의어와 반의어를 표 형태로 정리해 줄 것.
        [참고 자료]: {st.session_state.teacher_context}
        [질문]: {user_question}
        """
    else:
        system_prompt = f"""
        너는 전문적인 영어 조교야. 학생이 올린 자료를 바탕으로 다음을 수행해.
        1. 지문의 전체 줄거리와 논리적 흐름(원인-결과, 문제-해결, 대조 등)을 한눈에 파악할 수 있도록 마크다운 표, 글머리 기호, 화살표(->) 등을 활용하여 '구조도(인포그래픽 텍스트)' 형태로 시각화하여 요약해 줄 것.
        2. 복잡한 문장보다는 핵심 키워드 위주로 정리할 것.
        [참고 자료]: {st.session_state.teacher_context}
        [질문]: {user_question}
        """

    with st.chat_message("assistant"):
        with st.spinner("노라 조교가 열심히 분석 중입니다..."):
            try:
                if isinstance(uploaded_content, Image.Image):
                    response = model.generate_content([system_prompt, uploaded_content])
                else:
                    response = model.generate_content(f"{system_prompt}\n\n[학생 업로드 지문]:\n{uploaded_content}")
                
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"분석 중 오류가 발생했습니다: {e}")
