import streamlit as st
import requests
import os
from dotenv import load_dotenv
from pypdf import PdfReader
import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_community.vectorstores import FAISS

load_dotenv()
st.set_page_config(page_title="企业级 PDF 知识库", page_icon="📄")
st.title("📄 企业级 PDF 智能问答助手")

# 读取 API Key
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# 侧边栏：上传 PDF 文件
with st.sidebar:
    st.header("📂 文档管理")
    uploaded_file = st.file_uploader("上传你的 PDF 文件", type=["pdf"])
    if uploaded_file is not None:
        st.success(f"已加载: {uploaded_file.name}")

# 核心逻辑：解析 PDF 并建库
@st.cache_resource(show_spinner=False)
def process_pdf(file_bytes):
    # 1. 解析 PDF
    reader = PdfReader(file_bytes)
    raw_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            raw_text += text + "\n"
    
    # 清洗
    clean_text = re.sub(r'\n\s*\n', '\n\n', raw_text)
    clean_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s，。！？：；,.!?:;()（）\-\n]', '', clean_text)
    
    # 2. 智能切分
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300, chunk_overlap=50,
        separators=["\n\n", "\n", "。", "！", "？", " ", ""]
    )
    chunks = text_splitter.split_text(clean_text)
    
    # 3. 向量化建库
    embeddings = FastEmbedEmbeddings()
    vectorstore = FAISS.from_texts(chunks, embeddings)
    return vectorstore

# 初始化聊天记录
if "messages" not in st.session_state:
    st.session_state.messages = []

# 展示历史记录
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 如果用户上传了文件，就开始处理
if uploaded_file:
    # 如果还没处理过这个文件，就建库并提示
    if "vectorstore" not in st.session_state:
        with st.spinner("🔍 正在解析 PDF 并构建向量库，请稍等..."):
            st.session_state.vectorstore = process_pdf(uploaded_file)
        st.success("✅ 知识库构建完成！可以开始提问了。")

    # 聊天输入框
    if prompt := st.chat_input("请输入关于 PDF 的问题..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("AI 正在查阅文档..."):
                # 1. 检索
                docs = st.session_state.vectorstore.similarity_search(prompt, k=2)
                context = "\n---\n".join([d.page_content for d in docs])
                
                # 2. 拼 Prompt
                messages = [
                    {"role": "system", "content": f"请根据以下资料回答。找不到就回答不知道。\n【资料】：\n{context}"}
                ]
                for m in st.session_state.messages[-4:]:
                    messages.append(m)

                # 3. 调 API
                url = "https://api.deepseek.com/chat/completions"
                headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
                data = {"model": "deepseek-chat", "messages": messages}
                
                res = requests.post(url, headers=headers, json=data)
                answer = res.json()["choices"][0]["message"]["content"]
                
                st.markdown(answer)
                st.caption(f"📚 引用资料：\n{context[:100]}...")
                st.session_state.messages.append({"role": "assistant", "content": answer})
else:
    st.info("👈 请先在左侧边栏上传一份 PDF 文档。")