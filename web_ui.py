import streamlit as st
import requests
import os
import io
from dotenv import load_dotenv
from pypdf import PdfReader
import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_community.vectorstores import FAISS

load_dotenv()
st.set_page_config(page_title="企业级 AI 助手", page_icon="🤖", layout="wide")
st.title("🤖 企业级 AI 助手")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY") or (st.secrets["DEEPSEEK_API_KEY"] if "DEEPSEEK_API_KEY" in st.secrets else None)

# ---------------- 侧边栏：文档管理 ----------------
with st.sidebar:
    st.header("📂 知识库管理 (可选)")
    
    uploaded_files = st.file_uploader(
        "上传文档 (PDF 或 TXT)", 
        type=["pdf", "txt"], 
        accept_multiple_files=True
    )
    
    if st.button("🔄 重新构建知识库"):
        if uploaded_files:
            st.session_state.clear()
            st.rerun()
        else:
            st.warning("请先上传文件！")

    if st.button("🗑️ 清空聊天记录"):
        st.session_state.messages = []
        st.rerun()

# ---------------- 顶部状态栏：明确当前模式 ----------------
# 🌟 新增：根据是否上传文档，显示不同的状态横幅
if uploaded_files:
    st.success(f"📚 **当前模式：企业知识库问答**。AI 将优先基于您上传的 {len(uploaded_files)} 个文档进行回答。")
else:
    st.info("💬 **当前模式：通用 AI 聊天**。您可以自由提问。如需基于特定文档问答，请先在左侧上传文档。")

# ---------------- 解析与建库逻辑 ----------------
@st.cache_resource(show_spinner=False)
def process_multiple_docs(files_data):
    all_chunks = []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
    for file_name, file_bytes in files_data:
        if file_name.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file_bytes))
            raw_text = "".join([page.extract_text() + "\n" for page in reader.pages if page.extract_text()])
        elif file_name.endswith(".txt"):
            raw_text = file_bytes.decode("utf-8")
        else:
            continue
        clean_text = re.sub(r'\n\s*\n', '\n\n', raw_text)
        clean_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s，。！？：；,.!?:;()（）\-\n]', '', clean_text)
        all_chunks.extend(text_splitter.split_text(clean_text))
    embeddings = FastEmbedEmbeddings()
    return FAISS.from_texts(all_chunks, embeddings)

# ---------------- 主界面：聊天记录 ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------- 动态输入框提示 ----------------
# 🌟 新增：输入框文案切换
if uploaded_files:
    placeholder_text = "基于知识库提问（例如：请总结这份文档的核心要求）..."
else:
    placeholder_text = "通用聊天（例如：帮我写一段 Python 代码）..."

prompt = st.chat_input(placeholder_text)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("AI 正在思考..."):
            messages = []
            
            if uploaded_files:
                if "vectorstore" not in st.session_state:
                    with st.spinner(f"🔍 首次提问，正在解析文档并构建知识库..."):
                        files_data = [(f.name, f.getvalue()) for f in uploaded_files]
                        st.session_state.vectorstore = process_multiple_docs(files_data)
                
                docs = st.session_state.vectorstore.similarity_search(prompt, k=2)
                context = "\n---\n".join([d.page_content for d in docs])
                
                messages.append({"role": "system", "content": f"请优先根据以下资料回答。如果资料中没有，请结合你的常识回答，但不要编造资料内容。\n【资料】：\n{context}"})
                
                # 🌟 新增：气泡内的来源提示
                st.markdown("> 📚 **已接入本地知识库，正在检索并回答...**")
                
            else:
                messages.append({"role": "system", "content": "你是一个聪明、专业的 AI 助手，请直接回答用户的问题。"})

            for m in st.session_state.messages[-4:]:
                messages.append(m)

            url = "https://api.deepseek.com/chat/completions"
            headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
            data = {"model": "deepseek-chat", "messages": messages}
            
            res = requests.post(url, headers=headers, json=data)
            answer = res.json()["choices"][0]["message"]["content"]
            
            # 输出 AI 的回答
            st.markdown(answer)
            
            # 如果是知识库模式，把检索到的片段折叠展示出来
            if uploaded_files:
                with st.expander("查看检索到的原文片段"):
                    st.write(context)
                    
            st.session_state.messages.append({"role": "assistant", "content": answer})