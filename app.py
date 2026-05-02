import streamlit as st
import google.generativeai as genai
import PyPDF2
from PIL import Image

# 1. 비밀 금고에서 API 키 가져오기
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# 🚨 [오류 자동 해결 핵심 코드] 구글 서버에서 당장 쓸 수 있는 모델을 스스로 검색해서 연결합니다.
valid_model_name = 'gemini-pro' # 최후의 기본값
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        if 'flash' in m.name:
            valid_model_name = m.name.replace("models/", "")
            break
        elif 'vision' in m.name:
            valid_model_name = m.name.replace("models/", "")

# 찾아낸 모델로 AI 뇌 장착
model = genai.GenerativeModel(valid_model_name)

# 2. 웹사이트 기본 설정
st.set_page_config(page_title="English with Nora", page_icon="📚", layout="centered")

st.title("📚 English with Nora_Assistant system")
st.markdown("""
**수업 시간 중 다루었던 내신 시험 범위 내에서 헷갈리는 부분은 바로바로 질문해 보세요!**

📌 **[질문 방법]**
- 질문 할 구문을 문제만 잘 보이도록 사진을 찍어서, 한 구문만 올립니다.
- 구문을 올린 후 번호를 선택해서 구체적인 사항을 질문합니다.
""")

# 3. 학생 선택 기능
st.divider()
student_name = st.radio("👤 본인의 이름을 선택해 주세요:", ["수지 (문법/내용 중심)", "이정 (유반의어/핵심문장 중심)"])

# 선생님 전용 지식 베이스 임시 공간
if "teacher_context" not in st.session_state:
    st.session_state.teacher_context = ""

# 4. 선생님 전용 비밀 공간 (사이드바)
with st.sidebar:
    st.header("🔒 선생님 전용 메뉴")
    st.caption(f"🤖 현재 연결된 AI 모델: {valid_model_name}") # 현재 연결된 모델을 선생님만 볼 수 있게 표시!
    pw_input = st.text_input("비밀번호를 입력하세요", type="password")
    
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
            st.info("✅ 선생님 자료가 AI의 뇌에 저장되었습니다!")

# 5. 학생용 업로드 영역
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

    if "수지" in student_name:
        system_prompt = f"""
        너는 노라 선생님의 친절한 영어 조교야. 학생 이름은 '수지'야.
        학생이 올린 자료와 질문을 바탕으로 문법과 내용 이해 중심으로 친절하게 설명해줘.
        
        [참고 자료]: {st.session_state.teacher_context}
        [질문]: {user_question}
        """
    else:
        system_prompt = f"""
        너는 노라 선생님의 꼼꼼한 영어 조교야. 학생 이름은 '이정'이야.
        학생이 올린 자료를 바탕으로 다음 양식에 맞춰 답변해.
        1. 핵심 문장 2개 짚어주기
        2. 동사, 형용사, 부사 단어 추출하기
        3. 추출한 단어의 고급 유의어와 반의어를 표 형태로 정리하기
        
        [참고 자료]: {st.session_state.teacher_context}
        [질문]: {user_question}
        """

    with st.chat_message("assistant"):
        with st.spinner("노라 조교가 열심히 분석 중입니다..."):
            try:
                if isinstance(uploaded_content, Image.Image):
                    response = model.generate_content([system_prompt, uploaded_content])
                else:
                    response = model.generate_content(f"{system_prompt}\n\n[지문]:\n{uploaded_content}")
                
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"분석 중 오류가 발생했습니다: {e}")
