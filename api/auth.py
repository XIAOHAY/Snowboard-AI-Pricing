# -*- coding: utf-8 -*
import os
from fastapi import Header, HTTPException

def verify_api_key(x_api_key: str = Header(...)):
    """
    API Key 校验依赖
    """
    api_keys = os.getenv("SNOWBOARD_API_KEYS")

    if not api_keys:
        raise HTTPException(status_code=500, detail="API keys not configured")

    valid_keys = [k.strip() for k in api_keys.split(",")]

    if x_api_key not in valid_keys:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    return x_api_key
