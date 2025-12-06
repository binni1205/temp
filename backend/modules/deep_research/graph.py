"""
深度研究工作流 - 基于LangGraph构建

实现法律主题的深度研究报告生成流程：
1. 生成报告计划
2. 获取用户反馈
3. 基于网络搜索生成各章节
4. 编译最终报告
"""

import json
from typing import Annotated, List, TypedDict, Literal
from pydantic import BaseModel, Field
import operator

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.constants import Send
from langgraph.graph import START, END, StateGraph
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver

from duckduckgo_search import DDGS
from functools import lru_cache

from .llm import init_chat_model


# ==================== 提示词模板 ====================

report_structure = """使用此结构来创建关于用户提供法律主题的专业研究报告：

1. 引言（无需研究）
   - 法律主题的背景概述
   - 研究问题的重要性和现实意义

2. 正文部分：
   - 相关法律法规概述
   - 主要法律观点分析
   - 案例研究与判例分析
   - 法律争议点讨论
   - 各方观点比较
   
3. 结论
   - 总结主要法律见解
   - 可能的法律发展趋势
   - 提出合理的法律建议或解决方案"""


report_planner_query_writer_instructions = """您正在为一份报告进行研究。

<报告主题>
{topic}
</报告主题>

<报告组织结构>
{report_organization}
</报告组织结构>

<任务>
您的目标是生成{number_of_queries}个网络搜索查询，以帮助收集规划报告章节所需的信息。

这些查询应当：

1. 与报告主题相关
2. 有助于满足报告组织结构中指定的要求

请确保查询足够具体，以找到高质量、相关的资源，同时涵盖报告结构所需的广度。
</任务>
"""

report_planner_instructions = """我需要一个简洁且重点突出的法律研究报告计划。

<报告主题>
报告的法律主题是：
{topic}
</报告主题>

<报告组织结构>
报告应遵循以下组织结构：
{report_organization}
</报告组织结构>

<背景信息>
以下是用于规划报告章节的背景信息：
{context}
</背景信息>

<任务>
为法律研究报告生成章节列表。您的计划应当紧凑且重点突出，避免章节重叠或不必要的填充内容。

例如，一个良好的法律报告结构可能如下所示：
1/ 引言：法律背景与问题陈述
2/ 相关法律法规概述
3/ 司法实践与案例分析
4/ 法律争议点与不同观点
5/ 结论与法律建议

每个章节应包含以下字段：

- name（名称）- 报告此章节的名称。
- description（描述）- 本章节涵盖的主要法律问题和概念的简要概述。
- research（研究）- 是否需要为报告的这个章节进行网络研究。
- content（内容）- 章节的内容，现在暂时留空。

整合指南：
- 优先关注法律法规、判例和学术观点
- 确保每个章节有明确的法律分析目的，内容不重叠
- 注重实践应用，尽可能包含相关案例分析
- 合并相关法律概念而非分开处理

提交前，请检查您的结构，确保没有冗余章节并遵循逻辑流程。
</任务>

<反馈>
以下是审核对报告结构的反馈（如有）：
{feedback}
</反馈>
"""

final_section_writer_instructions = """您是一位专业法律技术作家，正在撰写一个综合报告其他部分信息的章节。

<报告主题>
{topic}
</报告主题>

<章节名称>
{section_name}
</章节名称>

<章节主题> 
{section_topic}
</章节主题>

<可用报告内容>
{context}
</可用报告内容>

<任务>
1. 章节特定方法：

对于引言：
- 使用#作为报告标题（Markdown格式）
- 限制在100-150字
- 明确阐述法律研究问题和意义
- 简要介绍相关法律背景
- 说明研究的目的和范围
- 不包含结构元素（无列表或表格）
- 不需要来源部分

对于结论/总结：
- 使用##作为章节标题（Markdown格式）
- 限制在150-200字
- 对于法律比较研究： 
    * 必须包含使用Markdown表格语法的法律观点比较表
    * 表格应提炼不同法律立场的关键差异
    * 表格各项目应包含主要法律依据
- 对于法律分析报告：
    * 必须使用一种结构元素强化法律论点：
    * 要么是使用Markdown表格语法比较不同法律观点的表格
    * 要么是使用正确Markdown列表语法的法律要点总结：
      - 使用`*`或`-`表示无序列表
      - 使用`1.`表示有序列表
      - 确保正确的缩进和间距
- 以具体的法律建议、发展趋势预测或实践影响结尾
- 不需要来源部分

3. 写作方法：
- 使用准确的法律术语和概念
- 保持客观、中立的专业语言
- 确保法律分析的准确性和完整性
- 专注于法律实质而非程序细节
</任务>

<质量检查>
- 对于引言：100-150字限制，#用于报告标题，包含法律背景和问题陈述，无结构元素，无来源部分
- 对于结论：150-200字限制，##用于章节标题，包含法律要点总结和建议，有一个结构元素，无来源部分
- Markdown格式正确
- 法律术语使用准确
- 不要在回复中包含字数统计或任何前言
</质量检查>"""

