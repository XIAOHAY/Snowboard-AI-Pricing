# -*- coding: utf-8 -*-
"""
文件名：app_ui_deploy.py
状态：最终修复版 (含自动密钥 + 手动纠错 + 聊天同步 + 矮人工匠动画)
"""
import streamlit as st
import pandas as pd
import os
import sys
import tempfile
import json
import time
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ==========================================
# 1. 核心逻辑直接导入
# ==========================================
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
# 2. 页面配置 & 密钥自动加载
# ==========================================
st.set_page_config(page_title="AI 雪板鉴定 Pro", page_icon="🏂", layout="wide")

st.title("🏂 AI 二手雪板智能定价系统 (Online Demo)")
st.caption("💡 这是一个在线演示版本，支持 AI 视觉鉴定、价格计算及多轮对话。")

with st.sidebar:
    st.title("🔧 配置")
    # 自动加载 Secrets
    if "DASHSCOPE_API_KEY" in st.secrets:
        st.success("✅ 云端密钥已自动加载")
        api_key = st.secrets["DASHSCOPE_API_KEY"]
    elif os.getenv("DASHSCOPE_API_KEY"):
        st.success("✅ 本地环境变量已加载")
        api_key = os.getenv("DASHSCOPE_API_KEY")
    else:
        api_key = st.text_input("请输入阿里云 DashScope API Key", type="password")
        if not api_key:
            st.warning("⚠️ 请输入 Key 继续")
            st.stop()

    os.environ["DASHSCOPE_API_KEY"] = api_key
    os.environ["SNOWBOARD_API_KEYS"] = api_key

# 初始化状态
if "current_data" not in st.session_state:
    st.session_state.current_data = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ==========================================
# 3. 核心功能区
# ==========================================
tab1, tab2 = st.tabs(["📷 鉴定与咨询", "ℹ️ 关于项目"])

