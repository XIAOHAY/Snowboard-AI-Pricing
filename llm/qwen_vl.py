# -*- coding: utf-8 -*-
"""
文件名：llm/qwen_vl.py
功能：调用阿里云千问 VL 模型分析图片（含重试机制与型号识别）
状态：改进版 (支持用户线索注入)
"""
import os
import json
import time
import dashscope
from dashscope import MultiModalConversation
from dotenv import load_dotenv

# ===============================
# 1. 初始化配置
# ===============================
# 加载环境变量
load_dotenv()

# 获取并设置 API Key
api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    # 尝试读取 SNOWBOARD_API_KEYS (兼容处理)
    api_key = os.getenv("SNOWBOARD_API_KEYS")

if not api_key:
    # 这里为了防崩，如果没读到环境变量，可以打印警告而不是直接抛异常，或者保持原样
    # raise ValueError("错误：未找到环境变量 DASHSCOPE_API_KEY。请检查 .env 文件。")
    print("⚠️ 警告：未找到 DASHSCOPE_API_KEY，后续调用可能会失败。")

dashscope.api_key = api_key
print("【DEBUG】DashScope SDK 初始化成功")


# ===============================
# 2. 辅助工具函数
# ===============================
def clean_json_text(text: str) -> str:
    """清理大模型返回的 markdown 格式，提取纯 JSON 字符串"""
    if not text:
        return ""
    text = text.strip()
    # 去掉 markdown 的代码块标记
    if text.startswith("```"):
        text = text.replace("```json", "")
        text = text.replace("```", "")
    return text.strip()


# ===============================
# 3. 定义 Prompt (提示词)
# ===============================
# 修改 llm/qwen_vl.py 中的 DEFAULT_PROMPT

DEFAULT_PROMPT = """
你是一名极其严苛的二手滑雪板鉴定专家。你的任务是根据图片客观描述损伤，并依据严格标准进行评分。
【重要提示】
1. 图片中可能包含竖排、旋转或艺术字体的 LOGO，请仔细辨认。
2. **注意区分通用词与品牌**：例如 "GRAY", "RIDE", "SIGNAL", "YES", "FLOW" 在这里是【品牌名】，而不是普通单词。
3. 请忽略水印文字（如“闲鱼”、“小红书”等）。

【已知品牌列表参考】
BURTON, SALOMON, CAPITA, NITRO, K2, RIDE, ROME SDS, JONES, LIB TECH, GNU, 
GRAY, OGASAKA, BC STREAM, MOSS, GENTEMSTICK, YONEX, 011 ARTISTIC, RICE28,
BATALEON, LOBSTER, ARBOR, DC, HEAD, FLOW, FLUX, UNION, NIDECKER, YES,
NOBADAY, VECTOR, REV, TERROR.
【第一步：强制视觉推理】
在输出 JSON 之前，你必须先在心中（或作为"thinking"字段）确认以下细节：
1. **板面 (Top sheet)**：是否有边缘崩裂(Chipping)？固定器安装区是否有压痕？
2. **板底 (Base)**：是否有露芯深划痕(Core Shot)？还是仅仅是发丝痕(Hairline)？
3. **板刃 (Edge)**：是否有断裂？是否有锈迹（浮锈还是腐蚀）？

【第二步：严格评分标准 (Rubric)】
请完全按照以下标准打分，禁止自由发挥：
- **9-10分**：充新。仅有极其轻微的使用痕迹，无肉眼可见划痕。
- **7-8分**：良好。板面有少量轻微划痕，板刃无锈或仅有浮锈，板底无深伤。
- **5-6分**：伊拉克成色。板面边缘有崩裂，板底有明显划痕但未漏芯，板刃有锈。
- **1-4分**：报废。板刃断裂、板底漏芯、板层开裂。

【第三步：输出格式】
请输出且仅输出以下 JSON 格式：
{
  "reasoning": "一句话描述你看到的损伤证据（例如：板头左侧有明显的边缘崩裂，板底有两条浅划痕）",
  "brand": "品牌英文大写 (例如 BURTON)",
  "possible_model": "型号猜测",
  "condition_score": "1-10的整数",
  "base_damage": "板底具体损伤 (无/轻微/严重)",
  "edge_damage": "板刃具体损伤 (无/浮锈/腐蚀/断裂)",
  "can_use": true
  "is_old_model": true 或 false (判断依据：板面设计风格是否陈旧，或者明显的旧款LOGO。如果无法判断，返回 false),
}
"""