section_writer_instructions = """您是一位专业法律技术作家，正在撰写法律研究报告的一个章节。

<报告主题>
{topic}
</报告主题>

<章节名称>
{section_name}
</章节名称>

<章节主题>
{section_topic}
</章节主题>

<现有章节内容（如已填写）>
{section_content}
</现有章节内容>

<源材料>
{context}
</源材料>

<写作指南>
1. 如果现有章节内容未填写，请从头开始撰写新章节。
2. 如果现有章节内容已填写，请撰写一个新章节，将现有章节内容与源材料综合起来。
</写作指南>

<长度和风格>
- 严格限制在200-250字（法律内容可能需要更多篇幅表达）
- 使用准确的法律术语和概念
- 严谨客观的法律分析风格
- 清晰阐述法律观点和依据
- 以**粗体**标注您最重要的法律见解开始
- 使用简短段落（最多3-4句话）
- 使用##作为章节标题（Markdown格式）
- 必要时使用一种结构元素：
  * 要么是对比不同法律观点的简明表格（使用Markdown表格语法）
  * 要么是使用正确Markdown列表语法的法律要点列表（3-5项）：
    - 使用`*`或`-`表示无序列表
    - 使用`1.`表示有序列表
    - 确保正确的缩进和间距
- 尽可能引用相关法律法规、判例或专家观点
- 以### 参考资料结尾，引用以下源材料，格式为：
  * 列出每个来源的标题、日期和URL
  * 格式：`- 标题：URL`
</长度和风格>

<质量检查>
- 恰好200-250字（不包括标题和来源）
- 术语准确，观点清晰
- 逻辑严谨，论证有力
- 区分事实陈述和法律分析
- 谨慎使用仅一种结构元素，且仅在有助于阐明法律观点时使用
- 至少引用一个具体法律条款或案例
- 以粗体法律见解开始
- 在创建章节内容前没有前言
- 在末尾引用来源
</质量检查>
"""

section_grader_instructions = """根据指定主题审查报告章节：

<报告主题>
{topic}
</报告主题>

<章节主题>
{section_topic}
</章节主题>

<章节内容>
{section}
</章节内容>

<任务>
评估章节内容是否充分涵盖了章节主题。

如果章节内容未能充分涵盖章节主题，请生成{number_of_follow_up_queries}个后续搜索查询以收集缺失信息。
</任务>

<格式>
    grade: Literal["pass","fail"] = Field(
        description="评估结果，表明响应是否满足要求（'pass'）或需要修改（'fail'）。"
    )
    follow_up_queries: List[SearchQuery] = Field(
        description="后续搜索查询列表。",
    )
</格式>
"""

legal_query_writer_instructions = """您是一位专业法律研究员，负责制定有针对性的法律网络搜索查询，以收集有关法律主题的全面信息。

<法律研究主题>
{topic}
</法律研究主题>

<章节主题>
{section_topic}
</章节主题>

<任务>
您的目标是生成{number_of_queries}个法律搜索查询，帮助收集关于上述章节主题的权威法律信息。

这些查询应当：
1. 与法律主题直接相关
2. 针对不同的法律信息来源（法规、判例、学术观点）
3. 包含法律特定术语和概念
4. 使用精确的法律语言
5. 注重查找最新和权威的法律资源

对于每个查询，请考虑：
- 相关法律法规
- 司法解释或指导案例
- 权威法律评论或学术观点
- 最近的法律发展或修订
</任务>

<输出格式>
请以JSON格式返回查询，格式如下：
{{
  "queries": [
    {{"search_query": "查询1"}},
    {{"search_query": "查询2"}},
    {{"search_query": "查询3"}}
  ]
}}
</输出格式>
"""


