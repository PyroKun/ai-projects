import streamlit as st
import requests
import os
import json
import sqlite3
import pandas as pd
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_community.vectorstores import FAISS

load_dotenv(dotenv_path="../.env")
API_KEY = os.getenv("DEEPSEEK_API_KEY")

st.set_page_config(page_title="工业售后智能调度", page_icon="🏭", layout="wide")
st.title("🏭 智能制造售后排障与工单系统")

# 数据库初始化与升级
conn = sqlite3.connect('maintenance_tickets.db')
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_model TEXT, error_code TEXT, issue_desc TEXT, solution TEXT,
    urgency TEXT, status TEXT DEFAULT '待处理', create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')
try:
    cursor.execute("ALTER TABLE tickets ADD COLUMN urgency TEXT")
    conn.commit()
except:
    pass
conn.close()

@st.cache_resource
def load_manual():
    # 🌟 关键修复：动态获取当前脚本所在目录，再拼上文件名
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "equipment_manual.txt")
    
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=20)
    return FAISS.from_texts(text_splitter.split_text(text), FastEmbedEmbeddings())

vectorstore = load_manual()
tab1, tab2 = st.tabs(["🔧 客户报修端", "🛠️ 工程师调度中心"])

with tab1:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("设备故障报修")
        issue_input = st.text_area("请描述故障现象（如：YAG-300 冒烟报 E01）", height=150)
        if st.button("🚨 提交报修并呼叫 AI 专家", use_container_width=True):
            if issue_input:
                with st.spinner("AI 正在查阅手册并生成方案..."):
                    docs = vectorstore.similarity_search(issue_input, k=2)
                    context = "\n".join([d.page_content for d in docs])
                    prompt = f"依据手册：{context}。故障：{issue_input}。输出JSON格式：equipment_model, error_code, solution, urgency(紧急/普通)"
                    
                    url = "https://api.deepseek.com/chat/completions"
                    headers = {"Authorization": f"Bearer {API_KEY}"}
                    res = requests.post(url, headers=headers, json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}}).json()
                    try:
                        result = json.loads(res["choices"][0]["message"]["content"])
                        conn = sqlite3.connect('maintenance_tickets.db')
                        cursor = conn.cursor()
                        cursor.execute('INSERT INTO tickets (equipment_model, error_code, issue_desc, solution, urgency) VALUES (?, ?, ?, ?, ?)', 
                                       (result.get("equipment_model"), result.get("error_code"), issue_input, result.get("solution"), result.get("urgency")))
                        conn.commit()
                        conn.close()
                        st.success("✅ 报修成功！工单已派发至工程师中心。")
                        st.info(f"**AI 预诊断方案**：\n{result.get('solution')}")
                    except:
                        st.error("解析失败，请重试。")
    with col2:
        st.subheader("AI 诊断报告")
        if 'result' in locals():
            st.json(result)

with tab2:
    st.subheader("最新售后工单看板")
    if st.button("🔄 刷新工单列表"):
        st.rerun()
        
    conn = sqlite3.connect('maintenance_tickets.db')
    df = pd.read_sql_query("SELECT id, equipment_model, error_code, urgency, status, issue_desc FROM tickets ORDER BY id DESC", conn)
    conn.close()
    
    if not df.empty:
        edited_df = st.data_editor(df, use_container_width=True, hide_index=True, 
                                   column_config={
                                       "status": st.column_config.SelectboxColumn("工单状态", options=["待处理", "维修中", "已解决", "已挂起"], required=True)
                                   })
        
        if st.button("💾 更新工单状态"):
            conn = sqlite3.connect('maintenance_tickets.db')
            cursor = conn.cursor()
            for index, row in edited_df.iterrows():
                cursor.execute("UPDATE tickets SET status = ? WHERE id = ?", (row['status'], row['id']))
            conn.commit()
            conn.close()
            st.success("工单状态已同步！")
    else:
        st.info("暂无工单记录。")