# -*- coding: utf-8 -*-
"""
文件名：pricing/review_generator.py
状态：LangChain 改造版 (Phase 1)
功能：利用 LangChain 调用 Qwen-Plus 生成专家点评
"""

import os
from dotenv import load_dotenv

# 1. 导入 LangChain 的核心组件
from langchain_community.chat_models import ChatTongyi  # 通义千问的模型包装器
from langchain_core.prompts import ChatPromptTemplate  # 聊天提示词模板
from langchain_core.output_parsers import StrOutputParser  # 字符串输出解析器 (把对象转成纯文本)

# 加载环境变量
load_dotenv()


def generate_expert_review(brand, model, condition_score, price_low, price_high, base_damage, edge_damage):
    """
    生成专家点评的主函数 (LangChain 版)
    """

    # --- A. 准备 API Key ---
    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("SNOWBOARD_API_KEYS")
    if not api_key:
        return "（系统提示：API Key 未配置，无法生成点评）"

    # --- B. 数据清洗 (保持原有逻辑) ---
    if model is None:
        model = "UNKNOWN"
    m = str(model).upper()
    b = str(brand).upper()

    # --- C. 风格推断逻辑 (保持原有逻辑，因为这是业务规则) ---
    style_hint = "全能/综和"
    style_keywords = ""

    if any(k in m for k in ["DOA", "EVIL", "HUCK", "BOX", "PARK", "TWIN"]):
        style_hint = "【公园/道具/街头】"
        style_keywords = "弹性、容错率、道具、跳台、抽板"
    elif any(k in m for k in ["DESPERADO", "FC", "CT", "TYPE", "TI", "SG"]):
        style_hint = "【硬核刻滑/竞速】"
        style_keywords = "抓地力、稳定性、切雪、过弯、G力"
    elif any(k in m for k in ["011", "RICE", "D4", "GT", "SPREAD"]):
        style_hint = "【日系平花/黄油】"
        style_keywords = "软弹、只有板腰硬、平地转圈"
    elif any(k in m for k in ["ORCA", "FLAGSHIP", "HOVER", "JONES", "GENTEM"]):
        style_hint = "【粉雪/野雪/大山】"
        style_keywords = "浮力、通过性、树林、深雪、冲浪感"

    # 动态指令构建
    model_instruction = ""
    if m in ["UNKNOWN", "未知型号", "NONE", "NULL", ""]:
        model_instruction = f"注意：看不清型号，请重点评价【{b}】品牌的保值率和当前的【成色】，别瞎编型号。"
    else:
        model_instruction = f"这是典型的 {style_hint} 风格雪板（型号：{m}）。请务必使用该领域的行话（关键词：{style_keywords}）点评。"

    # ===========================================
    # 🔥 D. LangChain 核心实现 (核心变化点)
    # ===========================================

    # 1. 初始化模型 (ChatTongyi)
    # temperature=0.7 让点评稍微有点文采，不那么死板
    chat_model = ChatTongyi(
        model="qwen-plus",
        dashscope_api_key=api_key,
        temperature=0.7
    )

    # 2. 定义 Prompt 模板 (System + User)
    # 以前是 f-string 拼接，现在是结构化的 Template
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "你是一名有15年雪龄的滑雪装备鉴定师，人称“雪圈毒舌老炮”。你的说话风格专业、犀利、接地气。"),
        ("user", """
        请根据以下数据，写一段 100 字左右的二手交易点评。

        【检测数据】
        - 品牌：{brand}
        - 疑似型号：{model}
        - 风格定位：{style_hint}
        - 综合成色：{condition_score}/10
        - 板底情况：{base_damage}
        - 边刃情况：{edge_damage}
        - 估价区间：¥{price_low} - ¥{price_high}

        【特别指令】
        {model_instruction}

        【写作要求】
        1. 直击痛点：如果有伤，指出维修成本。
        2. 解释价格：告诉小白为什么值这个价。
        3. 购买建议：适合新手还是大神？
        """)
    ])

    # 3. 创建处理链 (LCEL: LangChain Expression Language)
    # 逻辑：Prompt模板 -> 模型 -> 文本解析器
    chain = prompt_template | chat_model | StrOutputParser()

    # 4. 执行链
    try:
        # invoke 会自动把字典里的变量填入模板，然后发给 AI
        result = chain.invoke({
            "brand": b,
            "model": m,
            "style_hint": style_hint,
            "condition_score": condition_score,
            "base_damage": base_damage,
            "edge_damage": edge_damage,
            "price_low": price_low,
            "price_high": price_high,
            "model_instruction": model_instruction
        })
        return result

    except Exception as e:
        print(f"LangChain 调用异常: {str(e)}")
        return "（专家正在滑雪，LangChain 连接断开...）"