# ==================== 数据模型 ====================

class SearchQuery(BaseModel):
    search_query: str = Field(None, description="要进行网络搜索的query")
    
class Queries(BaseModel):
    queries: List[SearchQuery] = Field(description="搜索query列表")


class Section(BaseModel):
    name: str = Field(description="报告此章节的名称。")
    description: str = Field(description="本章节将涵盖的主要主题和概念的简要概述。")
    research: bool = Field(description="是否需要为报告的这个章节进行网络研究。")
    content: str = Field(description="章节的内容。")   

class Sections(BaseModel):
    sections: List[Section] = Field(description="报告的章节。")

class Feedback(BaseModel):
    grade: Literal["pass", "fail"] = Field(
        description="评估结果，表明响应是否满足要求（'pass'）或需要修改（'fail'）。"
    )
    follow_up_queries: List[SearchQuery] = Field(description="后续搜索查询列表。")


# ==================== 状态定义 ====================

class ReportStateInput(TypedDict):
    topic: str  # 报告主题
    
class ReportStateOutput(TypedDict):
    final_report: str  # 最终报告

class ReportState(TypedDict):
    topic: str  # 报告主题    
    feedback_on_report_plan: str  # 报告计划的反馈
    sections: list[Section]  # 报告章节列表 
    completed_sections: Annotated[list, operator.add]  # Send() API键
    report_sections_from_research: str  # 从研究中完成的任何章节的字符串
    final_report: str  # 最终报告

class SectionState(TypedDict):
    topic: str  # 报告主题
    section: Section  # 报告章节  
    search_iterations: int  # 已完成的搜索迭代次数
    search_queries: list[SearchQuery]  # 搜索查询列表
    source_str: str  # 来自网络搜索的格式化源内容字符串
    report_sections_from_research: str  # 从研究中完成的任何章节的字符串
    completed_sections: list[Section]  # 在外部状态中用于Send() API的最终键

class SectionOutputState(TypedDict):
    completed_sections: list[Section]


# ==================== 工具函数 ====================

@lru_cache()
def web_search(query: str) -> list:
    """
    使用DuckDuckGo搜索引擎执行网络搜索，优先考虑法律相关网站
    搜索失败时返回空列表，不会中断流程
    """
    import os
    
    # 从环境变量获取代理配置
    # Windows PowerShell: $env:PROXY_URL = "socks5://127.0.0.1:7890"
    # 或 HTTP 代理: $env:PROXY_URL = "http://127.0.0.1:7890"
    proxy = os.environ.get("PROXY_URL", None)
    
    try:
        # 基本搜索（带代理和超时）
        results = DDGS(proxy=proxy, timeout=30).text(query, max_results=15)
        results_list = list(results)
        
        if not results_list:
            print(f"[Search] '{query}' returned no results")
            return []
            
    except Exception as e:
        # 搜索失败时返回空结果而不是崩溃
        print(f"[Search Failed] '{query}': {e}")
        print("Tip: Set PROXY_URL environment variable if network issues persist")
        return []
    
    # 法律相关域名列表
    legal_domains = [
        'law.com', 'lawfirm', 'legaldaily', 'court.gov', 'supremecourt', 
        'justice.gov', 'findlaw', 'lexisnexis', 'westlaw', 'chinalaw', 
        'chinacourt', 'gov.cn/flfg', 'npc.gov.cn', 'spp.gov.cn', 'court.gov.cn',
        'lawyer', 'legal', 'judiciary', 'legislation', 'lawsociety', 
        'law.', '.law', 'baike', 'wiki', 'pkulaw', 'lawpress'
    ]
    
    legal_journals = [
        'journal', 'review', 'scholar', 'academic', 'edu.cn', 
        'research', 'ssrn.com', 'heinonline', 'jstor', 'cnki'
    ]
    
    def is_legal_site(url):
        url_lower = url.lower()
        domain_score = sum(2 for domain in legal_domains if domain in url_lower)
        journal_score = sum(1 for journal in legal_journals if journal in url_lower)
        return domain_score + journal_score
    
    results_list.sort(key=lambda x: is_legal_site(x['href']), reverse=True)
    return results_list[:10]


