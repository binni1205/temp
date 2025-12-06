"""
深度研究模块 - API路由

API前缀: /api/research

提供法律主题深度研究报告生成的API接口
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import uuid
import asyncio

from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver

from .graph import builder, Section

router = APIRouter()

# 存储研究会话
research_sessions = {}


# ==================== 请求/响应模型 ====================

class ResearchRequest(BaseModel):
    """研究请求"""
    topic: str
    
class FeedbackRequest(BaseModel):
    """反馈请求"""
    session_id: str
    feedback: str  # "true" 表示批准，其他字符串表示修改建议

class SectionResponse(BaseModel):
    """章节响应"""
    name: str
    description: str
    research: bool
    content: str = ""

class ReportPlanResponse(BaseModel):
    """报告计划响应"""
    session_id: str
    sections: List[SectionResponse]
    message: str

class ReportResponse(BaseModel):
    """最终报告响应"""
    session_id: str
    final_report: str
    status: str


# ==================== API接口 ====================

@router.get("/")
async def index():
    """模块首页"""
    return {
        "module": "deep_research",
        "description": "法律主题深度研究报告生成",
        "endpoints": {
            "POST /start": "开始新的研究，提交主题",
            "POST /feedback": "提交对报告计划的反馈",
            "GET /status/{session_id}": "获取研究状态",
            "GET /report/{session_id}": "获取最终报告"
        }
    }


@router.post("/start", response_model=ReportPlanResponse)
async def start_research(request: ResearchRequest):
    """
    开始新的深度研究
    
    提交研究主题，返回报告计划供用户审核
    """
    session_id = str(uuid.uuid4())
    
    # 创建带检查点的图
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)
    thread = {"configurable": {"thread_id": session_id}}
    
    # 存储会话
    research_sessions[session_id] = {
        "graph": graph,
        "thread": thread,
        "memory": memory,
        "status": "planning",
        "sections": [],
        "final_report": ""
    }
    
    try:
        # 生成报告计划
        sections_display = ""
        async for event in graph.astream({"topic": request.topic}, thread, stream_mode="updates"):
            if '__interrupt__' in event:
                sections_display = event['__interrupt__'][0].value
                break
        
        # 从图状态获取章节
        state = graph.get_state(thread)
        sections = state.values.get("sections", [])
        
        research_sessions[session_id]["sections"] = sections
        
        return ReportPlanResponse(
            session_id=session_id,
            sections=[
                SectionResponse(
                    name=s.name,
                    description=s.description,
                    research=s.research,
                    content=s.content
                ) for s in sections
            ],
            message="报告计划已生成，请审核后提交反馈"
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()  # 打印完整错误堆栈到终端
        del research_sessions[session_id]
        raise HTTPException(status_code=500, detail=f"生成报告计划失败: {str(e)}")


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    提交对报告计划的反馈
    
    - feedback="true": 批准计划，开始生成报告
    - feedback="其他文字": 修改建议，重新生成计划
    """
    session_id = request.session_id
    
    if session_id not in research_sessions:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    
    session = research_sessions[session_id]
    graph = session["graph"]
    thread = session["thread"]
    
    try:
        if request.feedback.lower() == "true":
            # 批准计划，开始生成报告
            session["status"] = "generating"
            
            async for event in graph.astream(Command(resume=True), thread, stream_mode="updates"):
                if 'compile_final_report' in event:
                    if 'final_report' in event['compile_final_report']:
                        session["final_report"] = event['compile_final_report']['final_report']
                        session["status"] = "completed"
                        break
            
            return {
                "session_id": session_id,
                "status": session["status"],
                "message": "报告生成完成" if session["status"] == "completed" else "报告生成中"
            }
        else:
            # 修改计划
            session["status"] = "replanning"
            
            async for event in graph.astream(request.feedback, thread, stream_mode="updates"):
                if '__interrupt__' in event:
                    break
            
            # 获取新的章节
            state = graph.get_state(thread)
            sections = state.values.get("sections", [])
            session["sections"] = sections
            session["status"] = "planning"
            
            return ReportPlanResponse(
                session_id=session_id,
                sections=[
                    SectionResponse(
                        name=s.name,
                        description=s.description,
                        research=s.research,
                        content=s.content
                    ) for s in sections
                ],
                message="报告计划已根据反馈重新生成"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理反馈失败: {str(e)}")


@router.get("/status/{session_id}")
async def get_status(session_id: str):
    """获取研究状态"""
    if session_id not in research_sessions:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    
    session = research_sessions[session_id]
    return {
        "session_id": session_id,
        "status": session["status"],
        "has_report": bool(session["final_report"])
    }


@router.get("/report/{session_id}", response_model=ReportResponse)
async def get_report(session_id: str):
    """获取最终报告"""
    if session_id not in research_sessions:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    
    session = research_sessions[session_id]
    
    if not session["final_report"]:
        raise HTTPException(status_code=400, detail="报告尚未生成完成")
    
    return ReportResponse(
        session_id=session_id,
        final_report=session["final_report"],
        status=session["status"]
    )


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """删除研究会话"""
    if session_id in research_sessions:
        del research_sessions[session_id]
        return {"message": "会话已删除"}
    raise HTTPException(status_code=404, detail="会话不存在")
