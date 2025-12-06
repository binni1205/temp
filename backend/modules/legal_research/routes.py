"""
法律检索模块 - API路由

API前缀: /api/research

提供两层法律检索接口：
- 精确检索：法律名称 + 法条号完全匹配
- 模糊检索：向量相似度搜索 (当精确检索失败时)
"""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid

from .retriever import LegalRetriever

router = APIRouter()

# ==================== 全局配置 ====================

# FAISS向量数据库路径（需要用户自行配置）
VECTOR_DB_PATH = os.getenv("LEGAL_VECTOR_DB_PATH", "./data/vector_db")

# 初始化检索引擎（全局单例）
_retriever_instance = None


def get_retriever() -> LegalRetriever:
    """获取全局检索引擎实例"""
    global _retriever_instance
    if _retriever_instance is None:
        if not os.path.exists(VECTOR_DB_PATH):
            raise HTTPException(
                status_code=500,
                detail=f"向量数据库路径不存在: {VECTOR_DB_PATH}。请先配置 LEGAL_VECTOR_DB_PATH 环境变量并构建向量库。"
            )
        _retriever_instance = LegalRetriever(VECTOR_DB_PATH, use_cuda=True)
    return _retriever_instance


# ==================== 请求/响应模型 ====================

class SearchRequest(BaseModel):
    """检索请求"""
    query: str = Field(..., description="查询字符串，格式 '《法律名称》法条信息'")
    top_k: int = Field(default=3, description="模糊检索返回结果数，默认3")


class SearchResult(BaseModel):
    """单条检索结果"""
    content: str = Field(description="法条全文内容")
    law_name: str = Field(description="完整法律名称")
    simple_law_name: str = Field(description="简化法律名称（去掉前缀）")
    article: str = Field(description="法条号")
    article_num: Optional[int] = Field(description="法条号转换为数字")
    score: float = Field(description="相似度分数 (0-1, 精确匹配为1.0)")


class SearchResponse(BaseModel):
    """检索响应"""
    query: str = Field(description="原始查询字符串")
    search_type: str = Field(description="检索类型: 'exact' 精确 | 'fuzzy' 模糊 | 'none' 无结果")
    results: List[SearchResult] = Field(description="检索结果列表")
    message: str = Field(description="提示信息")


class BatchSearchRequest(BaseModel):
    """批量检索请求"""
    queries: List[str] = Field(..., description="查询字符串列表")
    top_k: int = Field(default=3, description="每个查询返回的结果数")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    message: str
    vector_db_path: str


# ==================== API 接口 ====================

@router.get("/")
async def index():
    """模块首页"""
    return {
        "module": "legal_research",
        "description": "法律检索 - 基于向量数据库的两层检索",
        "endpoints": {
            "GET /": "模块信息",
            "GET /health": "健康检查",
            "POST /search": "执行检索 (精确优先 → 模糊备选)",
            "POST /batch-search": "批量检索",
        }
    }


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查 - 验证向量数据库是否正常"""
    try:
        retriever = get_retriever()
        return HealthResponse(
            status="healthy",
            message="向量数据库加载成功，检索引擎就绪",
            vector_db_path=VECTOR_DB_PATH
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"检索引擎初始化失败: {str(e)}"
        )


@router.post("/search", response_model=SearchResponse)
async def search_legal(request: SearchRequest):
    """
    执行法律检索
    
    两层检索策略：
    1. 精确检索：法律名称 + 法条号完全匹配
    2. 模糊检索：向量相似度搜索 (Top-K)
    
    示例请求：
    ```json
    {
        "query": "《合同法》第六十条",
        "top_k": 3
    }
    ```
    """
    try:
        retriever = get_retriever()
        
        # 执行检索
        result = retriever.search(request.query, top_k=request.top_k)
        
        # 生成提示信息
        if result["search_type"] == "exact":
            message = "✓ 精确匹配成功"
        elif result["search_type"] == "fuzzy":
            message = f"✓ 向量相似度匹配 (Top-{request.top_k})"
        else:
            message = "✗ 未找到匹配的法律条文"
        
        # 构建响应
        return SearchResponse(
            query=result["query"],
            search_type=result["search_type"],
            results=[SearchResult(**r) for r in result["results"]],
            message=message
        )
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"检索过程中出错: {str(e)}"
        )


@router.post("/batch-search")
async def batch_search(request: BatchSearchRequest):
    """
    批量执行法律检索
    
    示例请求：
    ```json
    {
        "queries": [
            "《合同法》第六十条",
            "《公司法》第三十五条"
        ],
        "top_k": 3
    }
    ```
    """
    try:
        retriever = get_retriever()
        
        results = []
        for query in request.queries:
            search_result = retriever.search(query, top_k=request.top_k)
            
            # 生成提示信息
            if search_result["search_type"] == "exact":
                message = "✓ 精确匹配"
            elif search_result["search_type"] == "fuzzy":
                message = f"✓ 向量匹配"
            else:
                message = "✗ 无结果"
            
            results.append({
                "query": search_result["query"],
                "search_type": search_result["search_type"],
                "results": [SearchResult(**r) for r in search_result["results"]],
                "message": message
            })
        
        return {
            "total": len(request.queries),
            "results": results
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"批量检索出错: {str(e)}"
        )


@router.get("/debug/stats")
async def get_stats():
    """
    [调试接口] 获取检索引擎统计信息
    """
    try:
        retriever = get_retriever()
        
        # 获取向量库文档数量
        doc_count = len(retriever.vector_db.documents) if hasattr(retriever.vector_db, "documents") else 0
        
        return {
            "status": "ok",
            "vector_db_path": VECTOR_DB_PATH,
            "total_documents": doc_count,
            "embedding_model": "shibing624/text2vec-base-chinese",
            "retrieval_strategy": "exact (priority) → fuzzy (fallback)"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取统计信息失败: {str(e)}"
        )