def deduplicate_and_format_sources(search_response, max_tokens_per_source):
    """去重并格式化搜索结果"""
    sources_list = []
    for response in search_response:
        sources_list.extend(response)
    unique_sources = {source['href']: source for source in sources_list}

    formatted_text = "Sources:\n\n"
    for i, source in enumerate(unique_sources.values(), 1):
        formatted_text += f"Source {source['title']}:\n===\n"
        formatted_text += f"URL: {source['href']}\n===\n"
        formatted_text += f"Most relevant content from source: {source['body']}\n===\n"
    return formatted_text.strip()


def format_sections(sections: list[Section]) -> str:
    """格式化章节列表为字符串"""
    formatted_str = ""
    for idx, section in enumerate(sections, 1):
        formatted_str += f"""
{'='*60}
Section {idx}: {section.name}
{'='*60}
Description:
{section.description}
Requires Research: 
{section.research}

Content:
{section.content if section.content else '[Not yet written]'}

"""
    return formatted_str


# ==================== 图节点函数 ====================

async def generate_report_plan(state: ReportState):
    """生成报告计划"""
    topic = state["topic"]
    feedback = state.get("feedback_on_report_plan", "")
    number_of_queries = 2

    writer_model = init_chat_model(
        provider="zhipuai",
        model_name="glm-4-flash",
        temperature=0.0
    )
    structured_llm = writer_model.with_structured_output(Queries)

    system_instructions_query = report_planner_query_writer_instructions.format(
        topic=topic, 
        report_organization=report_structure, 
        number_of_queries=number_of_queries
    )
    results = structured_llm.invoke([
        SystemMessage(content=system_instructions_query),
        HumanMessage(content="生成有助于规划报告章节的搜索查询。")
    ])

    query_list = [query.search_query for query in results.queries]
    
    # 执行网络搜索
    search_results = [web_search(query) for query in query_list]
    source_str = deduplicate_and_format_sources(search_results, max_tokens_per_source=1000)
    
    # 如果搜索结果为空，提供默认提示
    if not source_str or source_str == "Sources:":
        source_str = "No search results available. Please generate report sections based on your knowledge."
        print("[Warning] No search results, using LLM knowledge only")

    system_instructions_sections = report_planner_instructions.format(
        topic=topic, 
        report_organization=report_structure, 
        context=source_str, 
        feedback=feedback
    )
    planner_llm = init_chat_model(
        provider="zhipuai",
        model_name="glm-4-plus",
        temperature=0.0
    )

    # 使用 with_structured_output 替代 bind_tools，更稳定
    structured_llm = planner_llm.with_structured_output(Sections)
    try:
        report_sections = structured_llm.invoke([
            SystemMessage(content=system_instructions_sections),
            HumanMessage(content="生成报告的章节")
        ])
        
        # 处理不同的返回类型
        if isinstance(report_sections, Sections):
            sections = report_sections.sections
        elif isinstance(report_sections, dict):
            sections = Sections(**report_sections).sections
        elif isinstance(report_sections, str):
            tool_call = json.loads(report_sections)
            sections = Sections(**tool_call).sections
        else:
            # 尝试从AIMessage中提取
            content = report_sections.content if hasattr(report_sections, 'content') else str(report_sections)
            tool_call = json.loads(content)
            sections = Sections(**tool_call).sections
            
    except Exception as e:
        print(f"[Error] Failed to parse sections: {e}")
        # 创建默认章节结构
        sections = [
            Section(name="引言", description=f"关于{topic}的背景介绍", research=False, content=""),
            Section(name="法律法规概述", description=f"与{topic}相关的法律法规", research=True, content=""),
            Section(name="案例分析", description=f"相关司法案例分析", research=True, content=""),
            Section(name="结论与建议", description="总结与法律建议", research=False, content=""),
        ]
        print(f"[Info] Using default sections for topic: {topic}")
    
    return {"sections": sections}


