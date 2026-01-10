# -*- coding: utf-8 -*
# -*- coding: utf-8 -*-
"""
文件名：llm/chat_service.py
功能：基于鉴定结果的问答服务 (LangChain 实现)
"""
import os
from dotenv import load_dotenv
from langchain_community.chat_models import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()


def get_follow_up_answer(user_question: str, appraisal_context: dict):
    """
    用户追问处理函数
    :param user_question: 用户的具体问题 (例如：这就想卖2000？)
    :param appraisal_context: 之前鉴定生成的完整 JSON 数据 (作为 AI 的短期记忆)
    """

    # 1. 准备 API Key
    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("SNOWBOARD_API_KEYS")
    if not api_key:
        return "API Key 缺失，无法回复。"

    # 2. 初始化模型
    chat_model = ChatTongyi(
        model="qwen-plus",  # 用 Plus 模型保证对话逻辑更强
        dashscope_api_key=api_key,
        temperature=0.7
    )

    # 3. 将复杂的 JSON 上下文转化为自然语言摘要
    # 这一步是为了让 AI 更容易理解数据
    context_str = f"""
    【当前讨论的商品详情】
    - 品牌：{appraisal_context.get('brand', '未知')}
    - 型号：{appraisal_context.get('model', '未知')}
    - 成色评分：{appraisal_context.get('condition_score', 0)}/10
    - 估价范围：¥{appraisal_context.get('price_low', 0)} - ¥{appraisal_context.get('price_high', 0)}
    - 建议均价：¥{appraisal_context.get('suggest_price', 0)}
    - 板底损伤：{appraisal_context.get('base_damage', '无')}
    - 专家点评摘要：{appraisal_context.get('expert_review', '无')}
    """

    # 4. 定义 Prompt 模板
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
        你就是刚才给出估价报告的“雪圈毒舌老炮”。
        现在用户对你的估价或商品详情提出了疑问。

        请基于下方的【商品详情】进行回答。

        要求：
        1. 语气保持一致：专业、稍微带点傲娇、犀利。
        2. 严谨：如果用户问的问题在【商品详情】里找不到依据（比如问这板子是哪年生产的），就直说“看图看不出来，别难为我”。
        3. 捍卫你的估价：如果用户嫌贵或嫌便宜，你要根据成色和品牌解释原因。
        """),
        ("user", """
        【商品详情】：
        {context_str}

        【用户问题】：
        {question}
        """)
    ])

    # 5. 构建并执行链
    chain = prompt | chat_model | StrOutputParser()

    try:
        return chain.invoke({
            "context_str": context_str,
            "question": user_question
        })
    except Exception as e:
        return f"（老炮儿这会儿有点忙，没听清你说啥... 错误: {e}）"