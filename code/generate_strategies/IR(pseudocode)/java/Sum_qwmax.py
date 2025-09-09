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
input_folder = "java"  # Java 源文件所在的文件夹
output_folder = "qwmax_java_sum"  # 生成的文本文件将保存在该文件夹

# 创建输出文件夹（如果不存在）
if not os.path.exists(output_folder):
    os.makedirs(output_folder)


# 定义用于生成伪代码的 prompt 模板
def generate_prompt(source_code, class_name):
    return f"""

    Please analyze the following code and generate the corresponding pseudocode. The pseudocode should not reflect any specific language syntax or implementation details, and should focus solely on the core logic and steps of the algorithm. The pseudocode should be structured logically, describing the sequence of operations, decision-making processes, and function calls in a clear and understandable manner.

    Write only the pseudocode without any additional explanations or details.

    Class name: {class_name}. The Class name needs to appear

    Next, I will provide the source code; you must not directly mention the source code in your response:
    {source_code}
    """

# 获取 Java 文件中的类名
def extract_class_name(source_code):
    # 匹配 Java 类定义，获取类名
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
                model="qwen-max-2025-01-25",
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
def process_java_file(java_file):
    base_name = os.path.basename(java_file).replace(".java", "")
    output_file_path = os.path.join(output_folder, f"{base_name}.txt")

    if os.path.exists(output_file_path):
        logger.info(f"File '{output_file_path}' already exists, skipping analysis.")
        return

    with open(java_file, 'r', encoding='utf-8') as file:
        source_code = file.read()

    # 提取类名
    class_name = extract_class_name(source_code)

    logger.debug(f"Analyzing file: {java_file}")
    summary = analyze_code_with_gpt35(source_code, class_name)

    if summary:
        with open(output_file_path, 'w', encoding='utf-8') as out_file:
            out_file.write(summary)
        logger.debug(f"Analysis result saved: {output_file_path}")
    else:
        logger.error(f"Analysis failed for file: {java_file}, skipping saving.")


def main():
    for java_file_name in os.listdir(input_folder):
        if not java_file_name.endswith(".java"):
            continue
        java_file_path = os.path.join(input_folder, java_file_name)
        logger.debug(f"Processing file: {java_file_path}")
        process_java_file(java_file_path)
    logger.info("All files processed, results saved.")


if __name__ == "__main__":
    main()