def human_feedback(state: ReportState) -> Command[Literal["generate_report_plan", "build_section_with_web_research"]]:
    """获取报告计划的人类反馈"""
    topic = state["topic"]
    sections = state['sections']
    sections_str = "\n\n".join(
        f"Section: {section.name}\n"
        f"Description: {section.description}\n"
        f"Research needed: {'Yes' if section.research else 'No'}\n"
        for section in sections
    )

    interrupt_message = f"""请对以下报告计划提供反馈。
                        \n\n{sections_str}\n\n
                        \n报告计划是否满足您的需求？输入'true'来批准报告计划，或提供反馈以重新生成报告计划："""
    feedback = interrupt(interrupt_message)

    if isinstance(feedback, bool) and feedback is True:
        return Command(goto=[
            Send("build_section_with_web_research", {
                "topic": topic, 
                "section": s, 
                "search_iterations": 0
            }) 
            for s in sections 
            if s.research
        ])
    
    elif isinstance(feedback, str):
        return Command(
            goto="generate_report_plan", 
            update={"feedback_on_report_plan": feedback}
        )
    else:
        raise TypeError(f"Interrupt value of type {type(feedback)} is not supported.")


def generate_queries(state: SectionState):
    """为报告章节生成搜索查询"""
    topic = state["topic"]
    section = state["section"]
    number_of_queries = 3

    writer_model = init_chat_model(
        provider="zhipuai",
        model_name="glm-4-flash",
        temperature=0.0
    )
    structured_llm = writer_model.with_structured_output(Queries)

    system_instructions = legal_query_writer_instructions.format(
        topic=topic, 
        section_topic=section, 
        number_of_queries=number_of_queries
    )
    queries = structured_llm.invoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content="生成法律主题相关的搜索查询。")
    ])
    return {"search_queries": queries.queries}


async def search_web(state: SectionState):
    """执行网络搜索并格式化结果"""
    search_queries = state["search_queries"]
    query_list = [
        query.search_query 
        for query in search_queries 
        if query.search_query and query.search_query.strip()
    ]
    
    if not query_list:
        return {
            "source_str": "未找到有效的搜索查询。", 
            "search_iterations": state["search_iterations"] + 1
        }
    
    # 添加法律关键词以增强搜索相关性
    enhanced_queries = []
    for query in query_list:
        if not any(term in query.lower() for term in ['法律', '法规', '条例', '司法', '判例', '案例']):
            enhanced_queries.append(f"{query} 法律 法规")
        else:
            enhanced_queries.append(query)
    
    search_results = []
    for query in enhanced_queries:
        try:
            if query and query.strip():
                results = web_search(query)
                search_results.append(results)
        except Exception as e:
            print(f"搜索查询出错: {str(e)}")
            continue
    
    if not search_results:
        return {
            "source_str": "搜索过程中出现错误或未找到相关结果。", 
            "search_iterations": state["search_iterations"] + 1
        }
        
    source_str = deduplicate_and_format_sources(search_results, max_tokens_per_source=5000)
    return {"source_str": source_str, "search_iterations": state["search_iterations"] + 1}


