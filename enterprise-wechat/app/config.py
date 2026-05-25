"""配置管理模块"""
import os
from functools import lru_cache
from typing import Optional

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


class AppConfig(BaseModel):
    """应用配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False


class Config(BaseModel):
    """统一配置类"""
    wechat: WechatConfig = WechatConfig()
    database: DatabaseConfig = DatabaseConfig()
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

    if env_config.app.host == "0.0.0.0":
        env_config.app.host = yaml_config.app.host
    if env_config.app.port == 8000:
        env_config.app.port = yaml_config.app.port

    return env_config