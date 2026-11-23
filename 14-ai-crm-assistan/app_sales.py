import streamlit as st
import requests
import os
import json
import sqlite3
import pandas as pd
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")
API_KEY = os.getenv("DEEPSEEK_API_KEY")

st.set_page_config(page_title="全链路智能销售CRM", page_icon="💼", layout="wide")

# 顶部指标看板（每次加载更新数据）
conn = sqlite3.connect('crm_customers.db')
cursor = conn.cursor()
# 自动升级一下数据库结构（加入更新时间的机制）
try:
    cursor.execute("ALTER TABLE customers ADD COLUMN update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    conn.commit()
except:
    pass # 已经存在则跳过

total_leads = pd.read_sql_query("SELECT count(*) as count FROM customers", conn)['count'][0]
high_intent = pd.read_sql_query("SELECT count(*) as count FROM customers WHERE intent_level='高'", conn)['count'][0]
today_new = pd.read_sql_query("SELECT count(*) as count FROM customers WHERE date(create_time)=date('now')", conn)['count'][0]
conn.close()

# 渲染顶部看板
st.title("💼 智能销售 CRM 管理系统")
col1, col2, col3 = st.columns(3)
col1.metric("📊 总客户线索", f"{total_leads} 家")
col2.metric("🔥 高意向客户", f"{high_intent} 家", "实时追踪")
col3.metric("✨ 今日新增", f"{today_new} 家")

tab1, tab2 = st.tabs(["💬 AI 销售智能助理 (客户端)", "📊 CRM 客户跟进看板 (后台端)"])

# ================= 界面 1：智能销售助手 =================
with tab1:
    col_chat, col_profile = st.columns([2, 1])
    
    with col_chat:
        st.subheader("与 AI 销售对话")
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("客户输入需求（如：我是深蓝科技王总，想要个知识库）"):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("AI 正在回复..."):
                    url = "https://api.deepseek.com/chat/completions"
                    headers = {"Authorization": f"Bearer {API_KEY}"}
                    messages = [{"role": "system", "content": "你是一个顶级AI销售。必须热情解答问题，并千方百计获取客户的姓名、公司、具体需求。"}]
                    for m in st.session_state.chat_history[-4:]:
                        messages.append(m)
                    
                    data = {"model": "deepseek-chat", "messages": messages}
                    res = requests.post(url, headers=headers, json=data).json()
                    answer = res["choices"][0]["message"]["content"]
                    st.markdown(answer)
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})

                    # 后台静默提取并显示在右侧
                    extract_prompt = f"提取客户信息，输出JSON字段: name, company, intent_level(高/中/低), requirement。未提及填'未知'。内容：{prompt}"
                    extract_data = {"model": "deepseek-chat", "messages": [{"role": "user", "content": extract_prompt}], "response_format": {"type": "json_object"}}
                    extract_res = requests.post(url, headers=headers, json=extract_data).json()
                    
                    try:
                        customer_info = json.loads(extract_res["choices"][0]["message"]["content"])
                        st.session_state.current_profile = customer_info # 实时存到 session 里展示
                        
                        if customer_info.get("name") != "未知" or customer_info.get("company") != "未知":
                            conn = sqlite3.connect('crm_customers.db')
                            cursor = conn.cursor()
                            cursor.execute('INSERT INTO customers (name, company, intent_level, requirement, follow_up_status) VALUES (?, ?, ?, ?, ?)', 
                                           (customer_info.get("name"), customer_info.get("company"), customer_info.get("intent_level"), customer_info.get("requirement"), "未联系"))
                            conn.commit()
                            conn.close()
                            st.toast("✅ 客户档案已极速录入 CRM", icon="🚀")
                    except:
                        pass
                        
    with col_profile:
        st.subheader("🪪 实时客户画像")
        if "current_profile" in st.session_state:
            st.json(st.session_state.current_profile)
        else:
            st.info("等待对话提取...")

# ================= 界面 2：CRM 客户管理 =================
with tab2:
    st.subheader("客户跟进台账")
    if st.button("🔄 刷新台账"):
        st.rerun()
        
    conn = sqlite3.connect('crm_customers.db')
    df = pd.read_sql_query("SELECT id, name, company, intent_level, requirement, follow_up_status, create_time FROM customers ORDER BY id DESC", conn)
    conn.close()
    
    if not df.empty:
        # 使用 st.data_editor 让销售可以手动修改跟进状态
        edited_df = st.data_editor(df, use_container_width=True, hide_index=True, 
                                   column_config={
                                       "follow_up_status": st.column_config.SelectboxColumn("跟进状态", options=["未联系", "跟进中", "已成交", "已流失"], required=True)
                                   })
        
        # 如果修改了状态，自动保存到数据库
        if st.button("💾 保存跟进状态"):
            conn = sqlite3.connect('crm_customers.db')
            cursor = conn.cursor()
            for index, row in edited_df.iterrows():
                cursor.execute("UPDATE customers SET follow_up_status = ? WHERE id = ?", (row['follow_up_status'], row['id']))
            conn.commit()
            conn.close()
            st.success("跟进状态已保存！")
    else:
        st.info("暂无客户，请去左侧接待客户。")