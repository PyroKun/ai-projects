# 🤖 企业级 AI 知识库问答系统 (RAG-based QA)

这是一个基于 **FastAPI + Streamlit + DeepSeek + Docker** 构建的轻量级 RAG（检索增强生成）应用。支持上传自定义文本文档，并能基于文档内容进行准确问答与引用溯源。

## ✨ 核心特性
- **前后端分离**：FastAPI 提供后端接口，Streamlit 提供可视化聊天界面。
- **动态知识库**：支持在网页端直接上传 `.txt` 文件进行问答。
- **防幻觉机制**：通过 Prompt 强约束，遇到知识库外的问题能准确拒答。
- **容器化部署**：提供 `Dockerfile`，一条命令即可在任何环境运行。

## 📊 量化指标（基于 5 题内部测试集）
- **检索命中率**：100% (4/4)
- **未知问题拒答率**：100% (1/1)
- **幻觉率**：0%

*(详细测试记录与 BadCase 分析请见 `11-zero-base/评测记录.md`)*

## 🚀 快速启动 (Quick Start)

### 1. 克隆项目
```bash
git clone https://github.com/ProKun/ai-projects.git
cd ai-projects/11-zero-base

## 🌐 在线体验 (Live Demo)
👉 **点击这里直接体验：** [https://ai-projects-r8wreetahdybf88egptnzh.streamlit.app/](https://ai-projects-r8wreetahdybf88egptnzh.streamlit.app/)

*(注：请体验“年假有几天？”、“病假工资怎么发？”等内部制度问答。)*
