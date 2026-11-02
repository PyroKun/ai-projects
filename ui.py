import streamlit as st
import requests

st.set_page_config(page_title="我的 AI 知识库", page_icon="🤖")
st.title("🤖 企业内部知识库助手")

# 🌟 新增：左侧边栏，用于上传文件
with st.sidebar:
    st.header("📂 上传你的知识库")
    uploaded_file = st.file_uploader("上传一个 TXT 文件", type=["txt"])
    if uploaded_file is not None:
        st.success("文件已加载！")

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
            try:
                # 🌟 新增：读取上传文件的内容
                document_content = ""
                if uploaded_file is not None:
                    document_content = uploaded_file.read().decode("utf-8")
                
                # 发给后端
                response = requests.post(
                    "http://127.0.0.1:8080/ask",
                    json={"question": prompt, "document_text": document_content},
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    st.markdown(data["answer"])
                    st.caption(f"📚 引用资料：{data['source']}")
                    st.session_state.messages.append({"role": "assistant", "content": data["answer"]})
                else:
                    st.error(f"接口报错，状态码：{response.status_code}")
            except Exception as e:
                st.error(f"连接失败：{e}")