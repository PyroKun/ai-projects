import os
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

class AskRequest(BaseModel):
    question: str
    document_text: str = ""  # 新增：接收前端传来的文档

@app.post("/ask")
def ask_ai(req: AskRequest):
    question = req.question
    text = req.document_text
    
    # 如果前端传了文档，用前端的；没传就用本地的
    if not text:
        with open("corpus.txt", "r", encoding="utf-8") as f:
            text = f.read()
            
    chunks = [c.strip() for c in text.split("\n\n") if c.strip()]
    
    # 极简检索
    best_chunk, max_score = "", -1
    for chunk in chunks:
        score = sum(1 for char in question if char in chunk)
        if score > max_score:
            max_score, best_chunk = score, chunk

    # 调大模型
    API_KEY = os.getenv("DEEPSEEK_API_KEY")
    # 如果你没配好 .env，下面这行换成你的真实 key
    # API_KEY = "sk-xxx"
    
    prompt = f"根据资料回答问题，不知道就说不知道。\n资料：{best_chunk}\n问题：{question}"
    url = "https://api.deepseek.com/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    data = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}]}
    
    response = requests.post(url, headers=headers, json=data)
    answer = response.json()["choices"][0]["message"]["content"]
    
    return {"answer": answer, "source": best_chunk}