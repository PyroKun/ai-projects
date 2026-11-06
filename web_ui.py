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
st.set_page_config(page_title="企业级文档知识库", page_icon="📚", layout="wide")
st.title("📚 企业级多文档智能问答")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY") or (st.secrets["DEEPSEEK_API_KEY"] if "DEEPSEEK_API_KEY" in st.secrets else None)

# ---------------- 侧边栏：文档管理 ----------------
with st.sidebar:
    st.header("📂 知识库管理")
    st.info("💡 支持上传多个 PDF 或 TXT 文件，系统会自动合并建库。")
    
    # 核心升级：允许多文件上传，支持 PDF 和 TXT
    uploaded_files = st.file_uploader(
        "上传文档 (PDF 或 TXT)", 
        type=["pdf", "txt"], 
        accept_multiple_files=True
    )
    
    # 按钮：手动触发重建知识库
    if st.button("🔄 重新构建/更新知识库"):
        if uploaded_files:
            st.session_state.clear() # 清空旧记忆和旧库
            st.rerun() # 刷新页面重新建库
        else:
            st.warning("请先上传文件！")

    # 按钮：清空对话记录
    if st.button("🗑️ 清空聊天记录"):
        st.session_state.messages = []
        st.rerun()

# ---------------- 核心逻辑：多文件解析与建库 ----------------
@st.cache_resource(show_spinner=False)
def process_multiple_docs(files_data):
    all_chunks = []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
    
    for file_name, file_bytes in files_data:
        if file_name.endswith(".pdf"):
            reader = PdfReader(file_bytes)
            raw_text = "".join([page.extract_text() + "\n" for page in reader.pages if page.extract_text()])
        elif file_name.endswith(".txt"):
            raw_text = file_bytes.decode("utf-8")
        else:
            continue
            
        # 清洗
        clean_text = re.sub(r'\n\s*\n', '\n\n', raw_text)
        clean_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s，。！？：；,.!?:;()（）\-\n]', '', clean_text)
        
        # 切分并合并
        chunks = text_splitter.split_text(clean_text)
        all_chunks.extend(chunks)
        
    # 统一向量化建库
    embeddings = FastEmbedEmbeddings()
    return FAISS.from_texts(all_chunks, embeddings)

# ---------------- 主聊天界面 ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if uploaded_files:
    # 如果还没建库，则自动建库
    if "vectorstore" not in st.session_state:
        with st.spinner(f"🔍 正在解析 {len(uploaded_files)} 个文档并构建知识库..."):
            # 把上传的文件转成元组 (文件名, 字节流) 传给处理函数
            files_data = [(f.name, f.getvalue()) for f in uploaded_files]
            st.session_state.vectorstore = process_multiple_docs(files_data)
        st.success("✅ 知识库构建完成！你可以开始提问了。")

    if prompt := st.chat_input("请输入关于这些文档的问题..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("AI 正在多文档中检索..."):
                docs = st.session_state.vectorstore.similarity_search(prompt, k=2)
                context = "\n---\n".join([d.page_content for d in docs])
                
                messages = [{"role": "system", "content": f"请根据资料回答，找不到就说不知道。\n【资料】：\n{context}"}]
                for m in st.session_state.messages[-4:]:
                    messages.append(m)

                url = "https://api.deepseek.com/chat/completions"
                headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
                data = {"model": "deepseek-chat", "messages": messages}
                
                res = requests.post(url, headers=headers, json=data)
                answer = res.json()["choices"][0]["message"]["content"]
                
                st.markdown(answer)
                st.caption(f"📚 检索来源：\n{context[:100]}...")
                st.session_state.messages.append({"role": "assistant", "content": answer})
else:
    st.info("👈 请先在左侧上传 PDF 或 TXT 文档，系统会自动建立知识库。")