"""
法律咨询模块 - 成员B负责

API路由前缀: /api/consultation
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def index():
    """模块首页"""
    return {"module": "legal_consultation", "status": "待开发"}


# TODO: 成员B在此添加法律咨询相关的API接口

