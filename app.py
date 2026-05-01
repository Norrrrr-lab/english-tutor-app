import streamlit as st
import google.generativeai as genai
import PyPDF2
import re

# 1. 웹사이트 기본 설정 (탭 이름, 아이콘)
st.set_page_config(page_title="Nora's English Lab", page_icon="📚", layout="centered")

# 2. 타이틀 및 인사말
st.title("📚 수지 & 이정 전용 영어 조교 시스템")
st.markdown("선생님이 올려주신 지문을 꼼꼼히 읽고, 헷갈리는 부분은 바로바로 질문해 보세요!")

# 3. 사이드바 (API 키 입력 및 선생님 전용 세팅 공간)
with st.sidebar:
    st.header("⚙️ 선생님 전용 설정")
    st.markdown("Gemini API 키를 입력해 주세요. (학생들에게는 보이지 않게 처리할 수 있습니다)")
    api_key = st.text_input("API Key", type="password")

# API 키가 입력되면 AI 모델 준비
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.info("👈 왼쪽 사이드바에 API 키를 먼저 입력해 주세요!")

# 4. 지문 업로드 기능
st.divider()
uploaded_file = st.file_uploader("📂 공부할 지문 파일 업로드 (PDF 또는 TXT)", type=['pdf', 'txt'])

if uploaded_file is not None:
    text = ""
    # PDF 파일 읽기
    if uploaded_file.name.endswith('.pdf'):
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + " "
    # TXT 파일 읽기
    else:
        text = uploaded_file.read().decode("utf-8")
    
    # 5. 문장 번호 매기기 로직 (마침표, 물음표 등 기준으로 분리)
    st.subheader("📖 오늘의 지문")
    
    # 정규식을 사용해 문장 깔끔하게 분리
    sentences = re.split(r'(?<=[.?!])\s+', text.strip())
    sentences = [s for s in sentences if s] # 빈 문장 제거
    
    formatted_text = ""
    for i, sentence in enumerate(sentences):
        # 화면에 번호 달아서 출력
        st.write(f"**{i+1}.** {sentence}")
        # AI에게 전달할 텍스트도 번호 달아서 묶어두기
        formatted_text += f"{i+1}. {sentence}\n"

    # 6. 챗봇 질문 영역
    st.divider()
    st.subheader("💬 지문 질문하기")
    
    # 대화 기록 저장소 생성
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 기존 대화 화면에 보여주기
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 학생이 질문 입력
    user_question = st.chat_input("예: 3번 문장에서 to부정사가 명사적 용법으로 쓰인 게 맞아?")

    if user_question:
        # 학생 질문 화면에 띄우기
        st.chat_message("user").markdown(user_question)
        st.session_state.messages.append({"role": "user", "content": user_question})

        # 7. AI에게 전달할 '선생님의 바이브' 프롬프트 지시어
        if api_key:
            prompt = f"""
            너는 학생들을 아끼고 친절하게 가르치는 영어 과외 선생님 '노라'의 온라인 조교야.
            다음은 학생이 현재 공부하고 있는 영어 지문이야:
            
            [업로드된 지문]
            {formatted_text}
            
            학생의 질문: {user_question}
            
            지시사항:
            1. 반드시 위의 [업로드된 지문] 내용을 바탕으로 대답할 것.
            2. 학생이 이해하기 쉽도록 친근하고 격려하는 말투를 사용할 것.
            3. 문장 번호를 언급하며 설명해 주면 더 좋아.
            """
            
            # AI 답변 생성 및 화면에 띄우기
            with st.chat_message("assistant"):
                response = model.generate_content(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
