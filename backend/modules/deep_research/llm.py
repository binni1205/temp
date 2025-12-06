"""
智谱AI LLM封装 - 用于深度研究模块

提供与LangChain兼容的智谱AI聊天模型接口
"""

import os
import json
from typing import Any, Dict, List, Mapping, Optional, Union, Sequence, Type, Callable
from zhipuai import ZhipuAI
from pydantic import BaseModel, Field
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.chat_models.base import BaseChatModel
from langchain.schema import ChatResult, AIMessage, HumanMessage, SystemMessage, ChatMessage
from langchain.schema.messages import BaseMessage
from langchain.schema.output import ChatGeneration
from langchain.tools import BaseTool
from pydantic import BaseModel as TypeBaseModel
from langchain_core.language_models.chat_models import LanguageModelInput
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_core.output_parsers import PydanticToolsParser
from langchain_core.output_parsers.base import OutputParserLike
from langchain_core.utils.pydantic import is_basemodel_subclass

from config import settings


class ZhipuAIChat(BaseChatModel):
    """智谱AI聊天模型的LangChain集成"""
    
    client: Any = None
    model_name: str = "glm-4"
    temperature: float = 0.7
    top_p: float = 0.7
    max_tokens: Optional[int] = None
    api_key: Optional[str] = None
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        api_key = kwargs.get("api_key") or settings.ZHIPU_API_KEY or os.getenv("ZHIPU_API_KEY")
        if not api_key:
            raise ValueError("ZHIPU_API_KEY must be provided either as an argument or as an environment variable")
        self.client = ZhipuAI(api_key=api_key)
    
    def _convert_messages_to_zhipu_format(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """将LangChain消息格式转换为智谱AI格式"""
        zhipu_messages = []
        for message in messages:
            if isinstance(message, HumanMessage):
                zhipu_messages.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage):
                zhipu_messages.append({"role": "assistant", "content": message.content})
            elif isinstance(message, SystemMessage):
                zhipu_messages.append({"role": "system", "content": message.content})
            elif isinstance(message, ChatMessage):
                role = message.role
                if role == "human":
                    role = "user"
                elif role == "ai":
                    role = "assistant"
                zhipu_messages.append({"role": role, "content": message.content})
            else:
                raise ValueError(f"Message type {type(message)} not supported")
        return zhipu_messages
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """生成聊天完成"""
        zhipu_messages = self._convert_messages_to_zhipu_format(messages)
        
        params = {
            "model": self.model_name,
            "messages": zhipu_messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }
        
        if self.max_tokens:
            params["max_tokens"] = self.max_tokens
        
        if stop:
            params["stop"] = stop
            
        if "tools" in kwargs:
            params["tools"] = kwargs.pop("tools")
            
        if "tool_choice" in kwargs:
            params["tool_choice"] = kwargs.pop("tool_choice")
            
        if "response_format" in kwargs:
            params["response_format"] = kwargs.pop("response_format")
            
        for k, v in kwargs.items():
            params[k] = v

        response = self.client.chat.completions.create(**params)
        message = response.choices[0].message
        
        additional_kwargs = {}
        if hasattr(message, "tool_calls") and message.tool_calls:
            converted_tool_calls = []
            for tool_call in message.tool_calls:
                args = tool_call.function.arguments
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                
                converted_tool_call = {
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "args": args
                }
                converted_tool_calls.append(converted_tool_call)
            additional_kwargs["tool_calls"] = converted_tool_calls
        
        content = message.content if message.content is not None else ""
        
        generation = ChatGeneration(
            message=AIMessage(content=content, **additional_kwargs),
            generation_info={"finish_reason": response.choices[0].finish_reason}
        )
        token_usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }
        return ChatResult(generations=[generation], llm_output={"token_usage": token_usage})
    
    def bind_tools(
        self,
        tools: Sequence[Union[Dict[str, Any], Type, Callable, BaseTool]],
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, BaseMessage]:
        """绑定工具到模型"""
        from langchain.tools.convert_to_openai import format_tool_to_openai_function
        
        zhipu_tools = []
        for tool in tools:
            if isinstance(tool, dict):
                if "type" in tool and tool["type"] == "function" and "function" in tool:
                    zhipu_tools.append(tool)
                else:
                    zhipu_tools.append({
                        "type": "function",
                        "function": tool
                    })
            elif isinstance(tool, type) and is_basemodel_subclass(tool):
                schema = tool.schema()
                zhipu_tools.append({
                    "type": "function",
                    "function": {
                        "name": schema.get("title", tool.__name__),
                        "description": schema.get("description", ""),
                        "parameters": schema
                    }
                })
            elif isinstance(tool, BaseTool):
                openai_function = format_tool_to_openai_function(tool)
                zhipu_tools.append({
                    "type": "function",
                    "function": {
                        "name": openai_function["name"],
                        "description": openai_function["description"],
                        "parameters": openai_function["parameters"]
                    }
                })
            else:
                raise ValueError(f"Tool type {type(tool)} not supported")
        
        new_model = self.clone()
        
        def _invoke(input: LanguageModelInput) -> BaseMessage:
            messages = []
            if isinstance(input, str):
                messages = [HumanMessage(content=input)]
            elif isinstance(input, list):
                messages = input
            else:
                raise ValueError(f"Input type {type(input)} not supported")
            
            tool_choice = kwargs.get("tool_choice", "auto")
            response_format = {"type": "json_object"}

            result = new_model._generate(
                messages=messages,
                tools=zhipu_tools,
                tool_choice=tool_choice,
                response_format=response_format
            )
            
            message = result.generations[0].message
            
            if hasattr(message, 'tool_calls') and message.tool_calls:
                return AIMessage(
                    content=message.content or "",
                    tool_calls=message.tool_calls
                )
            
            return message
        
        from langchain_core.runnables import RunnableLambda
        return RunnableLambda(_invoke)
    
    @property
    def _llm_type(self) -> str:
        return "zhipuai-chat"
    
    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
        }
    
    def clone(self) -> "ZhipuAIChat":
        return ZhipuAIChat(
            model_name=self.model_name,
            temperature=self.temperature,
            top_p=self.top_p,
            max_tokens=self.max_tokens,
            api_key=self.api_key
        )

    def with_structured_output(
        self,
        schema: Union[Dict[str, Any], Type[TypeBaseModel]],
        **kwargs: Any
    ) -> Runnable[LanguageModelInput, Any]:
        """添加结构化输出支持"""
        from langchain_core.output_parsers import JsonOutputParser
        from langchain_core.runnables import RunnableLambda
        
        new_model = self.clone()
        is_pydantic_schema = isinstance(schema, type) and issubclass(schema, BaseModel)
        
        if is_pydantic_schema:
            parser = JsonOutputParser(pydantic_object=schema)
        else:
            parser = JsonOutputParser()
        
        schema_json = None
        if is_pydantic_schema:
            schema_json = schema.schema()
        elif isinstance(schema, dict):
            schema_json = schema

        def _invoke(input: LanguageModelInput) -> Any:
            messages = []
            if isinstance(input, str):
                messages = [HumanMessage(content=input)]
            elif isinstance(input, list):
                messages = input
            else:
                raise ValueError(f"Input type {type(input)} not supported")
            
            if schema_json:
                for i, message in enumerate(messages):
                    if isinstance(message, SystemMessage):
                        schema_str = json.dumps(schema_json, ensure_ascii=False, indent=2)
                        format_instruction = f"""
请严格按照以下JSON格式返回结果：
{schema_str}

不要包含任何其他解释，只返回符合上述格式的JSON。
"""
                        messages[i] = SystemMessage(content=message.content + format_instruction)
                        break
            
            response_format = {"type": "json_object"}

            result = new_model._generate(
                messages=messages,
                response_format=response_format
            )
            
            content = result.generations[0].message.content
            
            try:
                cleaned_content = content
                if cleaned_content.startswith("```json"):
                    cleaned_content = cleaned_content.split("```json")[1]
                    if "```" in cleaned_content:
                        cleaned_content = cleaned_content.split("```")[0]
                elif "```" in cleaned_content:
                    parts = cleaned_content.split("```")
                    for part in parts:
                        if part.strip().startswith("{") or part.strip().startswith("["):
                            cleaned_content = part.strip()
                            break
                
                cleaned_content = cleaned_content.strip()
                parsed_content = parser.parse(cleaned_content)
                
                if is_pydantic_schema:
                    if not isinstance(parsed_content, schema):
                        if isinstance(parsed_content, dict):
                            try:
                                return schema(**parsed_content)
                            except Exception:
                                pass
                
                return parsed_content
            except Exception as e:
                print(f"解析错误: {e}")
                try:
                    data = json.loads(content)
                    if is_pydantic_schema:
                        try:
                            return schema(**data)
                        except Exception:
                            pass
                    return data
                except Exception:
                    return None
        
        return RunnableLambda(_invoke)


def init_chat_model(provider=None, **kwargs):
    """初始化聊天模型"""
    if provider == "zhipuai":
        return ZhipuAIChat(**kwargs)
    
    try:
        from langchain.chat_models import init_chat_model as original_init_chat_model
        return original_init_chat_model(provider=provider, **kwargs)
    except ImportError:
        raise ValueError(f"Provider {provider} not supported")

