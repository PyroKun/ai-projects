from pypdf import PdfReader
import re

def extract_text_from_pdf(pdf_path):
    print(f"⏳ 正在解析文档: {pdf_path}")
    reader = PdfReader(pdf_path)
    raw_text = ""
    
    # 1. 遍历每一页提取文本
    for page in reader.pages:
        text = page.extract_text()
        if text:
            raw_text += text + "\n"
            
    # 2. 企业级清洗（去乱码、去多余空格）
    # 去掉连续的空行
    clean_text = re.sub(r'\n\s*\n', '\n\n', raw_text)
    # 去掉特殊乱码字符（保留中文、英文、数字和常见标点）
    clean_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s，。！？：；,.!?:;()（）\-\n]', '', clean_text)
    
    print(f"✅ 解析完成！原始长度: {len(raw_text)}，清洗后长度: {len(clean_text)}")
    return clean_text

if __name__ == "__main__":
    try:
        text = extract_text_from_pdf("test.pdf")
        print("\n=== 前 300 个字符预览 ===")
        print(text[:300])
        print("=========================")
    except Exception as e:
        print(f"❌ 解析失败，请确保当前目录下有 test.pdf 文件。错误：{e}")