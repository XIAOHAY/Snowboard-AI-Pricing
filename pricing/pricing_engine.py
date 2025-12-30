# -*- coding: utf-8 -*
# -*- coding: utf-8 -*-
"""
文件名：pricing_engine.py

【功能说明】
这是整个项目中“最有价值”的模块之一。

它负责：
- 接收视觉分析阶段输出的结构化结果（dict）
- 根据规则进行二手雪板价格估算
- 给出价格区间 + 定价依据（给雪友看的解释）

⚠️ 重要原则：
1. 不调用任何大模型
2. 不处理图片
3. 不关心 JSON 清洗
4. 只做“价值判断”
"""

# ===============================
# 1. 标准库导入
# ===============================
import json
import os
from typing import Dict, Any


# ===============================
# 2. 加载品牌基准价配置
# ===============================

def load_brand_price_table() -> Dict[str, int]:
    """
    从 data/brand_price.json 中加载品牌基准价表

    返回示例：
    {
        "ROSSIGNOL": 1600,
        "BURTON": 1800,
        "SALOMON": 1500,
        "UNKNOWN": 1200
    }
    """

    # pricing_engine.py 所在目录
    current_dir = os.path.dirname(__file__)

    # 项目根目录
    project_root = os.path.abspath(os.path.join(current_dir, ".."))

    # data/brand_price.json 的完整路径
    price_file_path = os.path.join(project_root, "data", "brand_price.json")

    if not os.path.exists(price_file_path):
        raise FileNotFoundError(f"品牌价格配置文件不存在：{price_file_path}")

    with open(price_file_path, "r", encoding="utf-8") as f:
        return json.load(f)


# 启动时加载一次（避免每次定价都读文件）
BRAND_BASE_PRICE = load_brand_price_table()


# ===============================
# 3. 成色评分 → 折价系数
# ===============================

def condition_factor(score: int) -> float:
    """
    根据成色评分（1-10）返回折价系数

    score: 1~10，来自视觉分析模型
    """

    if score >= 9:
        return 0.90
    elif score >= 7:
        return 0.75
    elif score >= 5:
        return 0.60
    else:
        return 0.40


# ===============================
# 4. 核心函数：二手雪板价格估算
# ===============================

def estimate_secondhand_price(analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    二手雪板价格估算主函数

    参数：
    analysis_result: 来自 qwen_vl 的结构化分析结果 dict

    返回：
    一个“可直接给用户 / Agent / 前端使用”的定价结果
    """

    # ---------------------------
    # 4.1 读取分析结果中的关键字段
    # ---------------------------
    brand = analysis_result.get("brand", "UNKNOWN")
    condition_score = analysis_result.get("condition_score", 5)
    can_use = analysis_result.get("can_use", False)

    # ---------------------------
    # 4.2 不可使用的兜底逻辑（硬规则）
    # ---------------------------
    if not can_use:
        return {
            "currency": "CNY",
            "price_low": 0,
            "price_high": 0,
            "confidence": 0.95,
            "suggestion": "不建议交易",
            "pricing_reason": [
                "雪板存在影响正常使用的问题",
                "维修成本可能高于其二手价值"
            ]
        }

    # ---------------------------
    # 4.3 获取品牌基准价
    # ---------------------------
    base_price = BRAND_BASE_PRICE.get(brand, BRAND_BASE_PRICE.get("UNKNOWN", 1200))

    # ---------------------------
    # 4.4 根据成色计算折后中心价
    # ---------------------------
    factor = condition_factor(condition_score)
    center_price = base_price * factor

    # ---------------------------
    # 4.5 生成价格区间（±15%）
    # ---------------------------
    price_low = int(center_price * 0.85)
    price_high = int(center_price * 1.15)

    # ---------------------------
    # 4.6 可信度估计（非常朴素，但可解释）
    # ---------------------------
    confidence = round(0.5 + condition_score * 0.05, 2)
    confidence = min(confidence, 0.9)

    # ---------------------------
    # 4.7 给雪友看的“定价解释”
    # ---------------------------
    pricing_reason = [
        f"品牌：{brand}（基准价约 ¥{base_price}）",
        f"成色评分：{condition_score}/10",
        "雪板功能正常，可继续使用"
    ]

    # ---------------------------
    # 4.8 最终返回结构
    # ---------------------------
    return {
        "currency": "CNY",
        "price_low": price_low,
        "price_high": price_high,
        "confidence": confidence,
        "suggestion": "合理出价区间",
        "pricing_reason": pricing_reason
    }
