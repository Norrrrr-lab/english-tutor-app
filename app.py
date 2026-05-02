import streamlit as st
import google.generativeai as genai
import PyPDF2
from PIL import Image

# 1. API 키 설정 (비밀 금고에서 가져옴)
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

# [수정 1] 제목 줄바꿈 방지 및 안내 멘트 중앙 정렬
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

# 4. [수정 2] 학생 로그인 시스템
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.current_student = ""

if not st.session_state.logged_in:
    st.subheader("🔒 학생 로그인")
    student_name = st.radio("👤 본인의 이름을 선택해 주세요:", ["수지", "이정"])
    student_pw = st.text_input("부여받은 비밀번호를 입력하세요:", type="password")

    if st.button("로그인"):
        # 비밀 금고(Secrets)에 저장된 학생 비번과 대조
        if student_pw == st.secrets.get(f"{student_name}_PW", ""):
            st.session_state.logged_in = True
            st.session_state.current_student = student_name
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다. 선생님께 확인해 주세요!")
    st.stop() # 로그인을 안 하면 여기서 화면이 멈춤 (아래 내용을 안 보여줌)

# 로그인 성공 메시지
st.success(f"환영합니다, {st.session_state.current_student} 학생! 😊")
if st.button("로그아웃"):
    st.session_state.logged_in = False
    st.session_state.messages = [] # 로그아웃 시 대화 내용 초기화
    st.rerun()

# 선생님 전용 지식 베이스 임시 공간
if "teacher_context" not in st.session_state:
    st.session_state.teacher_context = ""

# 5. 학생용 파일/사진 업로드 영역
st.divider()
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

# 6. 채팅창 영역
st.divider()
st.subheader("💬 조교에게 질문하기")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_question = st.chat_input("질문을 입력하세요 (예: 이 문장의 동사가 뭐야?)")

if user_question and uploaded_content:
    st.chat_message("user").markdown(user_question)
    st.session_state.messages.append({"role": "user", "content": user_question})

    # 접속한 학생에 따른 프롬프트(지시어) 설정
    if "수지" in st.session_state.current_student:
        system_prompt = f"""
        너는 노라 선생님의 친절한 영어 조교야. 학생 이름은 '수지'야.
        학생이 올린 자료와 질문을 바탕으로 문법과 내용 이해 중심으로 친절하게 설명해줘.
        
        [선생님이 제공한 참고 자료]: {st.session_state.teacher_context}
        [학생의 질문]: {user_question}
        """
    else:
        system_prompt = f"""
        너는 노라 선생님의 꼼꼼한 영어 조교야. 학생 이름은 '이정'이야.
        학생이 올린 자료를 바탕으로 질문에 답하되, 반드시 다음 양식에 맞춰 추가 학습 내용을 제공해.
        
        1. 이 지문의 주제를 관통하는 주요 핵심 문장 2개를 먼저 짚어줄 것.
        2. 해당 문장에서 쓰인 동사, 형용사, 부사 순으로 단어를 추출할 것.
        3. 추출한 단어들에 대해 '토플 해커스보카 초록이' 및 '보카바이블' 수준에 맞는 고급 유의어와 반의어를 표 형태로 정리해 줄 것.
        
        [선생님이 제공한 참고 자료]: {st.session_state.teacher_context}
        [학생의 질문]: {user_question}
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

# 7. [수정 3] 선생님 전용 비밀 공간 (화면 맨 아래 톱니바퀴)
st.divider()
with st.expander("⚙️"):
    st.caption("🔒 관리자 전용 메뉴")
    pw_input = st.text_input("선생님 비밀번호를 입력하세요", type="password", key="teacher_pw")
    
    if pw_input == st.secrets.get("TEACHER_PASSWORD", "nora"):
        st.success("인증 완료! 보조재료를 업로드하세요.")
        st.caption(f"🤖 현재 연결된 AI 모델: {valid_model_name}")
        teacher_file = st.file_uploader("교사용 교재/변형문제 업로드 (PDF/TXT)", type=['pdf', 'txt'])
        
        if teacher_file:
            if teacher_file.name.endswith('.pdf'):
                pdf_reader = PyPDF2.PdfReader(teacher_file)
                extracted = "".join([page.extract_text() or "" for page in pdf_reader.pages])
                st.session_state.teacher_context = extracted
            else:
                st.session_state.teacher_context = teacher_file.read().decode("utf-8")
            st.info("✅ 선생님 자료가 AI의 뇌에 저장되었습니다! (학생들은 볼 수 없습니다)")
