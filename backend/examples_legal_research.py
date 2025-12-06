#!/usr/bin/env python3
"""
Legal Research 模块使用示例

演示如何在项目中使用法律检索模块
"""

import sys
import os

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.legal_research.retriever import LegalRetriever


def example_basic_search():
    """基础检索示例"""
    print("\n" + "="*60)
    print("示例 1: 基础检索 (精确匹配)")
    print("="*60)
    
    # 初始化检索引擎
    retriever = LegalRetriever('./data/vector_db')
    
    # 精确检索示例
    query = "《合同法》第六十条"
    result = retriever.search(query, top_k=3)
    
    print(f"\n查询: {query}")
    print(f"检索类型: {result['search_type']}")
    print(f"结果数: {len(result['results'])}\n")
    
    if result['results']:
        for i, r in enumerate(result['results'], 1):
            print(f"{i}. {r['law_name']} {r['article']}")
            print(f"   相似度: {r['score']:.2%}")
            print(f"   内容: {r['content'][:80]}...")
            print()


def example_fuzzy_search():
    """模糊检索示例"""
    print("\n" + "="*60)
    print("示例 2: 模糊检索 (向量相似度)")
    print("="*60)
    
    retriever = LegalRetriever('./data/vector_db')
    
    # 模糊检索示例
    query = "合同当事人的权利和义务"
    result = retriever.search(query, top_k=5)
    
    print(f"\n查询: {query}")
    print(f"检索类型: {result['search_type']}")
    print(f"结果数: {len(result['results'])}\n")
    
    if result['results']:
        for i, r in enumerate(result['results'], 1):
            print(f"{i}. {r['law_name']} {r['article']}")
            print(f"   相似度: {r['score']:.2%}")
            print()


def example_batch_search():
    """批量检索示例"""
    print("\n" + "="*60)
    print("示例 3: 批量检索")
    print("="*60)
    
    retriever = LegalRetriever('./data/vector_db')
    
    queries = [
        "《合同法》第六十条",
        "《公司法》第三十五条",
        "《民法典》第一千条"
    ]
    
    results = retriever.batch_search(queries, top_k=2)
    
    for query, result in zip(queries, results):
        print(f"\n查询: {query}")
        print(f"类型: {result['search_type']}, 结果: {len(result['results'])}")
        if result['results']:
            for r in result['results'][:1]:
                print(f"  → {r['law_name']} {r['article']}")


def example_exact_vs_fuzzy():
    """精确检索和模糊检索对比"""
    print("\n" + "="*60)
    print("示例 4: 精确 vs 模糊检索对比")
    print("="*60)
    
    retriever = LegalRetriever('./data/vector_db')
    
    # 精确检索
    query1 = "《民法典》第一条"
    result1 = retriever.search(query1)
    print(f"\n【精确检索】{query1}")
    print(f"  搜索类型: {result1['search_type']}")
    print(f"  结果数: {len(result1['results'])}")
    if result1['results']:
        print(f"  得分: {result1['results'][0]['score']:.2%}")
    
    # 模糊检索（无精确匹配时）
    query2 = "民法关于人格权的保护"
    result2 = retriever.search(query2)
    print(f"\n【模糊检索】{query2}")
    print(f"  搜索类型: {result2['search_type']}")
    print(f"  结果数: {len(result2['results'])}")
    if result2['results']:
        print(f"  最高得分: {result2['results'][0]['score']:.2%}")
        print(f"  匹配法条: {result2['results'][0]['law_name']}")


def example_with_fastapi():
    """FastAPI 集成示例"""
    print("\n" + "="*60)
    print("示例 5: FastAPI 集成")
    print("="*60)
    print("""
在 routes.py 中集成检索引擎:

from fastapi import APIRouter
from pydantic import BaseModel
from .retriever import LegalRetriever

router = APIRouter()
retriever = None

def get_retriever():
    global retriever
    if retriever is None:
        retriever = LegalRetriever('./data/vector_db')
    return retriever

class SearchRequest(BaseModel):
    query: str
    top_k: int = 3

@router.post("/search")
async def search(request: SearchRequest):
    ret = get_retriever()
    result = ret.search(request.query, top_k=request.top_k)
    return result
    """)


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║       Legal Research 模块使用示例                           ║
║                                                            ║
║  前置条件:                                                 ║
║  1. 已运行 python scripts/build_vector_db.py              ║
║  2. 向量库存在于 ./data/vector_db                         ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    # 检查向量库是否存在
    if not os.path.exists('./data/vector_db'):
        print("❌ 错误: 向量库不存在")
        print("请先运行: python scripts/build_vector_db.py --json-root /path/to/json-laws")
        sys.exit(1)
    
    try:
        # 运行示例
        example_basic_search()
        example_fuzzy_search()
        example_batch_search()
        example_exact_vs_fuzzy()
        example_with_fastapi()
        
        print("\n" + "="*60)
        print("✅ 所有示例运行完成!")
        print("="*60)
    
    except Exception as e:
        print(f"\n❌ 出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
