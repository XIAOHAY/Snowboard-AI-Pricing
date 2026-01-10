# -*- coding: utf-8 -*
# utils/analysis_merge.py
from typing import List, Dict, Any
from collections import Counter


def merge_analysis_results(
        analysis_list: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    将多张图片的分析结果融合成一个最终分析结果
    改进点：自动剔除 UNKNOWN 干扰，优先采信有效品牌
    """

    valid_brands = []  # 只存有效的品牌
    scores = []
    base_damages = []
    edge_damages = []
    can_use_list = []

    # 定义哪些词会被视为“没识别出来”
    IGNORE_KEYWORDS = {"UNKNOWN", "NULL", "NONE", "未知", ""}

    for item in analysis_list:
        # --- 1. 品牌提取逻辑优化 ---
        raw_brand = str(item.get("brand", "")).strip().upper()

        # 只有当它不在排除名单里，才算一票
        if raw_brand and raw_brand not in IGNORE_KEYWORDS:
            valid_brands.append(raw_brand)

        # --- 2. 收集分数 ---
        # 只有数字才算数
        if isinstance(item.get("condition_score"), (int, float)):
            scores.append(item["condition_score"])

        # --- 3. 收集损伤描述 ---
        if item.get("base_damage"):
            base_damages.append(item["base_damage"])
        if item.get("edge_damage"):
            edge_damages.append(item["edge_damage"])

        # --- 4. 可用性 ---
        if item.get("can_use") is not None:
            can_use_list.append(item["can_use"])

    # ===============================
    # 融合决策
    # ===============================

    # 1. 品牌：优先取出现最多的“有效品牌”
    if valid_brands:
        final_brand = Counter(valid_brands).most_common(1)[0][0]
    else:
        # 如果大家全是 UNKNOWN，那真没办法了
        final_brand = "UNKNOWN"

    # 2. 成色评分：取平均值
    final_score = round(sum(scores) / len(scores), 1) if scores else 5

    # 3. 损伤描述：去重合并
    # 过滤掉 "无" 之类的废话，只保留有意义的描述
    unique_base = set([d for d in base_damages if d not in IGNORE_KEYWORDS])
    final_base_damage = "；".join(unique_base) if unique_base else "未发现明显板底损伤"

    unique_edge = set([d for d in edge_damages if d not in IGNORE_KEYWORDS])
    final_edge_damage = "；".join(unique_edge) if unique_edge else "未发现明显边刃损伤"

    # 4. 是否可用：严格模式（只要有一张图说不能用，就预警）
    # 或者改为宽松模式： final_can_use = any(can_use_list)
    final_can_use = all(can_use_list) if can_use_list else True

    return {
        "brand": final_brand,
        "condition_score": final_score,
        "base_damage": final_base_damage,
        "edge_damage": final_edge_damage,
        "can_use": final_can_use,
        # 加上这个字段方便调试
        "overall_condition": f"基于{len(analysis_list)}张图片分析，综合评分 {final_score}"
    }