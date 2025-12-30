# api/app.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from typing import List
import tempfile
import os
from utils.analysis_merge import merge_analysis_results
from pricing.pricing_engine import estimate_secondhand_price
from uuid import uuid4
from datetime import datetime
from fastapi import Depends
from api.auth import verify_api_key
from pydantic import BaseModel
from collections import defaultdict
import time

from llm.qwen_vl import analyze_snowboard_image
from pricing.pricing_engine import estimate_secondhand_price

# 限制每分钟请求次数
RATE_LIMIT = 5
TIME_WINDOW = 60  # 时间窗口：每分钟最大请求次数

# 用 defaultdict 来存储每个 API Key 的请求时间
api_request_count = defaultdict(list)


app = FastAPI()


class AnalyzeRequest(BaseModel):
    """
    请求体结构
    前端需要传什么数据，就在这里定义
    """
    image_path: str

@app.post("/analyze-multiple")
def analyze_multiple_images(
    images: List[UploadFile] = File(...),
    api_key: str = Depends(verify_api_key)
):
    analysis_results = []
    MAX_IMAGES = 5

    if len(images) > MAX_IMAGES:
        return {
            "success": False,
            "error": {
                "code": "TOO_MANY_IMAGES",
                "message": f"最多只能上传 {MAX_IMAGES} 张图片"
            }
        }
    MAX_IMAGE_SIZE_MB = 5
    for image in images:
        if image.size is not None:
            size_mb = image.size / (1024 * 1024)
            if size_mb > MAX_IMAGE_SIZE_MB:
                return {
                    "success": False,
                    "error": {
                        "code": "IMAGE_TOO_LARGE",
                        "message": f"单张图片不能超过 {MAX_IMAGE_SIZE_MB}MB"
                    }
                }

    # 1️⃣ 遍历每一张上传的图片
    for image in images:
        # 创建临时文件
        suffix = os.path.splitext(image.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(image.file.read())
            temp_path = tmp.name

        try:
            # 2️⃣ 调用你已有的图像分析函数
            result = analyze_snowboard_image(temp_path)
            analysis_results.append(result)
        finally:
            # 3️⃣ 删除临时文件
            os.remove(temp_path)

    # 4️⃣ 多图融合（你后面已经写好的）
    final_analysis = merge_analysis_results(analysis_results)

    # 5️⃣ 二手定价
    price_result = estimate_secondhand_price(final_analysis)

    # 6️⃣ 唯一 return（关键）
    return {
        "success": True,
        "request_id": str(uuid4()),
        "timestamp": datetime.now().isoformat(),

        # ====== 客户端真正关心的 ======
        "data": {
            "suggest_price": price_result.get("suggest_price"),
            "price_range": price_result.get("price_range"),
            "confidence": price_result.get("confidence"),
            "condition_level": final_analysis.get("overall_condition"),
            "can_use": final_analysis.get("can_use"),
            "brand": final_analysis.get("brand")
        },

        # ====== Debug / 内测信息 ======
        "debug": {
            "image_count": len(analysis_results),
            "analysis_results": analysis_results,
            "final_analysis": final_analysis,
            "raw_price_result": price_result
        }
    }
@app.post("/v1/snowboard/estimate")
def estimate_snowboard_price(
    images: List[UploadFile] = File(...),
    scene: str = "sell"
):
    """
    对外正式接口（小程序 / App 使用）
    """
    return analyze_multiple_images(images)

def check_rate_limit(api_key: str):
    """
    检查每个 API Key 的请求次数是否超过限制
    """
    current_time = time.time()  # 获取当前的时间戳（单位：秒）
    request_times = api_request_count[api_key]  # 获取这个 API Key 的请求时间列表

    # 删除过期的请求时间，保留在当前时间窗口内的请求
    api_request_count[api_key] = [t for t in request_times if current_time - t < TIME_WINDOW]

    # 如果请求次数超过限制，抛出 HTTP 429 错误
    if len(api_request_count[api_key]) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Too many requests. Try again later.")

    # 记录当前请求的时间戳
    api_request_count[api_key].append(current_time)


