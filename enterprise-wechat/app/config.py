"""配置管理模块"""
import os
from functools import lru_cache
from typing import Optional, List

import yaml
from pydantic import BaseModel


class WechatConfig(BaseModel):
    """企业微信配置"""
    corp_id: str = ""
    corp_secret: str = ""
    agent_id: str = ""
    callback_token: str = ""
    callback_aes_key: str = ""


class DatabaseConfig(BaseModel):
    """数据库配置"""
    url: str = "sqlite:///./wechat.db"


class LLMConfig(BaseModel):
    """LLM 大模型配置"""
    provider: str = "openai"  # openai, claude, ollama
    api_key: str = ""
    base_url: str = ""
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 2000


class RAGConfig(BaseModel):
    """RAG 知识库配置"""
    enabled: bool = False
    embedding_provider: str = "openai"  # openai, ollama
    embedding_api_key: str = ""
    embedding_base_url: str = ""
    collection_name: str = "knowledge_base"
    persist_directory: str = "./data/chromadb"
    similarity_threshold: float = 0.5


class AgentConfig(BaseModel):
    """Agent 智能助手配置"""
    enabled: bool = False
    use_rag: bool = True
    system_prompt: str = ""


class AppConfig(BaseModel):
    """应用配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False


class Config(BaseModel):
    """统一配置类"""
    wechat: WechatConfig = WechatConfig()
    database: DatabaseConfig = DatabaseConfig()
    llm: LLMConfig = LLMConfig()
    rag: RAGConfig = RAGConfig()
    agent: AgentConfig = AgentConfig()
    app: AppConfig = AppConfig()


def _load_yaml_config() -> Config:
    """从 YAML 文件加载配置"""
    config = Config()
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "config.yaml")

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
            if yaml_data:
                if "wechat" in yaml_data:
                    config.wechat = WechatConfig(**yaml_data["wechat"])
                if "database" in yaml_data:
                    config.database = DatabaseConfig(**yaml_data["database"])
                if "llm" in yaml_data:
                    config.llm = LLMConfig(**yaml_data["llm"])
                if "rag" in yaml_data:
                    config.rag = RAGConfig(**yaml_data["rag"])
                if "agent" in yaml_data:
                    config.agent = AgentConfig(**yaml_data["agent"])
                if "app" in yaml_data:
                    config.app = AppConfig(**yaml_data["app"])

    return config


def _load_env_config() -> Config:
    """从环境变量加载配置（优先级更高）"""
    config = Config()

    # 企业微信配置
    config.wechat.corp_id = os.getenv("CORP_ID", "")
    config.wechat.corp_secret = os.getenv("CORP_SECRET", "")
    config.wechat.agent_id = os.getenv("AGENT_ID", "")
    config.wechat.callback_token = os.getenv("CALLBACK_TOKEN", "")
    config.wechat.callback_aes_key = os.getenv("CALLBACK_AES_KEY", "")

    # 数据库配置
    config.database.url = os.getenv("DATABASE_URL", "sqlite:///./wechat.db")

    # LLM 配置
    config.llm.provider = os.getenv("LLM_PROVIDER", "openai")
    config.llm.api_key = os.getenv("LLM_API_KEY", "")
    config.llm.base_url = os.getenv("LLM_BASE_URL", "")
    config.llm.model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # RAG 配置
    config.rag.enabled = os.getenv("RAG_ENABLED", "false").lower() == "true"
    config.rag.embedding_provider = os.getenv("EMBEDDING_PROVIDER", "openai")
    config.rag.embedding_api_key = os.getenv("EMBEDDING_API_KEY", "")
    config.rag.embedding_base_url = os.getenv("EMBEDDING_BASE_URL", "")
    config.rag.collection_name = os.getenv("RAG_COLLECTION", "knowledge_base")
    config.rag.persist_directory = os.getenv("RAG_PERSIST_DIR", "./data/chromadb")

    # Agent 配置
    config.agent.enabled = os.getenv("AGENT_ENABLED", "false").lower() == "true"
    config.agent.use_rag = os.getenv("AGENT_USE_RAG", "true").lower() == "true"

    # 应用配置
    config.app.host = os.getenv("APP_HOST", "0.0.0.0")
    config.app.port = int(os.getenv("APP_PORT", "8000"))
    config.app.debug = os.getenv("APP_DEBUG", "false").lower() == "true"

    return config


@lru_cache()
def get_config() -> Config:
    """获取配置单例（优先从环境变量读取，环境变量为空时从 YAML 读取）"""
    env_config = _load_env_config()

    # 如果环境变量中有配置，使用环境变量
    if env_config.wechat.corp_id and env_config.wechat.corp_secret:
        return env_config

    # 否则使用 YAML 配置
    yaml_config = _load_yaml_config()

    # 合并配置（环境变量优先）
    if not env_config.wechat.corp_id:
        env_config.wechat.corp_id = yaml_config.wechat.corp_id
    if not env_config.wechat.corp_secret:
        env_config.wechat.corp_secret = yaml_config.wechat.corp_secret
    if not env_config.wechat.agent_id:
        env_config.wechat.agent_id = yaml_config.wechat.agent_id
    if not env_config.wechat.callback_token:
        env_config.wechat.callback_token = yaml_config.wechat.callback_token
    if not env_config.wechat.callback_aes_key:
        env_config.wechat.callback_aes_key = yaml_config.wechat.callback_aes_key

    if not env_config.database.url or env_config.database.url == "sqlite:///./wechat.db":
        env_config.database.url = yaml_config.database.url

    # LLM 配置合并
    if not env_config.llm.api_key:
        env_config.llm.api_key = yaml_config.llm.api_key
    if not env_config.llm.model:
        env_config.llm.model = yaml_config.llm.model
    if not env_config.llm.provider:
        env_config.llm.provider = yaml_config.llm.provider

    # RAG 配置合并
    if not env_config.rag.embedding_api_key:
        env_config.rag.embedding_api_key = yaml_config.rag.embedding_api_key

    if env_config.app.host == "0.0.0.0":
        env_config.app.host = yaml_config.app.host
    if env_config.app.port == 8000:
        env_config.app.port = yaml_config.app.port

    return env_config