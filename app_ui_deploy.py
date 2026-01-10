# -*- coding: utf-8 -*
# -*- coding: utf-8 -*-
"""
文件名：app_ui_deploy.py
状态：部署专用版 (单体架构，无需启动 FastAPI 后端)
"""
import streamlit as st
import pandas as pd
import os
import sys
import tempfile
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ==========================================
# 1. 核心逻辑直接导入 (不再走 HTTP 请求)
# ==========================================
# 确保能找到本地模块
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from llm.qwen_vl import analyze_snowboard_image
    from utils.analysis_merge import merge_analysis_results
    from pricing.pricing_engine import estimate_secondhand_price
    from pricing.review_generator import generate_expert_review
    from llm.chat_service import get_follow_up_answer
except ImportError as e:
    st.error(f"模块导入失败: {e}. 请确保文件结构正确。")
    st.stop()

# ==========================================
# 2. 页面配置
# ==========================================
st.set_page_config(page_title="AI 雪板鉴定 Pro", page_icon="🏂", layout="wide")

st.title("🏂 AI 二手雪板智能定价系统 (Online Demo)")
st.info("💡 这是一个在线演示版本，数据存储在内存中，刷新页面会重置。")

# 侧边栏：输入 API Key (为了安全，不把 Key 写死在代码里)
with st.sidebar:
    st.title("🔧 配置")
    # 让面试官输入 Key，或者你可以后面在云端后台配置 Secrets
    user_api_key = st.text_input("请输入阿里云 DashScope API Key", type="password")
    if not user_api_key:
        st.warning("请先输入 API Key 才能使用功能。")
        st.stop()
    else:
        # 临时设置环境变量
        os.environ["DASHSCOPE_API_KEY"] = user_api_key
        os.environ["SNOWBOARD_API_KEYS"] = user_api_key

# 初始化 Session State
if "current_data" not in st.session_state:
    st.session_state.current_data = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ==========================================
# 3. 核心功能区
# ==========================================
tab1, tab2 = st.tabs(["📷 鉴定与咨询", "ℹ️ 关于项目"])

with tab1:
    # --- 上传区 ---
    if not st.session_state.current_data:
        st.markdown("### 1️⃣ 上传照片")
        user_hint = st.text_input("💡 (选填) 线索提示", placeholder="例如：Gray Desperado...")
        uploaded_files = st.file_uploader("上传图片", type=['jpg', 'png'], accept_multiple_files=True)

        if st.button("🚀 开始分析", type="primary"):
            if uploaded_files:
                with st.spinner('🤖 AI 正在云端分析 (可能需要十几秒)...'):
                    try:
                        # 1. 处理图片
                        analysis_results = []
                        for uploaded_file in uploaded_files:
                            # Streamlit Cloud 处理临时文件的方式
                            suffix = os.path.splitext(uploaded_file.name)[1]
                            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                                tmp.write(uploaded_file.read())
                                temp_path = tmp.name

                            try:
                                # 直接调用视觉函数
                                res = analyze_snowboard_image(temp_path, user_hint=user_hint)
                                analysis_results.append(res)
                            finally:
                                os.remove(temp_path)

                        # 2. 逻辑计算
                        if analysis_results:
                            final_analysis = merge_analysis_results(analysis_results)
                            price_result = estimate_secondhand_price(final_analysis)

                            p_low = price_result.get("price_low", 0)
                            p_high = price_result.get("price_high", 0)

                            expert_comment = generate_expert_review(
                                brand=final_analysis.get("brand"),
                                model=final_analysis.get("possible_model"),
                                condition_score=final_analysis.get("condition_score"),
                                price_low=p_low, price_high=p_high,
                                base_damage=final_analysis.get("base_damage"),
                                edge_damage=final_analysis.get("edge_damage")
                            )

                            # 存入 Session
                            st.session_state.current_data = {
                                "suggest_price": int((p_low + p_high) / 2),
                                "price_low": p_low,
                                "price_high": p_high,
                                "expert_review": expert_comment,
                                "brand": final_analysis.get("brand"),
                                "model": final_analysis.get("possible_model"),
                                "condition_score": final_analysis.get("condition_score"),
                                "base_damage": final_analysis.get("base_damage"),
                                "calculation_process": price_result.get("calculation_process", [])
                            }
                            st.rerun()
                        else:
                            st.error("未能识别图片内容")

                    except Exception as e:
                        st.error(f"运行出错: {e}")

    # --- 结果展示区 ---
    else:
        data = st.session_state.current_data

        if st.button("⬅️ 测下一块"):
            st.session_state.current_data = None
            st.session_state.chat_history = []
            st.rerun()

        st.divider()
        st.success("✅ 鉴定完成")
        c1, c2, c3 = st.columns(3)
        c1.metric("📉 最低", f"¥{data['price_low']}")
        c2.metric("🏷️ 均价", f"¥{data['suggest_price']}")
        c3.metric("📈 最高", f"¥{data['price_high']}")

        st.info(f"🗣️ **专家点评**：{data['expert_review']}")

        # 聊天区
        st.divider()
        st.subheader("💬 咨询专家")

        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        if prompt := st.chat_input("有疑问？问问老炮儿..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("思考中..."):
                    # 直接调用 Chat Service
                    ans = get_follow_up_answer(prompt, data)
                    st.write(ans)
                    st.session_state.chat_history.append({"role": "assistant", "content": ans})

with tab2:
    st.markdown("""
    ### 👨‍💻 关于这个项目
    这是一个基于 **LangChain + Qwen-VL** 的多模态 AI 应用。
    * **视觉层**: 识别雪板品牌、划痕、成色。
    * **逻辑层**: 基于市场数据的定价引擎。
    * **交互层**: 具备领域知识的 AI 问答助手。
    """)