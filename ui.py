import streamlit as st
import requests
import os
from dotenv import load_dotenv  # 🌟 补上了这个，用于读取本地 .env
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_community.vectorstores import FAISS

# 1. 优先加载本地 .env 文件
load_dotenv()

st.set_page_config(page_title="AI 知识库", page_icon="🤖")
st.title("🤖 企业内部知识库助手 (记忆版)")

# 2. 智能读取 API Key：云端优先读 st.secrets，本地读 .env
DEEPSEEK_API_KEY = None
try:
    # 尝试从 Streamlit 云端密钥读取
    DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
except Exception:
    # 如果云端没有，再去环境变量（.env）里找
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# 如果两头都找不到，报错停止
if not DEEPSEEK_API_KEY:
    st.error("❌ 未配置 API Key！请检查本地 .env 文件或云端 Secrets 设置。")
    st.stop()

# 3. 加载离线向量库（带有缓存，不用每次都重新加载）
@st.cache_resource
def load_vectorstore():
    embeddings = FastEmbedEmbeddings()
    return FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)

vectorstore = load_vectorstore()

# 4. 初始化聊天记录
if "messages" not in st.session_state:
    st.session_state.messages = []

# 5. 展示历史聊天记录
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 6. 接收用户输入
if prompt := st.chat_input("请输入你的问题..."):
    # 把用户的问题加入历史记录并显示
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("AI 正在查阅资料并思考..."):
            try:
                # 第一步：去向量库检索最相关的段落
                docs = vectorstore.similarity_search(prompt, k=1)
                best_chunk = docs[0].page_content
                
                # 第二步：构造发给大模型的消息列表（注入记忆和资料）
                api_messages = [
                    {"role": "system", "content": f"你是一个专业的企业助手。请严格根据以下参考资料回答问题。如果资料中找不到答案，请直接回答“资料中未提及”，绝对不要自己编造。\n\n【参考资料】：\n{best_chunk}"}
                ]
                
                # 把最近的 6 条历史聊天记录加进去（实现多轮对话记忆）
                for m in st.session_state.messages[-6:]:
                    api_messages.append(m)
                
                # 第三步：调用 DeepSeek 接口
                url = "https://api.deepseek.com/chat/completions"
                headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
                data = {
                    "model": "deepseek-chat",
                    "messages": api_messages
                }
                
                res = requests.post(url, headers=headers, json=data)
                answer = res.json()["choices"][0]["message"]["content"]
                
                # 第四步：显示回答，并存入历史记录
                st.markdown(answer)
                st.caption(f"📚 引用资料：{best_chunk}")
                st.session_state.messages.append({"role": "assistant", "content": answer})
                
            except Exception as e:
                st.error(f"出错了：{e}")