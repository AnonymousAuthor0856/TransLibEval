import os
import json
import logging
import re
import time
from openai import OpenAI

# 设置日志记录器
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("code_summary_log.txt", mode='w', encoding='utf-8')
    ]
)
logger = logging.getLogger()

# 初始化 OpenAI 客户端（替换为你的 API 密钥和基础 URL）
client = OpenAI(api_key="xxxx", base_url = 'xxxx')

# 定义输入文件夹路径和输出文件夹
input_folder = "python"  # Python 源文件所在的文件夹
output_folder = "GPT4o_python_sum"  # 生成的文本文件将保存在该文件夹

# 创建输出文件夹（如果不存在）
if not os.path.exists(output_folder):
    os.makedirs(output_folder)


# 定义用于生成伪代码的 prompt 模板
def generate_prompt(source_code, class_name):
    return f"""
    Please read the following source code for the class '{class_name}' and provide a step-by-step chain of thought that describes the logical flow and algorithmic steps. 

    Focus on the conceptual process rather than language-specific syntax. 
    Do not quote the exact source code.

    Class name: {class_name}. The Class name needs to appear

    Here is the code，which provides only a step-by-step chain of thought:
    {source_code}
    """

# 获取 Python 文件中的类名
def extract_class_name(source_code):
    # 匹配类定义，获取类名
    match = re.search(r'class\s+(\w+)', source_code)
    if match:
        return match.group(1)  # 返回第一个类的名字
    return "UnnamedClass"  # 如果没有找到类名，返回默认值


# 修改后的 API 调用函数
def analyze_code_with_gpt35(source_code, class_name, retries=5):
    prompt = generate_prompt(source_code, class_name)

    messages = [
        {"role": "system", "content": "You are a code analysis assistant that provides structured summaries."},
        {"role": "user", "content": prompt}
    ]

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",  # 使用 gpt-4o 模型
                messages=messages,
                temperature=0.01,
                top_p=0.95,
                timeout=60
            )
            summary = response.choices[0].message.content
            if summary:
                return summary.strip()
            logger.error(f"API returned empty response in attempt {attempt + 1}/{retries}")
        except Exception as e:
            logger.error(f"API request failed (attempt {attempt + 1}/{retries}): {str(e)}")
            if attempt < retries - 1:
                time.sleep(5)
        return None


# 以下部分保持不变
def process_python_file(python_file):
    base_name = os.path.basename(python_file).replace(".py", "")
    output_file_path = os.path.join(output_folder, f"{base_name}.txt")

    if os.path.exists(output_file_path):
        logger.info(f"File '{output_file_path}' already exists, skipping analysis.")
        return

    with open(python_file, 'r', encoding='utf-8') as file:
        source_code = file.read()

    # 提取类名
    class_name = extract_class_name(source_code)

    logger.debug(f"Analyzing file: {python_file}")
    summary = analyze_code_with_gpt35(source_code, class_name)

    if summary:
        with open(output_file_path, 'w', encoding='utf-8') as out_file:
            out_file.write(summary)
        logger.debug(f"Analysis result saved: {output_file_path}")
    else:
        logger.error(f"Analysis failed for file: {python_file}, skipping saving.")


def main():
    for python_file_name in os.listdir(input_folder):
        if not python_file_name.endswith(".py"):
            continue
        python_file_path = os.path.join(input_folder, python_file_name)
        logger.debug(f"Processing file: {python_file_path}")
        process_python_file(python_file_path)
    logger.info("All files processed, results saved.")


if __name__ == "__main__":
    main()
