"""LLM 服务 - 支持 OpenAI / Claude / 本地模型"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncIterator
from dataclasses import dataclass
import json

import httpx

from app.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """对话消息"""
    role: str  # system, user, assistant
    content: str


class LLMProvider(ABC):
    """LLM provider 抽象基类"""

    @abstractmethod
    async def chat(self, messages: List[Message], **kwargs) -> str:
        """发送对话请求"""
        pass

    @abstractmethod
    async def chat_stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """流式对话请求"""
        pass


class OpenAILLM(LLMProvider):
    """OpenAI LLM 实现"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        timeout: float = 60.0
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def chat(self, messages: List[Message], **kwargs) -> str:
        """OpenAI 对话请求"""
        model = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 2000)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def chat_stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """OpenAI 流式对话请求"""
        model = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", 0.7)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": True
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except json.JSONDecodeError:
                            continue


class ClaudeLLM(LLMProvider):
    """Claude LLM 实现（Anthropic）"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.anthropic.com/v1",
        model: str = "claude-sonnet-4-20250514",
        timeout: float = 60.0
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def chat(self, messages: List[Message], **kwargs) -> str:
        """Claude 对话请求"""
        model = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 2000)

        # 构建 Anthropic 格式的消息
        anthropic_messages = []
        for m in messages:
            if m.role == "system":
                continue  # Claude 使用特殊的 system 消息格式
            anthropic_messages.append({
                "role": m.role,
                "content": m.content
            })

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        payload = {
            "model": model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # 添加 system prompt
        for m in messages:
            if m.role == "system":
                payload["system"] = m.content
                break

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]

    async def chat_stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """Claude 流式对话请求"""
        model = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", 0.7)

        anthropic_messages = []
        for m in messages:
            if m.role == "system":
                continue
            anthropic_messages.append({
                "role": m.role,
                "content": m.content
            })

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        payload = {
            "model": model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": 1024,
            "stream": True
        }

        for m in messages:
            if m.role == "system":
                payload["system"] = m.content
                break

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/messages",
                headers=headers,
                json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data.get("delta", {})
                            if "text" in delta:
                                yield delta["text"]
                        except json.JSONDecodeError:
                            continue


class OllamaLLM(LLMProvider):
    """Ollama 本地模型实现"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
        timeout: float = 120.0
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def chat(self, messages: List[Message], **kwargs) -> str:
        """Ollama 对话请求"""
        model = kwargs.get("model", self.model)

        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]

    async def chat_stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """Ollama 流式对话请求"""
        model = kwargs.get("model", self.model)

        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                yield data["message"]["content"]
                        except json.JSONDecodeError:
                            continue


class SenseNovaLLM(LLMProvider):
    """SenseNova 大模型实现（商汤科技）"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://token.sensenova.cn/v1",
        model: str = "sensenova-6.7-flash-lite",
        timeout: float = 60.0
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def chat(self, messages: List[Message], **kwargs) -> str:
        """SenseNova 对话请求"""
        model = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 2000)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def chat_stream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """SenseNova 流式对话请求"""
        model = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", 0.7)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": True
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except json.JSONDecodeError:
                            continue


class LLMService:
    """LLM 服务管理器"""

    _instance: Optional["LLMService"] = None

    def __init__(self):
        self._provider: Optional[LLMProvider] = None
        self._provider_type: str = ""
        self._initialized = False

    @classmethod
    def get_instance(cls) -> "LLMService":
        """获取单例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化 LLM 服务

        Args:
            config: LLM 配置字典，包含:
                - provider: "openai" | "claude" | "ollama" | "sensenova"
                - api_key: API 密钥（openai/claude/sensenova）
                - base_url: API 地址（可选，默认使用官方地址）
                - model: 模型名称
        """
        provider = config.get("provider", "openai")
        api_key = config.get("api_key", "")
        base_url = config.get("base_url", "")
        model = config.get("model", "")

        if provider == "openai":
            self._provider = OpenAILLM(
                api_key=api_key,
                base_url=base_url or "https://api.openai.com/v1",
                model=model or "gpt-4o-mini"
            )
            self._provider_type = "openai"
        elif provider == "claude":
            self._provider = ClaudeLLM(
                api_key=api_key,
                base_url=base_url or "https://api.anthropic.com/v1",
                model=model or "claude-sonnet-4-20250514"
            )
            self._provider_type = "claude"
        elif provider == "ollama":
            self._provider = OllamaLLM(
                base_url=base_url or "http://localhost:11434",
                model=model or "llama3.2"
            )
            self._provider_type = "ollama"
        elif provider == "sensenova":
            self._provider = SenseNovaLLM(
                api_key=api_key,
                base_url=base_url or "https://token.sensenova.cn/v1",
                model=model or "sensenova-6.7-flash-lite"
            )
            self._provider_type = "sensenova"
        else:
            raise ValueError(f"不支持的 LLM provider: {provider}")

        self._initialized = True
        logger.info(f"LLM 服务初始化完成: {self._provider_type}")

    async def chat(
        self,
        user_message: str,
        system_prompt: str = "",
        history: Optional[List[Message]] = None,
        **kwargs
    ) -> str:
        """发送对话请求

        Args:
            user_message: 用户消息
            system_prompt: 系统提示词
            history: 对话历史
            **kwargs: 其他参数（temperature, max_tokens 等）

        Returns:
            LLM 回复
        """
        if not self._initialized:
            raise RuntimeError("LLM 服务未初始化")

        messages = []
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        if history:
            messages.extend(history)
        messages.append(Message(role="user", content=user_message))

        return await self._provider.chat(messages, **kwargs)

    async def chat_stream(
        self,
        user_message: str,
        system_prompt: str = "",
        history: Optional[List[Message]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """流式对话请求"""
        if not self._initialized:
            raise RuntimeError("LLM 服务未初始化")

        messages = []
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        if history:
            messages.extend(history)
        messages.append(Message(role="user", content=user_message))

        async for chunk in self._provider.chat_stream(messages, **kwargs):
            yield chunk

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized

    @property
    def provider_type(self) -> str:
        """获取 provider 类型"""
        return self._provider_type


# 全局单例
llm_service = LLMService.get_instance()