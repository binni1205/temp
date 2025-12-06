"""
司法摘要模块 - 成员D负责

API路由前缀: /api/summary
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def index():
    """模块首页"""
    return {"module": "legal_summary", "status": "待开发"}


# TODO: 成员D在此添加司法摘要相关的API接口