# ===============================
# 4. 核心函数：分析图片
# ===============================
def analyze_snowboard_image(image_path: str, user_hint: str = None) -> dict:
    """
    调用千问 VL 模型分析雪板图片
    :param image_path: 图片路径
    :param user_hint: 用户提供的线索 (可选)
    """

    # 🔥 动态构建 Prompt：如果用户给了线索，拼接到 Prompt 里
    final_prompt = DEFAULT_PROMPT
    if user_hint and user_hint.strip():
        final_prompt += f"""
        \n【用户额外提示】
        用户指出这张图片中的雪板可能是："{user_hint}"。
        请以此为重要线索，优先在画面中验证该品牌或型号特征。
        如果画面明显与用户提示不符，请忽略提示，以画面为准。
        """

    max_retries = 3  # 最大重试次数
    retry_delay = 2  # 每次失败等待秒数

    last_error = None
    response = None

    # --- 开始重试循环 ---
    for attempt in range(max_retries):
        try:
            print(f"🚀 正在调用阿里云视觉模型 (第 {attempt + 1} 次尝试)...")

            # 兼容 Windows 路径
            local_file_path = f"file://{image_path}" if not image_path.startswith("file://") else image_path

            response = MultiModalConversation.call(
                model="qwen-vl-max",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"image": local_file_path},
                            {"text": final_prompt}  # 使用包含线索的 Prompt
                        ]
                    }
                ],
                # 🔥【核心修改】加上这两行参数，给视觉模型“降温”
                temperature = 0.01,  # 接近 0 表示极度理性，每次输出几乎一致
                top_p = 0.1,  # 限制它的发散思维，只选概率最高的词
            )

            # 检查 HTTP 状态码
            if response.status_code == 200:
                print("✅ 模型调用成功！")
                break  # 成功了就跳出循环
            else:
                error_msg = f"API错误码: {response.code} - {response.message}"
                print(f"⚠️ {error_msg}")
                raise RuntimeError(error_msg)

        except Exception as e:
            print(f"❌ 第 {attempt + 1} 次请求异常: {str(e)}")
            last_error = e
            if attempt < max_retries - 1:
                print(f"⏳ 等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
            else:
                print("💀 重试次数耗尽。")

    # --- 循环结束后的处理 ---

    # 如果最后一次 response 依然是空的或者失败
    if response is None or response.status_code != 200:
        # 为了不让程序崩掉，返回一个兜底的错误 JSON
        print(f"【严重错误】无法获取模型结果: {last_error}")
        return {
            "brand": "UNKNOWN",
            "possible_model": "UNKNOWN",
            "condition_score": 5,
            "can_use": True,
            "base_damage": "网络错误，无法分析",
            "error": "NETWORK_ERROR"
        }

    # 检查 output 字段
    if "output" not in response or not response.output.choices:
        return {
            "brand": "UNKNOWN",
            "error": "EMPTY_RESPONSE"
        }

    # 提取文本内容
    content_list = response.output.choices[0].message.content
    raw_text = ""

    for item in content_list:
        if "text" in item:
            raw_text += item["text"]

    # 清洗并解析 JSON
    clean_text = clean_json_text(raw_text)

    try:
        data = json.loads(clean_text)
        return data
    except Exception as e:
        print(f"【JSON解析失败】原始文本: {raw_text}")
        # 返回兜底数据
        return {
            "brand": "UNKNOWN",
            "possible_model": "UNKNOWN",
            "condition_score": 5,
            "can_use": True,
            "error": "JSON_PARSE_ERROR"
        }