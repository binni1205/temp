"""
法律检索引擎 - 向量数据库 + 精确检索

实现两层检索策略：
1. 精确检索：法律名称 + 法条号匹配
2. 模糊检索：FAISS向量相似度 (Top-3)
"""

import os
import re
from typing import List, Tuple, Optional, Dict, Any
from langchain.docstore.document import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS


# ==================== 辅助函数 ====================

def chinese_to_arabic(chinese_num: str) -> int:
    """中文数字转阿拉伯数字"""
    mapping = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        '十': 10, '百': 100, '千': 1000, '万': 10000
    }
    total = 0
    temp = 0
    for c in chinese_num:
        if c in mapping:
            val = mapping[c]
            if val >= 10:
                if temp == 0:
                    temp = 1
                total += temp * val
                temp = 0
            else:
                temp = val
    return total + temp


def get_article_number(article_str: str) -> Optional[int]:
    """
    从 "第六十条" 的字符串中提取数字，转换为阿拉伯数字
    失败返回 None
    """
    num_str = article_str.replace("第", "").replace("条", "")
    try:
        return chinese_to_arabic(num_str)
    except Exception:
        return None


def extract_simple_law_name(query: str) -> Optional[str]:
    """
    从查询中提取法律名称
    格式：《合同法》第六十条 → 合同法
    """
    m = re.search(r"《(.*?)》", query)
    if m:
        return m.group(1).strip()
    return None


def extract_article(query: str) -> Optional[str]:
    """
    从查询中提取法条号
    格式：第六十条 → 第六十条（去除空格）
    """
    m = re.search(r"(第[零一二三四五六七八九十百千万\s]+条)", query)
    if m:
        return re.sub(r"\s+", "", m.group(1))
    return None


# ==================== 法律检索引擎类 ====================

class LegalRetriever:
    """
    两层法律检索引擎
    
    第一层（精确检索）：法律名称 + 法条号完全匹配
    第二层（模糊检索）：向量相似度搜索 Top-3
    """
    
    def __init__(self, vector_db_path: str, use_cuda: bool = True):
        """
        初始化检索引擎
        
        Args:
            vector_db_path: FAISS向量数据库路径
            use_cuda: 是否使用GPU
        """
        self.vector_db_path = vector_db_path
        self.use_cuda = use_cuda
        self.vector_db = None
        self.embeddings = None
        self._initialize()
    
    def _initialize(self):
        """初始化向量数据库和嵌入模型"""
        device = "cuda" if self.use_cuda else "cpu"
        self.embeddings = HuggingFaceEmbeddings(
            model_name="shibing624/text2vec-base-chinese",
            model_kwargs={"device": device}
        )
        self.vector_db = FAISS.load_local(
            self.vector_db_path,
            self.embeddings,
            allow_dangerous_deserialization=True
        )
    
    def exact_search(self, query: str) -> List[Document]:
        """
        精确检索：法律名称 + 法条号完全匹配
        
        Args:
            query: 查询字符串，格式 "《合同法》第六十条"
            
        Returns:
            匹配的文档列表
        """
        query_law = extract_simple_law_name(query)
        query_article_str = extract_article(query)
        query_article_num = get_article_number(query_article_str) if query_article_str else None
        
        if not query_law or query_article_num is None:
            return []
        
        # 遍历所有文档进行精确匹配
        if not hasattr(self.vector_db, "documents"):
            return []
        
        results = []
        for doc in self.vector_db.documents:
            # 法律名称匹配
            if query_law not in doc.metadata.get("simple_law_name", ""):
                continue
            # 法条号完全匹配
            if doc.metadata.get("article_num") != query_article_num:
                continue
            results.append(doc)
        
        return results
    
    def fuzzy_search(self, query: str, top_k: int = 3) -> List[Tuple[Document, float]]:
        """
        模糊检索：向量相似度搜索
        
        当精确检索失败时使用，返回相似度最高的 Top-K 法条
        
        Args:
            query: 查询字符串
            top_k: 返回结果数 (默认3)
            
        Returns:
            [(Document, similarity_score), ...] 列表
        """
        try:
            # 使用相似度搜索
            results = self.vector_db.similarity_search_with_score(query, k=top_k)
            return results
        except Exception as e:
            print(f"[Error] 模糊检索失败: {e}")
            return []
    
    def search(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        """
        两层检索：精确优先，模糊备选
        
        Args:
            query: 查询字符串
            top_k: 模糊检索返回的结果数
            
        Returns:
            {
                "query": 原始查询,
                "search_type": "exact" | "fuzzy",
                "results": [
                    {
                        "content": 法条内容,
                        "law_name": 法律名称,
                        "article": 法条号,
                        "score": 相似度分数 (仅模糊检索有),
                        "metadata": 元数据
                    },
                    ...
                ]
            }
        """
        # 第一层：精确检索
        exact_results = self.exact_search(query)
        if exact_results:
            return {
                "query": query,
                "search_type": "exact",
                "results": [
                    {
                        "content": doc.page_content,
                        "law_name": doc.metadata.get("law_name"),
                        "simple_law_name": doc.metadata.get("simple_law_name"),
                        "article": doc.metadata.get("article"),
                        "article_num": doc.metadata.get("article_num"),
                        "score": 1.0,  # 精确匹配得分为1.0
                        "metadata": doc.metadata
                    }
                    for doc in exact_results
                ]
            }
        
        # 第二层：模糊检索（向量相似度）
        fuzzy_results = self.fuzzy_search(query, top_k=top_k)
        if fuzzy_results:
            return {
                "query": query,
                "search_type": "fuzzy",
                "results": [
                    {
                        "content": doc.page_content,
                        "law_name": doc.metadata.get("law_name"),
                        "simple_law_name": doc.metadata.get("simple_law_name"),
                        "article": doc.metadata.get("article"),
                        "article_num": doc.metadata.get("article_num"),
                        "score": float(score),  # 相似度分数
                        "metadata": doc.metadata
                    }
                    for doc, score in fuzzy_results
                ]
            }
        
        # 都没有结果
        return {
            "query": query,
            "search_type": "none",
            "results": []
        }
    
    def batch_search(self, queries: List[str], top_k: int = 3) -> List[Dict[str, Any]]:
        """
        批量检索
        
        Args:
            queries: 查询字符串列表
            top_k: 每个查询返回的结果数
            
        Returns:
            搜索结果列表
        """
        return [self.search(q, top_k=top_k) for q in queries]
