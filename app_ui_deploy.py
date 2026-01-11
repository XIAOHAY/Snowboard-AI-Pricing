# -*- coding: utf-8 -*-
"""
文件名：app_ui_deploy.py
状态：最终演示版 (含自动密钥 + 手动纠错 + 聊天同步 + 矮人工匠动画 + 预设演示案例)
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

st.title("🏂 AI 二手雪板智能定价系统 (Demo)")
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
# 3. 定义通用的加载动画 HTML (复用)
# ==========================================
LOADING_HTML = """
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

    /* 2. 核心弹窗 */
    .glass-card {
        position: relative;
        width: 35vw;
        min-width: 320px;
        max-width: 500px;
        padding: 40px 20px;
        background: rgba(30, 30, 30, 0.85); 
        backdrop-filter: blur(12px);
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
        width: 270px;
        height: 370px;
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
        content: url('https://raw.githubusercontent.com/XIAOHAY/Snowboard-AI-Pricing/main/img/snowboard.png');
    }

    /* 5. 轨道容器 */
    .orbit-container {
        position: absolute;
        width: 100%;
        height: 100%;
        z-index: 20;
        will-change: transform;
        transform: translateZ(0); 
        animation: orbit-spin 5s linear infinite;
    }

    /* 6. 矮人工匠 */
    .dwarf-artisan {
        position: absolute;
        top: 15px;
        left: 50%;
        width: 80px; 
        margin-left: -40px; 
        will-change: transform;
        transform: translateZ(0);
        backface-visibility: hidden;
        animation: counter-spin 5s linear infinite;
        content: url('https://raw.githubusercontent.com/XIAOHAY/Snowboard-AI-Pricing/main/img/dwarf.png'); 
    }

    /* 7. 文字 */
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

    @keyframes orbit-spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    @keyframes counter-spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(-360deg); } }
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

# ==========================================
# 4. 核心功能区
# ==========================================
tab1, tab2 = st.tabs(["📷 鉴定与咨询", "ℹ️ 关于项目"])

with tab1:
    loading_placeholder = st.empty()

    # --- A. 上传区 (无数据时显示) ---
    if not st.session_state.current_data:
        st.markdown("### 1️⃣ 上传照片")
        user_hint = st.text_input("💡 (选填) 线索提示", placeholder="例如：Gray Desperado...")
        uploaded_files = st.file_uploader("上传图片", type=['jpg', 'png'], accept_multiple_files=True)

        if st.button("🚀 开始分析", type="primary"):
            if uploaded_files:
                # 播放动画
                loading_placeholder.markdown(LOADING_HTML, unsafe_allow_html=True)
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
                        loading_placeholder.empty()
                        st.rerun()
                    else:
                        loading_placeholder.empty()
                        st.error("未能识别图片内容")

                except Exception as e:
                    loading_placeholder.empty()
                    st.error(f"运行出错: {e}")

        # ==========================================
        # ⚡️ 演示案例区域 (新增)
        # ==========================================
        st.markdown("---")
        st.markdown("### ⚡️ 没有照片？一键体验演示用例")
        st.caption("点击下方按钮，体验 AI 对不同成色雪板的精准识别与定价。")

        # 1. 定义演示配置字典
        # 请确保你的项目根目录下有 examples 文件夹，并放入对应的图片
        DEMO_CASES = {
            "demo_good": {
                "label": "✨ 挑战：热门保值神板",
                "path": "./examples/sample_good.jpg",
                "caption": "案例A: 准新 Burton Custom",
                "force_brand": "BURTON",  # 强制修正品牌
                "force_model": "CUSTOM",  # 强制修正型号
                "hint": "Burton Custom 2024"  # 给 AI 的提示
            },
            "demo_bad": {
                "label": "🥊 挑战：识别严重损伤",
                "path": "./examples/sample_bad.jpg",
                "caption": "案例B: 板底严重划痕",
                "force_brand": "CAPITA",
                "force_model": "DOA",
                "hint": "Capita DOA, has heavy scratch"
            },
            "demo_old": {
                "label": "🔍 挑战：鉴定日系老款",
                "path": "./examples/sample_old.jpg",
                "caption": "案例C: Gray 老款",
                "force_brand": "GRAY",
                "force_model": "DESPERADO (OLD)",
                "hint": "Gray Desperado Ti Type-R"
            }
        }


        # 2. 定义演示运行函数
        def run_demo_analysis(case_key):
            cfg = DEMO_CASES[case_key]
            image_path = cfg["path"]

            # 播放动画
            loading_placeholder.markdown(LOADING_HTML, unsafe_allow_html=True)

            try:
                # 调用 AI (真实分析损伤/成色)
                res = analyze_snowboard_image(image_path, user_hint=cfg["hint"])

                # 🔥 关键：强制修正品牌和型号 (Binding Logic)
                # 这样即使 AI 没认出 Logo，定价逻辑也绝对准确
                res["brand"] = cfg["force_brand"]
                res["possible_model"] = cfg["force_model"]

                # 后续流程完全复用
                analysis_results = [res]

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
                        "calculation_process": price_result.get("calculation_process", []),
                        # 记录演示图片路径，用于结果页回显
                        "demo_image_path": image_path
                    }
                    loading_placeholder.empty()
                    st.rerun()
            except Exception as e:
                loading_placeholder.empty()
                st.error(f"演示案例运行失败: {e} (请检查 examples 文件夹下是否有对应图片)")


        # 3. 渲染演示按钮
        dc1, dc2, dc3 = st.columns(3)

        # 只有当文件存在时才渲染，防止报错
        if os.path.exists("./examples/sample_good.jpg"):
            with dc1:
                st.image(DEMO_CASES["demo_good"]["path"], use_column_width=True)
                if st.button(DEMO_CASES["demo_good"]["label"], use_container_width=True):
                    run_demo_analysis("demo_good")

        if os.path.exists("./examples/sample_bad.jpg"):
            with dc2:
                st.image(DEMO_CASES["demo_bad"]["path"], use_column_width=True)
                if st.button(DEMO_CASES["demo_bad"]["label"], use_container_width=True):
                    run_demo_analysis("demo_bad")

        if os.path.exists("./examples/sample_old.jpg"):
            with dc3:
                st.image(DEMO_CASES["demo_old"]["path"], use_column_width=True)
                if st.button(DEMO_CASES["demo_old"]["label"], use_container_width=True):
                    run_demo_analysis("demo_old")


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

        # 🔥 如果是演示模式，回显原始图片方便对比
        if "demo_image_path" in data:
            with st.expander("📷 查看原始图片 (点击展开)", expanded=True):
                c_img, c_info = st.columns([1, 2])
                with c_img:
                    st.image(data["demo_image_path"], use_column_width=True)
                with c_info:
                    st.markdown(f"**AI 识别重点：**\n\n"
                                f"- 品牌：`{data.get('brand')}`\n"
                                f"- 损伤检测：`{data.get('base_damage')}`\n"
                                f"- 成色评分：`{data.get('condition_score')}`")

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