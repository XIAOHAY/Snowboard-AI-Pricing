# -*- coding: utf-8 -*
# utils/analysis_merge.py
from typing import List, Dict, Any
from collections import Counter


def merge_analysis_results(
    analysis_list: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    将多张图片的分析结果融合成一个最终分析结果
    """

    brands = []
    scores = []
    base_damages = []
    edge_damages = []
    can_use_list = []

    for item in analysis_list:
        a = item

        if a.get("brand"):
            brands.append(a["brand"])

        if a.get("condition_score") is not None:
            scores.append(a["condition_score"])

        if a.get("base_damage"):
            base_damages.append(a["base_damage"])

        if a.get("edge_damage"):
            edge_damages.append(a["edge_damage"])

        if a.get("can_use") is not None:
            can_use_list.append(a["can_use"])

    # 1. 品牌：出现最多的
    final_brand = Counter(brands).most_common(1)[0][0] if brands else "unknown"

    # 2. 成色评分：平均值
    final_score = round(sum(scores) / len(scores), 1) if scores else None

    # 3. 损伤描述：合并文本
    final_base_damage = "；".join(set(base_damages)) if base_damages else "未发现明显板底损伤"
    final_edge_damage = "；".join(set(edge_damages)) if edge_damages else "未发现明显边刃损伤"

    # 4. 是否可用：只要有 False 就 False
    final_can_use = all(can_use_list) if can_use_list else True

    return {
        "brand": final_brand,
        "condition_score": final_score,
        "base_damage": final_base_damage,
        "edge_damage": final_edge_damage,
        "can_use": final_can_use
    }
