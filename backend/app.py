"""
智法 - 司法智能助手后端主应用

模块化架构，四个功能模块分别由不同成员开发：
- modules/deep_research/     深度研究 (成员A)
- modules/legal_consultation/ 法律咨询 (成员B)  
- modules/legal_search/       法律检索 (成员C)
- modules/legal_summary/      司法摘要 (成员D)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings

app = FastAPI(
    title="智法 - 司法智能助手API",
    description="模块化后端架构，支持团队协作开发",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 注册各模块路由 ==========
# 每个成员在自己的模块目录下创建 routes.py，然后在这里注册

# 成员A: 深度研究
from modules.deep_research.routes import router as research_router
app.include_router(research_router, prefix="/api/research", tags=["深度研究"])

# 新增: 法律检索 (基于向量数据库)
from modules.legal_research.routes import router as legal_research_router
app.include_router(legal_research_router, prefix="/api/legal-research", tags=["法律检索-向量"])

# 成员B: 法律咨询
from modules.legal_consultation.routes import router as consultation_router
app.include_router(consultation_router, prefix="/api/consultation", tags=["法律咨询"])

# 成员C: 法律检索
from modules.legal_search.routes import router as search_router
app.include_router(search_router, prefix="/api/search", tags=["法律检索"])

# 成员D: 司法摘要
from modules.legal_summary.routes import router as summary_router
app.include_router(summary_router, prefix="/api/summary", tags=["司法摘要"])


@app.get("/")
async def root():
    """服务状态"""
    return {"service": "智法API", "status": "running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=settings.HOST, port=settings.PORT, reload=True)