def write_section(state: SectionState) -> Command[Literal[END, "search_web"]]:
    """根据搜索结果编写章节内容"""
    topic = state["topic"]
    section = state["section"]
    source_str = state["source_str"]

    system_instructions = section_writer_instructions.format(
        topic=topic, 
        section_name=section.name, 
        section_topic=section.description, 
        context=source_str, 
        section_content=section.content
    )
 
    writer_model = init_chat_model(
        provider="zhipuai",
        model_name="glm-4-flash",
        temperature=0.0
    )
    
    section_content = writer_model.invoke([
        SystemMessage(content=system_instructions), 
        HumanMessage(content="根据提供的资料生成一个报告章节。")
    ])

    section.content = section_content.content

    section_grader_message = """评估报告并考虑针对缺失信息的后续问题。
                               如果评级为'pass'，则所有后续查询返回空字符串。
                               如果评级为'fail'，请提供具体的搜索查询以收集缺失信息。"""
    
    section_grader_instructions_formatted = section_grader_instructions.format(
        topic=topic, 
        section_topic=section.description,
        section=section.content, 
        number_of_follow_up_queries=2
    )

    reflection_model = init_chat_model(
        provider="zhipuai",
        model_name="glm-4-plus",
        temperature=0.0
    )

    reflection_result = reflection_model.bind_tools([Feedback]).invoke([
        SystemMessage(content=section_grader_instructions_formatted),
        HumanMessage(content=section_grader_message)
    ])
    
    tool_call = json.loads(reflection_result.content)

    if tool_call['follow_up_queries'] and isinstance(tool_call['follow_up_queries'][0], str):
        tool_call['follow_up_queries'] = [{'search_query': _} for _ in tool_call['follow_up_queries']]
    
    feedback = Feedback(**tool_call)
    
    if feedback.grade == "pass" or state["search_iterations"] >= 2:
        return Command(
            update={"completed_sections": [section]},
            goto=END
        )
    else:
        return Command(
            update={"search_queries": feedback.follow_up_queries, "section": section},
            goto="search_web"
        )


def write_final_sections(state: SectionState):
    """编写最终章节内容"""
    topic = state["topic"]
    section = state["section"]
    completed_report_sections = state["report_sections_from_research"]
    
    system_instructions = final_section_writer_instructions.format(
        topic=topic, 
        section_name=section.name, 
        section_topic=section.description, 
        context=completed_report_sections
    )

    writer_model = init_chat_model(
        provider="zhipuai",
        model_name="glm-4-flash",
        temperature=0.0
    )
    
    section_content = writer_model.invoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content="根据提供的资料生成一个报告章节。")
    ])
    
    section.content = section_content.content
    return {"completed_sections": [section]}


def gather_completed_sections(state: ReportState):
    """收集已完成的章节"""
    completed_sections = state["completed_sections"]
    completed_report_sections = format_sections(completed_sections)
    return {"report_sections_from_research": completed_report_sections}


def initiate_final_section_writing(state: ReportState):
    """使用Send API并行编写最终章节"""    
    return [
        Send("write_final_sections", {
            "topic": state["topic"], 
            "section": s, 
            "report_sections_from_research": state["report_sections_from_research"]
        }) 
        for s in state["sections"] 
        if not s.research
    ]


def compile_final_report(state: ReportState):
    """编译最终报告"""    
    sections = state["sections"]
    completed_sections = {s.name: s.content for s in state["completed_sections"]}

    for section in sections:
        section.content = completed_sections[section.name]

    all_sections = "\n\n".join([s.content for s in sections])
    return {"final_report": all_sections}


# ==================== 构建图 ====================

# 章节构建子图
section_builder = StateGraph(SectionState, output=SectionOutputState)
section_builder.add_node("generate_queries", generate_queries)
section_builder.add_node("search_web", search_web)
section_builder.add_node("write_section", write_section)

section_builder.add_edge(START, "generate_queries")
section_builder.add_edge("generate_queries", "search_web")
section_builder.add_edge("search_web", "write_section")

# 主图
builder = StateGraph(ReportState, input=ReportStateInput, output=ReportStateOutput)
builder.add_node("generate_report_plan", generate_report_plan)
builder.add_node("human_feedback", human_feedback)
builder.add_node("build_section_with_web_research", section_builder.compile())
builder.add_node("gather_completed_sections", gather_completed_sections)
builder.add_node("write_final_sections", write_final_sections)
builder.add_node("compile_final_report", compile_final_report)

builder.add_edge(START, "generate_report_plan")
builder.add_edge("generate_report_plan", "human_feedback")
builder.add_edge("build_section_with_web_research", "gather_completed_sections")
builder.add_conditional_edges(
    "gather_completed_sections", 
    initiate_final_section_writing, 
    ["write_final_sections"]
)
builder.add_edge("write_final_sections", "compile_final_report")
builder.add_edge("compile_final_report", END)


def create_research_graph():
    """创建带有内存检查点的研究图"""
    memory = MemorySaver()
    return builder.compile(checkpointer=memory)


# 默认图实例
graph = builder.compile()