with tab1:
    # --- A. 上传区 (无数据时显示) ---
    if not st.session_state.current_data:
        st.markdown("### 1️⃣ 上传照片")
        user_hint = st.text_input("💡 (选填) 线索提示", placeholder="例如：Gray Desperado...")
        uploaded_files = st.file_uploader("上传图片", type=['jpg', 'png'], accept_multiple_files=True)

        if st.button("🚀 开始分析", type="primary"):
            if uploaded_files:

                # ==================================================
                # 🎬 动画代码开始
                # ==================================================
                # ==================================================
                # 🎬 动画代码开始 (升级版：暗色磨砂弹窗)
                # ==================================================
                loading_placeholder = st.empty()

                # 定义 CSS 动画和 HTML 结构
                loading_html = """
                                <style>
                                    /* 1. 全屏遮罩 */
                                    .loading-overlay {
                                        position: fixed;
                                        top: 0;
                                        left: 0;
                                        width: 100vw;
                                        height: 100vh;
                                        background: rgba(0, 0, 0, 0.4);
                                        display: flex;
                                        justify-content: center;
                                        align-items: center;
                                        z-index: 99999;
                                    }

                                    /* 2. 核心弹窗 (性能优化版) */
                                    .glass-card {
                                        position: relative;
                                        width: 35vw;
                                        min-width: 320px;
                                        max-width: 500px;
                                        padding: 40px 20px;

                                        /* 🎨 优化：稍微降低模糊度以提升 FPS */
                                        background: rgba(30, 30, 30, 0.85); 
                                        backdrop-filter: blur(12px);  /* 从 20px 降到 12px */
                                        -webkit-backdrop-filter: blur(12px);

                                        border: 1px solid rgba(255, 255, 255, 0.15);
                                        border-radius: 20px;
                                        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);

                                        display: flex;
                                        flex-direction: column;
                                        align-items: center;
                                        color: #ffffff;
                                        font-family: sans-serif;
                                        text-align: center;
                                    }

                                    /* 3. 动画舞台 */
                                    .stage-container {
                                        position: relative;
                                        width: 300px;
                                        height: 300px;
                                        display: flex;
                                        justify-content: center;
                                        align-items: center;
                                        margin-bottom: 20px;
                                    }

                                    /* 4. 中心物体：雪板 */
                                    .center-obj {
                                        position: absolute;
                                        width: 110px;
                                        z-index: 10;
                                        /* 👇 你的 GitHub Raw 链接 */
                                        content: url('https://raw.githubusercontent.com/XIAOHAY/Snowboard-AI-Pricing/main/img/snowboard.png');
                                    }

                                    /* 5. 轨道容器 (🚀 GPU 加速核心) */
                                    .orbit-container {
                                        position: absolute;
                                        width: 100%;
                                        height: 100%;
                                        z-index: 20;

                                        /* 🚀 性能优化关键指令 */
                                        will-change: transform;
                                        transform: translateZ(0); 

                                        animation: orbit-spin 5s linear infinite; /* 稍微加快一点速度 (6s->5s) 也会感觉更流畅 */
                                    }

                                    /* 6. 矮人工匠 (🚀 GPU 加速核心) */
                                    .dwarf-artisan {
                                        position: absolute;
                                        top: 15px;
                                        left: 50%;
                                        width: 60px; 
                                        margin-left: -30px; 
                                        margin-top: 0px;

                                        /* 🚀 性能优化关键指令 */
                                        will-change: transform;
                                        transform: translateZ(0);
                                        backface-visibility: hidden; /* 防止旋转锯齿 */

                                        animation: counter-spin 5s linear infinite; /* 必须和轨道时间一致 */

                                        /* 👇 你的 GitHub Raw 链接 */
                                        content: url('https://raw.githubusercontent.com/XIAOHAY/Snowboard-AI-Pricing/main/img/dwarf.png'); 
                                    }

                                    /* 7. 文字提示 */
                                    .loading-text {
                                        font-size: 1.4rem;
                                        font-weight: bold;
                                        letter-spacing: 1px;
                                        margin-bottom: 8px;
                                        text-shadow: 0 2px 4px rgba(0,0,0,0.5);
                                    }

                                    .sub-text {
                                        font-size: 0.9rem;
                                        color: #dddddd;
                                        line-height: 1.4;
                                    }

                                    /* --- 关键帧 --- */
                                    @keyframes orbit-spin {
                                        0% { transform: rotate(0deg); }
                                        100% { transform: rotate(360deg); }
                                    }

                                    @keyframes counter-spin {
                                        0% { transform: rotate(0deg); }
                                        100% { transform: rotate(-360deg); }
                                    }
                                </style>

                                <div class="loading-overlay">
                                    <div class="glass-card">
                                        <div class="stage-container">
                                            <img class="center-obj">
                                            <div class="orbit-container">
                                                <img class="dwarf-artisan">
                                            </div>
                                        </div>
                                        <div class="loading-text">⚒️ 宗师鉴定中...</div>
                                        <div class="sub-text">AI 正在云端比对全球市场数据<br>请稍候片刻</div>
                                    </div>
                                </div>
                                """

                # 渲染动画
                loading_placeholder.markdown(loading_html, unsafe_allow_html=True)
                # ==================================================
                # 🎬 动画代码结束
                # ==================================================

                try:
                    # 1. 视觉分析
                    analysis_results = []
                    for uploaded_file in uploaded_files:
                        suffix = os.path.splitext(uploaded_file.name)[1]
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                            tmp.write(uploaded_file.read())
                            temp_path = tmp.name
                        try:
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
                            "edge_damage": final_analysis.get("edge_damage"),
                            "calculation_process": price_result.get("calculation_process", [])
                        }

                        # ✅ 分析完成，清空动画
                        loading_placeholder.empty()
                        st.rerun()
                    else:
                        loading_placeholder.empty()
                        st.error("未能识别图片内容")

                except Exception as e:
                    # ❌ 出错也要清空动画，否则用户会卡在遮罩里
                    loading_placeholder.empty()
                    st.error(f"运行出错: {e}")

    # --- B. 结果展示 & 交互区 (有数据时显示) ---
    else:
        data = st.session_state.current_data

        # 顶部导航栏
        col_back, col_space = st.columns([1, 5])
        with col_back:
            if st.button("⬅️ 测下一块"):
                st.session_state.current_data = None
                st.session_state.chat_history = []
                st.rerun()

        st.divider()
        st.success("✅ 鉴定完成")

        # 1. 价格看板
        c1, c2, c3 = st.columns(3)
        c1.metric("📉 最低", f"¥{data.get('price_low', 0)}")
        c2.metric("🏷️ 均价", f"¥{data.get('suggest_price', 0)}")
        c3.metric("📈 最高", f"¥{data.get('price_high', 0)}")

        st.info(f"🗣️ **专家点评**：{data.get('expert_review', '暂无')}")

        # ==========================================
        # 🔥 手动纠错区域
        # ==========================================
        st.markdown("---")
        with st.expander("🛠️ 识别错了？点这里修正品牌/型号", expanded=False):
            with st.form("fix_form"):
                col_a, col_b, col_c = st.columns(3)
                new_brand = col_a.text_input("品牌", value=data.get('brand', ''))
                new_model = col_b.text_input("型号", value=data.get('model', ''))
                new_score = col_c.slider("成色", 1.0, 10.0, float(data.get('condition_score', 8.0)))

                if st.form_submit_button("🔄 修正并重新估价"):
                    with st.spinner("正在基于新数据重新计算..."):
                        try:
                            # 1. 构造新的分析数据
                            new_analysis = {
                                "brand": new_brand,
                                "possible_model": new_model,
                                "condition_score": new_score,
                                "can_use": True,
                                "base_damage": data.get("base_damage", "用户修正"),
                                "edge_damage": data.get("edge_damage", "用户修正"),
                                "is_old_model": False
                            }

                            # 2. 调用定价引擎重算
                            new_price_res = estimate_secondhand_price(new_analysis)
                            p_low = new_price_res.get("price_low", 0)
                            p_high = new_price_res.get("price_high", 0)

                            # 3. 重新生成点评
                            new_review = generate_expert_review(
                                brand=new_brand,
                                model=new_model,
                                condition_score=new_score,
                                price_low=p_low, price_high=p_high,
                                base_damage=data.get("base_damage"),
                                edge_damage=data.get("edge_damage")
                            )

                            # 4. 更新 Session State
                            st.session_state.current_data.update({
                                "brand": new_brand,
                                "model": new_model,
                                "condition_score": new_score,
                                "price_low": p_low,
                                "price_high": p_high,
                                "suggest_price": int((p_low + p_high) / 2),
                                "expert_review": new_review,
                                "calculation_process": new_price_res.get("calculation_process", [])
                            })

                            # 5. 清空聊天记录
                            st.session_state.chat_history = []
                            st.toast("数据已修正，AI 记忆已更新！", icon="✅")
                            time.sleep(1)
                            st.rerun()

                        except Exception as e:
                            st.error(f"修正失败: {e}")

        # 3. 聊天互动区
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
                    # 把更新后的 data 传给 Chat Service
                    ans = get_follow_up_answer(prompt, data)
                    st.write(ans)
                    st.session_state.chat_history.append({"role": "assistant", "content": ans})

with tab2:
    st.markdown("""
    ### 👨‍💻 关于这个项目
    这是一个基于 **LangChain + Qwen-VL** 的多模态 AI 应用。
    """)