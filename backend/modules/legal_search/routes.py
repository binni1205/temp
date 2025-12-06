"""
法律检索模块 - 成员C负责

API路由前缀: /api/search
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def index():
    """模块首页"""
    return {"module": "legal_search", "status": "待开发"}


# TODO: 成员C在此添加法律检索相关的API接口

