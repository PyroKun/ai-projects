import streamlit as st
import requests
import os
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_community.vectorstores import FAISS

st.set_page_config(page_title="AI 知识库", page_icon="🤖")
st.title("🤖 企业内部知识库助手")

# 🌟 关键：从 Streamlit 云端读取密钥
try:
    DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
except Exception:
    st.error("未配置 API Key，请在 Streamlit 后台设置。")
    st.stop()

# 加载向量库 (确保 faiss_index 文件夹和 ui.py 在同一个目录)
@st.cache_resource
def load_vectorstore():
    embeddings = FastEmbedEmbeddings()
    return FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)

vectorstore = load_vectorstore()

# 初始化聊天记录
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("请输入你的问题..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("AI 正在查阅资料..."):
            # 1. 检索
            docs = vectorstore.similarity_search(prompt, k=1)
            best_chunk = docs[0].page_content
            
            # 2. 调大模型
            url = "https://api.deepseek.com/chat/completions"
            headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
            data = {"model": "deepseek-chat", "messages": [{"role": "user", "content": f"根据资料回答：{best_chunk}\n问题：{prompt}"}]}
            
            res = requests.post(url, headers=headers, json=data)
            answer = res.json()["choices"][0]["message"]["content"]
            
            st.markdown(answer)
            st.caption(f"📚 引用资料：{best_chunk}")
            st.session_state.messages.append({"role": "assistant", "content": answer})