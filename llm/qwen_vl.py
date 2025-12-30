# -*- coding: utf-8 -*-
"""
文件名：qwen_vl.py

功能：
使用阿里云 DashScope 的千问 VL（qwen-vl-plus）模型，
对二手雪板图片进行分析，并返回结构化 JSON 结果。
"""
import dashscope
import os

# ===== 千问 API Key 显式设置（开发阶段推荐）=====
dashscope.api_key = "sk-********"
# ================================================
print("【DEBUG】dashscope.api_key =", dashscope.api_key)

import json
from dashscope import MultiModalConversation


# ===============================
# 工具函数：清洗模型返回的 JSON
# ===============================
def clean_json_text(text: str) -> str:
    if not text:
        return ""

    text = text.strip()
    if text.startswith("```"):
        text = text.replace("```json", "")
        text = text.replace("```", "")

    return text.strip()


# ===============================
# Prompt（可集中管理）
# ===============================
DEFAULT_PROMPT = """
你是一名专业的二手滑雪装备鉴定师。
请根据雪板图片进行客观分析，并【严格】以 JSON 格式返回，不要输出多余文字。

返回字段必须完全一致：
{
  "brand": "品牌或 UNKNOWN",
  "possible_model": "可能型号或 UNKNOWN",
  "condition_score": "1-10 的整数，10 表示接近全新",
  "base_damage": "板底磨损情况描述",
  "edge_damage": "边刃情况描述",
  "overall_condition": "整体成色总结",
  "can_use": true 或 false
}
"""


# ===============================
# 核心函数：对外暴露的接口
# ===============================
def analyze_snowboard_image(image_path: str, prompt: str = DEFAULT_PROMPT) -> dict:
    """
    调用千问 VL 模型分析雪板图片

    参数：
        image_path (str): 雪板图片路径
        prompt (str): 分析 Prompt（可覆盖）

    返回：
        dict: 结构化分析结果
    """

    response = MultiModalConversation.call(
        model="qwen-vl-plus",
        messages=[
            {
                "role": "user",
                "content": [
                    {"image": image_path},
                    {"text": prompt}
                ]
            }
        ]
    )

    # ===== 防御式检查 =====
    if response is None:
        raise RuntimeError("DashScope 返回 None，请检查网络或 API Key")

    if "output" not in response or response["output"] is None:
        raise RuntimeError(f"模型未返回 output，response={response}")

    if "choices" not in response["output"]:
        raise RuntimeError(f"output 中不存在 choices，response={response}")

    # ===== 提取文本 =====
    content_list = response["output"]["choices"][0]["message"]["content"]

    raw_text = ""
    for item in content_list:
        if "text" in item:
            raw_text += item["text"]

    clean_text = clean_json_text(raw_text)

    try:
        return json.loads(clean_text)
    except Exception as e:
        raise ValueError(
            f"JSON 解析失败\n原始文本:\n{raw_text}\n\n清洗后:\n{clean_text}"
        ) from e
