# -*- coding: utf-8 -*
# api/estimate.py

from fastapi import APIRouter

# 创建一个路由对象
router = APIRouter()


@router.get("/ping")
def ping():
    """
    健康检查接口
    用来确认服务是否正常运行
    """
    return {"status": "ok"}
