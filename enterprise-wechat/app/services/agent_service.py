"""Agent 服务 - MCP 协议智能助手"""
import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from app.services.llm_service import llm_service, Message
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    """工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Any


@dataclass
class ToolCall:
    """工具调用"""
    tool_name: str
    arguments: Dict[str, Any]


@dataclass
class AgentResponse:
    """Agent 响应"""
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    raw_response: Optional[Dict[str, Any]] = None


class MCPServer:
    """MCP Server - 工具服务器基类"""

    def __init__(self, name: str):
        self.name = name
        self._tools: Dict[str, Tool] = {}

    def register_tool(self, tool: Tool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool

    def get_tools(self) -> List[Dict[str, Any]]:
        """获取工具列表"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
            for tool in self._tools.values()
        ]

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """执行工具"""
        if tool_name not in self._tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        return await self._tools[tool_name].handler(arguments)


class WeChatMCPFunctions:
    """企业微信 MCP 函数库"""

    def __init__(self, message_service=None):
        self._message_service = message_service

    async def send_message(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """发送消息"""
        if not self._message_service:
            return {"success": False, "error": "Message service not initialized"}

        user_id = args.get("user_id")
        content = args.get("content")
        msg_type = args.get("msg_type", "text")

        if not user_id or not content:
            return {"success": False, "error": "Missing user_id or content"}

        try:
            if msg_type == "text":
                result = await self._message_service.send_text(user_id, content)
            elif msg_type == "markdown":
                result = await self._message_service.send_markdown(user_id, content)
            else:
                return {"success": False, "error": f"Unsupported msg_type: {msg_type}"}

            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def query_customer(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """查询客户信息"""
        customer_id = args.get("customer_id")
        if not customer_id:
            return {"success": False, "error": "Missing customer_id"}

        # 这里应该调用客户服务的查询方法
        return {
            "success": True,
            "customer_id": customer_id,
            "customer_name": "客户",
            "tags": ["标签1", "标签2"]
        }

    async def search_knowledge(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """搜索知识库"""
        query = args.get("query")
        if not query:
            return {"success": False, "error": "Missing query"}

        try:
            results = await rag_service.search(query, top_k=5)
            return {
                "success": True,
                "results": results,
                "count": len(results)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def add_knowledge(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """添加知识"""
        content = args.get("content")
        source = args.get("source", "manual")
        category = args.get("category", "general")

        if not content:
            return {"success": False, "error": "Missing content"}

        try:
            doc_id = await rag_service.add_documents([{
                "content": content,
                "metadata": {"source": source, "category": category}
            }])
            return {"success": True, "doc_id": doc_id[0]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_customer_list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """获取客户列表"""
        page = args.get("page", 1)
        page_size = args.get("page_size", 20)

        # 这里应该调用客户服务的列表方法
        return {
            "success": True,
            "customers": [],
            "total": 0,
            "page": page,
            "page_size": page_size
        }


class AgentService:
    """Agent 服务 - 智能助手核心"""

    _instance: Optional["AgentService"] = None

    def __init__(self):
        self._mcp_servers: Dict[str, MCPServer] = {}
        self._initialized = False
        self._system_prompt = """你是一个智能微信运营助手，可以通过工具来帮助用户完成以下任务：
- 发送消息给客户
- 查询客户信息
- 搜索知识库
- 管理知识库

当用户请求发送消息或查询信息时，你应该调用相应的工具。

注意：
1. 每次只能调用一个工具
2. 工具参数必须完整
3. 如果工具执行失败，告诉用户错误原因"""

    @classmethod
    def get_instance(cls) -> "AgentService":
        """获取单例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(
        self,
        config: Dict[str, Any],
        message_service=None
    ) -> None:
        """初始化 Agent 服务

        Args:
            config: Agent 配置
            message_service: 消息服务实例
        """
        # 注册 MCP Server
        wechat_server = MCPServer(name="wechat")

        # 创建 WeChat 函数库
        wechat_functions = WeChatMCPFunctions(message_service)

        # 注册工具
        wechat_server.register_tool(Tool(
            name="send_message",
            description="发送消息给微信用户",
            parameters={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "用户 ID"},
                    "content": {"type": "string", "description": "消息内容"},
                    "msg_type": {"type": "string", "description": "消息类型: text 或 markdown"}
                },
                "required": ["user_id", "content"]
            },
            handler=wechat_functions.send_message
        ))

        wechat_server.register_tool(Tool(
            name="query_customer",
            description="查询客户信息",
            parameters={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "客户 ID"}
                },
                "required": ["customer_id"]
            },
            handler=wechat_functions.query_customer
        ))

        wechat_server.register_tool(Tool(
            name="search_knowledge",
            description="搜索知识库内容",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"}
                },
                "required": ["query"]
            },
            handler=wechat_functions.search_knowledge
        ))

        wechat_server.register_tool(Tool(
            name="add_knowledge",
            description="添加内容到知识库",
            parameters={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "要添加的内容"},
                    "source": {"type": "string", "description": "来源"},
                    "category": {"type": "string", "description": "分类"}
                },
                "required": ["content"]
            },
            handler=wechat_functions.add_knowledge
        ))

        wechat_server.register_tool(Tool(
            name="get_customer_list",
            description="获取客户列表",
            parameters={
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "description": "页码"},
                    "page_size": {"type": "integer", "description": "每页数量"}
                }
            },
            handler=wechat_functions.get_customer_list
        ))

        self._mcp_servers["wechat"] = wechat_server

        # 初始化 LLM 服务
        llm_config = config.get("llm", {})
        if llm_config:
            llm_service.initialize(llm_config)

        # 初始化 RAG 服务
        rag_config = config.get("rag", {})
        if rag_config:
            rag_service.initialize(rag_config)

        self._initialized = True
        logger.info("Agent 服务初始化完成")

    async def process_message(
        self,
        user_message: str,
        user_id: str = "",
        use_rag: bool = True,
        conversation_history: Optional[List[Message]] = None
    ) -> AgentResponse:
        """处理用户消息

        Args:
            user_message: 用户消息
            user_id: 用户 ID（用于上下文）
            use_rag: 是否使用 RAG 检索
            conversation_history: 对话历史

        Returns:
            AgentResponse
        """
        if not self._initialized:
            return AgentResponse(content="Agent 服务未初始化")

        # 如果启用 RAG，先检索知识库
        context = ""
        if use_rag and rag_service.is_initialized():
            try:
                context = await rag_service.get_relevant_context(
                    user_message,
                    context_length=3,
                    similarity_threshold=0.5
                )
            except Exception as e:
                logger.error(f"RAG 检索失败: {e}")

        # 构建提示词
        prompt = self._build_prompt(user_message, context, user_id)

        # 调用 LLM
        if not llm_service.is_initialized():
            return AgentResponse(content="LLM 服务未初始化")

        response_text = await llm_service.chat(
            user_message=prompt,
            system_prompt=self._system_prompt,
            history=conversation_history or []
        )

        # 解析工具调用
        tool_calls = self._parse_tool_calls(response_text)

        # 执行工具调用
        results = []
        for tool_call in tool_calls:
            result = await self._execute_tool_call(tool_call)
            results.append(result)

        # 构建最终响应
        final_content = response_text
        if results:
            # 将工具执行结果添加到响应
            result_summary = "\n\n".join([
                f"工具 {r['tool_name']} 执行结果: {r['result']}"
                for r in results if r.get("success")
            ])
            if result_summary:
                final_content = f"{response_text}\n\n{result_summary}"

        return AgentResponse(
            content=final_content,
            tool_calls=tool_calls,
            raw_response={"results": results}
        )

    def _build_prompt(self, user_message: str, context: str, user_id: str) -> str:
        """构建提示词"""
        prompt_parts = []

        if context:
            prompt_parts.append(f"【知识库上下文】\n{context}\n")

        if user_id:
            prompt_parts.append(f"【当前用户】{user_id}")

        prompt_parts.append(f"【用户请求】\n{user_message}")

        return "\n\n".join(prompt_parts)

    def _parse_tool_calls(self, text: str) -> List[ToolCall]:
        """从 LLM 输出中解析工具调用

        支持格式:
        1. JSON: {"tool": "send_message", "args": {"user_id": "xxx", "content": "xxx"}}
        2. 自然语言描述
        """
        tool_calls = []

        # 尝试 JSON 格式
        try:
            # 查找 JSON 对象
            import re
            json_matches = re.findall(r'\{[^{}]*"tool"[^{}]*\}', text)
            for match in json_matches:
                try:
                    data = json.loads(match)
                    if "tool" in data:
                        tool_calls.append(ToolCall(
                            tool_name=data["tool"],
                            arguments=data.get("args", {})
                        ))
                except json.JSONDecodeError:
                    continue
        except Exception:
            pass

        return tool_calls

    async def _execute_tool_call(self, tool_call: ToolCall) -> Dict[str, Any]:
        """执行工具调用"""
        for server in self._mcp_servers.values():
            if tool_call.tool_name in [t.name for t in server.get_tools()]:
                try:
                    result = await server.execute_tool(
                        tool_call.tool_name,
                        tool_call.arguments
                    )
                    return {
                        "tool_name": tool_call.tool_name,
                        "success": result.get("success", False),
                        "result": result
                    }
                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    return {
                        "tool_name": tool_call.tool_name,
                        "success": False,
                        "error": str(e)
                    }

        return {
            "tool_name": tool_call.tool_name,
            "success": False,
            "error": f"Tool not found: {tool_call.tool_name}"
        }

    def get_available_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取所有可用工具"""
        return {
            server.name: server.get_tools()
            for server in self._mcp_servers.values()
        }

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized


# 全局单例
agent_service = AgentService.get_instance()