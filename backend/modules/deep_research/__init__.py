"""
深度研究模块

基于LangGraph实现法律主题的深度研究报告生成
"""

from .routes import router
from .graph import create_research_graph, graph

__all__ = ["router", "create_research_graph", "graph"]
