import os
import json
import sqlite3
import requests
from dotenv import load_dotenv

# 读取环境变量中的 API Key
load_dotenv(dotenv_path="../.env") 
API_KEY = os.getenv("DEEPSEEK_API_KEY")

# 1. 模拟客户发来的一段话
customer_message = "你好，我是深圳深蓝科技的采购经理王强。我们公司大概 200 人，最近想给售后部门做一个 AI 客服知识库。预算大概 3 到 5 万，你们能做吗？"
print(f"💬 客户原话：{customer_message}\n")

# 2. 构造提示词，强制大模型输出 JSON 格式
prompt = f"""
你是一个专业的销售线索提取助手。请从以下客户对话中提取关键信息。
必须严格输出 JSON 格式，不要输出任何其他解释文字。

【要求输出的字段】：
- name: 客户姓名
- company: 公司名称
- intent_level: 意向等级（只能是 "高", "中", "低" 三者之一）
- requirement: 核心需求概括
- follow_up_status: 跟进状态（默认填 "未联系"）

【客户对话】：
{customer_message}
"""

url = "https://api.deepseek.com/chat/completions"
headers = {"Authorization": f"Bearer {API_KEY}"}
data = {
    "model": "deepseek-chat", 
    "messages": [{"role": "user", "content": prompt}],
    "response_format": {"type": "json_object"}  # 🌟 关键：强制大模型返回 JSON
}

print("🧠 正在让大模型分析客户意图并提取信息...")
res = requests.post(url, headers=headers, json=data).json()
ai_reply = res["choices"][0]["message"]["content"]
print(f"✅ AI 提取的原始结果：\n{ai_reply}\n")

# 3. 解析 JSON
try:
    customer_data = json.loads(ai_reply)
    
    # 4. 写入 SQLite 数据库
    conn = sqlite3.connect('crm_customers.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO customers (name, company, intent_level, requirement, follow_up_status)
    VALUES (?, ?, ?, ?, ?)
    ''', (
        customer_data.get("name"),
        customer_data.get("company"),
        customer_data.get("intent_level"),
        customer_data.get("requirement"),
        customer_data.get("follow_up_status", "未联系")
    ))
    
    conn.commit()
    conn.close()
    
    print("🎉 成功！客户信息已自动存入 CRM 数据库！")
    
except Exception as e:
    print(f"❌ 解析或入库失败：{e}")