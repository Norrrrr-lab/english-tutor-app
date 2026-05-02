import streamlit as st
import google.generativeai as genai
import PyPDF2
from PIL import Image

# 1. 비밀 금고에서 API 키 가져오기 (학생들에겐 절대 안 보임!)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
# 사진도 볼 수 있는 최신 멀티모달 모델 사용
model = genai.GenerativeModel('gemini-1.5-flash-latest')
# 2. 웹사이트 기본 설정 및 변경된 타이틀
st.set_page_config(page_title="English with Nora", page_icon="📚", layout="centered")

st.title("📚 English with Nora_Assistant system")
st.markdown("""
**수업 시간 중 다루었던 내신 시험 범위 내에서 헷갈리는 부분은 바로바로 질문해 보세요!**

📌 **[질문 방법]**
- 질문 할 구문을 문제만 잘 보이도록 사진을 찍어서, 한 구문만 올립니다.
- 구문을 올린 후 번호를 선택해서 구체적인 사항을 질문합니다.
""")

# 3. 학생 선택 기능 (수지 vs 이정 맞춤형 프롬프트 분리)
st.divider()
student_name = st.radio("👤 본인의 이름을 선택해 주세요:", ["수지 (문법/내용 중심)", "이정 (유반의어/핵심문장 중심)"])

# 선생님 전용 지식 베이스를 저장할 임시 공간
if "teacher_context" not in st.session_state:
    st.session_state.teacher_context = ""

# 4. 선생님 전용 비밀 공간 (사이드바)
with st.sidebar:
    st.header("🔒 선생님 전용 메뉴")
    pw_input = st.text_input("비밀번호를 입력하세요", type="password")
    
    # 설정한 비밀번호가 맞을 때만 업로드 창이 열림
    if pw_input == st.secrets["TEACHER_PASSWORD"]:
        st.success("인증 완료! 보조재료를 업로드하세요.")
        teacher_file = st.file_uploader("교사용 교재/변형문제 업로드 (PDF/TXT)", type=['pdf', 'txt'])
        
        if teacher_file:
            if teacher_file.name.endswith('.pdf'):
                pdf_reader = PyPDF2.PdfReader(teacher_file)
                extracted = "".join([page.extract_text() or "" for page in pdf_reader.pages])
                st.session_state.teacher_context = extracted
            else:
                st.session_state.teacher_context = teacher_file.read().decode("utf-8")
            st.info("✅ 선생님 자료가 AI의 뇌에 저장되었습니다! (학생들은 볼 수 없습니다)")

# 5. 학생용 파일/사진 업로드 영역 (JPG, PNG 추가)
st.divider()
st.subheader("📂 질문할 구문 사진/파일 업로드")
student_file = st.file_uploader("핸드폰으로 찍은 사진이나 파일을 올려주세요", type=['jpg', 'jpeg', 'png', 'pdf', 'txt'])

uploaded_content = None # 텍스트 또는 이미지 객체를 담을 변수

if student_file:
    # 사진 파일일 경우
    if student_file.type.startswith('image/'):
        image = Image.open(student_file)
        st.image(image, caption="업로드한 사진", use_container_width=True)
        uploaded_content = image
    # PDF 파일일 경우
    elif student_file.name.endswith('.pdf'):
        pdf_reader = PyPDF2.PdfReader(student_file)
        uploaded_content = "".join([page.extract_text() or "" for page in pdf_reader.pages])
        st.text_area("업로드한 텍스트", uploaded_content, height=150)
    # TXT 파일일 경우
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

    # 학생에 따른 프롬프트(지시어) 설정
    if "수지" in student_name:
        system_prompt = f"""
        너는 노라 선생님의 친절한 영어 조교야. 학생 이름은 '수지'야.
        학생이 올린 자료와 질문을 바탕으로 문법과 내용 이해 중심으로 친절하게 설명해줘.
        
        [선생님이 제공한 참고 자료 (없을 수도 있음)]: {st.session_state.teacher_context}
        [학생의 질문]: {user_question}
        """
    else:
        system_prompt = f"""
        너는 노라 선생님의 꼼꼼한 영어 조교야. 학생 이름은 '이정'이야.
        학생이 올린 자료를 바탕으로 질문에 답하되, 반드시 다음 양식에 맞춰 추가 학습 내용을 제공해.
        
        1. 이 지문의 주제를 관통하는 주요 핵심 문장 2개를 먼저 짚어줄 것.
        2. 해당 문장에서 쓰인 동사, 형용사, 부사 순으로 단어를 추출할 것.
        3. 추출한 단어들에 대해 '토플 해커스보카 초록이' 및 '보카바이블' 수준에 맞는 고급 유의어와 반의어를 표 형태로 정리해 줄 것.
        
        [선생님이 제공한 참고 자료 (없을 수도 있음)]: {st.session_state.teacher_context}
        [학생의 질문]: {user_question}
        """

    # AI에게 질문 전송 (사진인지 텍스트인지에 따라 다르게 처리)
    with st.chat_message("assistant"):
        with st.spinner("노라 조교가 열심히 분석 중입니다..."):
            if isinstance(uploaded_content, Image.Image):
                # 사진과 텍스트(프롬프트)를 동시에 던짐
                response = model.generate_content([system_prompt, uploaded_content])
            else:
                response = model.generate_content(f"{system_prompt}\n\n[학생 업로드 지문]:\n{uploaded_content}")
            
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
