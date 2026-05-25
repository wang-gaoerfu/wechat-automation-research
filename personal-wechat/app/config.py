"""Configuration management for Personal WeChat."""
import os
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class WCFConfig(BaseModel):
    """WeChatFerry configuration."""
    host: str = "localhost"
    port: int = 10086
    reconnect_interval: int = 30
    max_reconnect_attempts: int = 5


class RestHoursConfig(BaseModel):
    """Rest hours configuration for anti-ban."""
    start: int = 2
    end: int = 6


class AntiBanConfig(BaseModel):
    """Anti-ban settings."""
    daily_message_limit: int = 500
    min_send_interval: int = 3
    rest_hours: RestHoursConfig = RestHoursConfig()


class LLMConfig(BaseModel):
    """LLM 大模型配置"""
    provider: str = "sensenova"  # sensenova, openai, ollama
    api_key: str = ""
    base_url: str = ""
    model: str = "sensenova-6.7-flash-lite"
    temperature: float = 0.7
    max_tokens: int = 2000


class RAGConfig(BaseModel):
    """RAG 知识库配置"""
    enabled: bool = False
    embedding_provider: str = "sensenova"
    embedding_api_key: str = ""
    embedding_base_url: str = ""
    collection_name: str = "knowledge_base"
    persist_directory: str = "./data/chromadb"
    similarity_threshold: float = 0.5


class DatabaseConfig(BaseModel):
    """Database configuration."""
    url: str = "sqlite:///./personal_wechat.db"


class AppConfig(BaseModel):
    """Application server configuration."""
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = False
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]


class Settings(BaseSettings):
    """Main settings class combining all configurations."""
    wcf: WCFConfig = WCFConfig()
    anti_ban: AntiBanConfig = AntiBanConfig()
    llm: LLMConfig = LLMConfig()
    rag: RAGConfig = RAGConfig()
    database: DatabaseConfig = DatabaseConfig()
    app: AppConfig = AppConfig()

    class Config:
        env_prefix = ""
        env_file = ".env"
        env_nested_delimiter = "__"


def load_config_from_yaml(config_path: Optional[str] = None) -> Settings:
    """Load configuration from YAML file."""
    if config_path is None:
        config_dir = Path(__file__).parent.parent / "config"
        config_path = config_dir / "config.yaml"

    settings = Settings()

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f)

        if yaml_config:
            if "wcf" in yaml_config:
                settings.wcf = WCFConfig(**yaml_config["wcf"])
            if "anti_ban" in yaml_config:
                ab_config = yaml_config["anti_ban"]
                if "rest_hours" in ab_config:
                    ab_config["rest_hours"] = RestHoursConfig(**ab_config["rest_hours"])
                settings.anti_ban = AntiBanConfig(**ab_config)
            if "llm" in yaml_config:
                settings.llm = LLMConfig(**yaml_config["llm"])
            if "rag" in yaml_config:
                settings.rag = RAGConfig(**yaml_config["rag"])
            if "database" in yaml_config:
                settings.database = DatabaseConfig(**yaml_config["database"])
            if "app" in yaml_config:
                settings.app = AppConfig(**yaml_config["app"])

    # Override with environment variables if present
    wcf_host = os.getenv("WCF_HOST")
    if wcf_host:
        settings.wcf.host = wcf_host

    wcf_port = os.getenv("WCF_PORT")
    if wcf_port:
        settings.wcf.port = int(wcf_port)

    reconnect_interval = os.getenv("WCF_RECONNECT_INTERVAL")
    if reconnect_interval:
        settings.wcf.reconnect_interval = int(reconnect_interval)

    max_reconnect = os.getenv("WCF_MAX_RECONNECT_ATTEMPTS")
    if max_reconnect:
        settings.wcf.max_reconnect_attempts = int(max_reconnect)

    daily_limit = os.getenv("ANTI_BAN_DAILY_MESSAGE_LIMIT")
    if daily_limit:
        settings.anti_ban.daily_message_limit = int(daily_limit)

    min_send_interval = os.getenv("ANTI_BAN_MIN_SEND_INTERVAL")
    if min_send_interval:
        settings.anti_ban.min_send_interval = int(min_send_interval)

    rest_start = os.getenv("ANTI_BAN_REST_START")
    if rest_start:
        settings.anti_ban.rest_hours.start = int(rest_start)

    rest_end = os.getenv("ANTI_BAN_REST_END")
    if rest_end:
        settings.anti_ban.rest_hours.end = int(rest_end)

    # LLM 配置
    llm_provider = os.getenv("LLM_PROVIDER")
    if llm_provider:
        settings.llm.provider = llm_provider

    llm_api_key = os.getenv("LLM_API_KEY")
    if llm_api_key:
        settings.llm.api_key = llm_api_key

    llm_base_url = os.getenv("LLM_BASE_URL")
    if llm_base_url:
        settings.llm.base_url = llm_base_url

    llm_model = os.getenv("LLM_MODEL")
    if llm_model:
        settings.llm.model = llm_model

    # RAG 配置
    rag_enabled = os.getenv("RAG_ENABLED")
    if rag_enabled:
        settings.rag.enabled = rag_enabled.lower() == "true"

    rag_api_key = os.getenv("RAG_API_KEY")
    if rag_api_key:
        settings.rag.embedding_api_key = rag_api_key

    db_url = os.getenv("DATABASE_URL")
    if db_url:
        settings.database.url = db_url

    cors_origins = os.getenv("CORS_ORIGINS")
    if cors_origins:
        settings.app.cors_origins = [o.strip() for o in cors_origins.split(",")]

    return settings


# Global settings instance
settings = load_config_from_yaml()