# 企业微信自动化 - 完整设计方案

**调研日期**: 2026-05-24
**版本**: v2.0 (完整版)
**技术栈**: Python + FastAPI + SQLite + ChromaDB + 企业微信官方API

---

## 一、架构设计

```
                                    +--------------------+
                                    |                    |
                                    |   发布系统         |
                                    |   (CMS/Database)   |
                                    |                    |
                                    +--------+-----------+
                                             |
                                             | Polling/Webhook
                                             v
+----------------+                    +--------+-----------+                    +------------------+
|                |                    |                    |                    |                  |
|  企业微信       |<----------------->|   FastAPI Server   |<----------------->|  ChromaDB        |
|  平台          |<----------------->|   (Python/FastAPI) |<----------------->|  (向量存储)      |
|                |                    |                    |                    |                  |
+----------------+                    +--------+-----------+                    +------------------+
       |                                      │                                      |
       |                                      │                                      |
       v                                      v                                      v
+----------------+                    +--------+-----------+                    +------------------+
|                |                    |                    |                    |                  |
|  客户联系API    |                    |   SQLite 数据库    |                    |  LLM 服务        |
|  (加好友/管理)  |                    |   (元数据/日志)    |                    |  (DeepSeek/     |
+----------------+                    +--------+-----------+                    +   OpenAI)       |
                                      |                                      +------------------+
                                      ▼
                              +------------------+
                              |  基础设施服务     |
                              |                  |
                              | • Token管理器    |
                              | • 消息去重       |
                              | • 操作审计       |
                              | • 健康检查       |
                              | • 热更新配置     |
                              | • 数据备份       |
                              +------------------+
```

---

## 二、三大核心功能模块

### 模块1: 自动加好友

**实现方式**: 企业微信「客户联系」功能 + API

**流程**:
```
[潜在客户扫码/点击链接]
        │
        ▼
[创建"联系我"二维码] ──► [设置欢迎语]
        │
        ▼
[客户扫码添加] ──► [企业微信回调事件: add_external_contact]
        │
        ▼
[自动通过 + 发送欢迎语] ──► [自动打标签]
        │
        ▼
[入库: external_contact + user_id 关联]
```

**关键API**:

| API | 端点 | 说明 |
|-----|------|------|
| 创建联系我二维码 | `POST /externalcontact/add_contact_way` | 生成获客二维码 |
| 获取客户列表 | `GET /externalcontact/list?userid={userid}` | 获取员工的所有客户 |
| 获取客户详情 | `GET /externalcontact/get?external_userid={id}` | 获取客户详细信息 |
| 配置客户标签 | `POST /externalcontact/edit_company_contact_data` | 打标签 |
| 发送欢迎语 | 调用 `message/send` 发送 | 新客户添加后自动发送 |

**"联系我"二维码创建示例**:
```json
POST /externalcontact/add_contact_way
{
  "type": 2,
  "scene": 2,
  "style": 1,
  "remark": "获客二维码",
  "skip_verify": true,
  "state": "campaign_001",
  "user": ["USERID1", "USERID2"],
  "partyid": []
}
```

**回调事件处理**:
```python
# 监听事件: add_external_contact (新客户添加)
async def handle_add_external_contact(event):
    external_user_id = event.get("ExternalUserID")
    user_id = event.get("UserID")  # 员工ID

    # 1. 获取客户详情
    customer = await wechat_service.get_customer(external_user_id)

    # 2. 发送欢迎语
    welcome_msg = f"您好{customer['name']}，感谢添加！有什么可以帮您？"
    await wechat_service.send_message(user_id, welcome_msg)

    # 3. 自动打标签
    await wechat_service.add_tag(external_user_id, "新客户")

    # 4. 写入数据库
    await db.customers.create({
        "external_id": external_user_id,
        "user_id": user_id,
        "name": customer['name'],
        "tags": ["新客户"]
    })
```

---

### 模块2: 自动给好友发消息

**触发方式分类**:

| 触发类型 | 实现方式 | 频率限制 |
|---------|---------|---------|
| 欢迎语 | 新客户添加时自动发送 | 无限制 |
| 关键词回复 | 收到消息后匹配回复 | 无限制 |
| 定时群发 | 按cron表达式发送 | **每天最多4次/客户** |
| 事件触发 | 发布系统更新时推送 | 受20次/分钟限制 |

**消息发送API**:
```python
# 发送给指定客户
POST /message/send
{
  "touser": "EXTERNAL_USER_ID",
  "msgtype": "text",
  "agentid": 1000002,
  "text": {"content": "消息内容"}
}
```

**群发助手API (每天4次限制)**:
```python
# 按标签群发
POST /message/send_all
{
  "filter": {"tag_id": "TAG_ID"},
  "msgtype": "text",
  "text": {"content": "群发内容"}
}

# 全量群发
{
  "filter": {"is_to_all": true},
  "msgtype": "text",
  "text": {"content": "群发内容"}
}
```

**发布系统触发推送**:
```python
class PublishNotificationService:
    async def notify_customers_about_new_article(self, article: dict):
        """当发布系统有新内容时，推送给相关客户"""
        customers = await self.get_customers_by_tags(["已订阅"])

        for customer in customers:
            try:
                message = self._build_article_message(article)
                await self.wechat_service.send_text(
                    customer["external_id"],
                    message
                )
                # 添加延迟避免超过20次/分钟限制
                await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"发送失败: {customer['external_id']}, {e}")
```

---

### 模块3: 群里自动回复

**重要**: 群机器人Webhook只能**推送**，无法被动接收。需要配置**应用消息回调**来接收群消息。

**群消息接收架构**:
```
[用户在群中@应用]
        │
        ▼
[企业微信回调URL] ──► [解析消息内容]
        │
        ▼
[关键词匹配 或 LLM处理]
        │
        ▼
[通过应用消息发送回群]
```

**回调配置**:
- 管理后台 → 应用管理 → 选择应用 → 接收消息 → 配置回调URL
- 需要提供Token和EncodingAESKey

**群消息回调格式**:
```xml
<xml>
  <ToUserName><![CDATA[toUser]]></ToUserName>
  <FromUserName><![CDATA[fromUser]]></FromUserName>
  <CreateTime>1348831860</CreateTime>
  <MsgType><![CDATA[text]]></MsgType>
  <Content><![CDATA[用户发送的内容]]></Content>
  <MsgId>1234567890</MsgId>
  <AgentID>1000002</AgentID>
  <GroupCode><![CDATA[GROUP_ID]]></GroupCode>
</xml>
```

**群内@应用自动回复实现**:
```python
async def handle_group_message(msg_dict: dict):
    content = msg_dict.get("Content", "")
    group_id = msg_dict.get("GroupCode", "")
    from_user = msg_dict.get("FromUserName", "")

    # 检查是否是@应用的消息
    if "@arthur" not in content:
        return

    # 去除@部分，获取实际查询内容
    query = content.replace("@arthur", "").strip()

    if not query:
        return

    # 消息去重检查
    msg_id = msg_dict.get("MsgId")
    if self.dedup_check.is_duplicate(msg_id):
        return

    # RAG检索
    rag_context = await self.knowledge_base.get_context_string(query, top_k=3)

    # LLM生成回复
    response = await self.ai_service.generate_with_rag(query, rag_context)

    # 发送回复到群
    await self.wechat_service.send_group_message(
        group_id=group_id,
        content=response
    )
```

---

## 三、API频率限制表

### 消息发送限制

| API | 限制 | 说明 |
|-----|------|------|
| `message/send` (发消息给客户) | 100次/分钟/人 | 发送给单个用户 |
| `message/send_all` (群发) | **每天4次/客户** | 给同一客户每天最多4次群发 |
| `message/send` (群聊) | 100次/分钟 | 通过chatid发送 |
| 主动发消息给外部联系人 | **20次/分钟/企业** | 超过会提示"操作频繁" |

### 客户联系限制

| 功能 | 限制 |
|-----|------|
| 单个企业员工好友数 | 无明确上限，超过5000需升级 |
| 单个企业客户总数 | 无上限 |
| `add_contact_way` (创建二维码) | 100个/企业 |
| 每日新增客户数 | 无明确限制，但异常会被风控 |

### 群相关限制

| 功能 | 限制 |
|-----|------|
| 群数量 | 无明确限制 |
| 群成员数 | 上限200人（标准）/ 500人（付费） |
| 群机器人 | 每个群最多1个机器人 |

### 风控规则

| 行为 | 风险等级 | 说明 |
|------|---------|------|
| 同一条内容大量群发 | 高 | 内容要多样化，避免完全相同 |
| 新客户立即大量发送 | 高 | 建议先正常互动几天 |
| 被客户举报 | 极高 | 直接封禁 |
| 高频操作 | 中 | 操作太快会被限制，需加延迟 |
| 批量添加好友 | 高 | 会被风控检测 |

---

## 四、基础设施服务

### 4.1 Token自动刷新机制

```python
# app/services/token_manager.py
import time
import asyncio
from datetime import datetime

class WeChatTokenManager:
    """企业微信Access Token管理器 - 自动刷新"""

    def __init__(self, corp_id: str, corp_secret: str):
        self.corp_id = corp_id
        self.corp_secret = corp_secret
        self._token = None
        self._expires_at = 0
        self.base_url = "https://qyapi.weixin.qq.com/cgi-bin/"

    async def get_token(self) -> str:
        """获取access_token，自动处理刷新"""
        if time.time() >= self._expires_at - 300:  # 提前5分钟刷新
            await self._refresh_token()
        return self._token

    async def _refresh_token(self):
        """刷新access_token"""
        url = f"{self.base_url}gettoken"
        params = {
            "corpid": self.corp_id,
            "corpsecret": self.corp_secret
        }

        async with self.http_client.get(url, params=params) as resp:
            data = await resp.json()

            if data.get("errcode") == 0:
                self._token = data["access_token"]
                # 企业微信token有效期2小时
                self._expires_at = time.time() + data.get("expires_in", 7200)
                logger.info(f"Token刷新成功，有效期到: {self._expires_at}")
            else:
                raise Exception(f"Token刷新失败: {data}")

    async def get_token_with_retry(self, max_retries: int = 3) -> str:
        """带重试的token获取"""
        for attempt in range(max_retries):
            try:
                return await self.get_token()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = 2 ** attempt
                logger.warning(f"Token获取失败，{wait_time}秒后重试: {e}")
                await asyncio.sleep(wait_time)
```

### 4.2 消息去重机制

```python
# app/services/message_dedup.py
import time
from collections import defaultdict

class MessageDeduplicator:
    """消息去重 - 防止重复处理同一消息"""

    def __init__(self, cache_ttl: int = 3600):
        self.seen = defaultdict(dict)
        self.cache_ttl = cache_ttl

    def is_duplicate(self, msg_id: str) -> bool:
        """检查是否重复"""
        if not msg_id:
            return False

        current_time = time.time()

        if msg_id in self.seen:
            if current_time - self.seen[msg_id] < self.cache_ttl:
                return True
            del self.seen[msg_id]

        self.seen[msg_id] = current_time
        return False

    def cleanup_expired(self):
        """清理过期记录"""
        current_time = time.time()
        expired = [
            msg_id for msg_id, timestamp in self.seen.items()
            if current_time - timestamp >= self.cache_ttl
        ]

        for msg_id in expired:
            del self.seen[msg_id]
```

### 4.3 操作审计日志

```sql
-- 审计日志表
CREATE TABLE audit_logs (
    id TEXT PRIMARY KEY,
    operator_type TEXT,                   -- system, ai, manual
    operator_id TEXT,
    action_type TEXT,                     -- send_message, add_friend, etc
    target_type TEXT,                     -- contact, group, customer
    target_id TEXT,
    content_preview TEXT,                  -- 内容预览（脱敏）
    ip_address TEXT,
    user_agent TEXT,
    risk_level INTEGER,
    status TEXT,                          -- success, failed
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_operator (operator_id),
    INDEX idx_action_type (action_type),
    INDEX idx_created_at (created_at)
);
```

```python
# app/services/audit_logger.py
import json
from datetime import datetime

class AuditLogger:
    """操作审计日志服务"""

    def __init__(self, db):
        self.db = db

    def log(self, operator_type: str, operator_id: str,
           action_type: str, target_type: str, target_id: str,
           content: str = None, status: str = "success",
           risk_level: int = 0, error_msg: str = None):
        """记录操作日志"""

        # 内容脱敏
        content_preview = self._mask_sensitive(content) if content else None

        log_entry = AuditLog(
            operator_type=operator_type,
            operator_id=operator_id,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            content_preview=content_preview,
            risk_level=risk_level,
            status=status,
            error_message=error_msg,
            created_at=datetime.now()
        )

        self.db.add(log_entry)
        self.db.commit()

    def _mask_sensitive(self, content: str) -> str:
        """敏感信息脱敏"""
        import re

        # 手机号脱敏: 138xxxx1234
        content = re.sub(
            r'1[3-9]\d{9}',
            lambda m: m.group()[:3] + "****" + m.group()[-4:],
            content
        )

        # 身份证脱敏
        content = re.sub(
            r'\d{17}[\dXx]',
            lambda m: m.group()[:6] + "****" + m.group()[-4:],
            content
        )

        return content[:200] if len(content) > 200 else content
```

### 4.4 健康检查与告警

```python
# app/services/health_check.py
from collections import defaultdict
from datetime import datetime

class HealthCheckService:
    """健康检查与告警服务"""

    def __init__(self, db, alert_callback=None):
        self.db = db
        self.alert_callback = alert_callback
        self.today_stats = defaultdict(lambda: {"success": 0, "failed": 0})
        self.alert_thresholds = {
            "success_rate": 0.95,
            "failure_count": 20,
            "api_latency_ms": 3000,
            "token_refresh_failures": 3,
        }
        self.token_refresh_failures = 0

    def record_success(self, action_type: str):
        self.today_stats[action_type]["success"] += 1

    def record_failure(self, action_type: str):
        self.today_stats[action_type]["failed"] += 1

    def record_token_failure(self):
        self.token_refresh_failures += 1

    def record_token_success(self):
        self.token_refresh_failures = 0

    async def check_health(self) -> dict:
        """执行健康检查"""
        checks = {
            "token_status": self._check_token(),
            "success_rate": self._check_success_rate(),
            "failure_count": self._check_failure_count(),
            "db_status": await self._check_db(),
        }

        overall_healthy = all(
            check["status"] == "ok" for check in checks.values()
        )

        return {
            "healthy": overall_healthy,
            "checks": checks,
            "timestamp": datetime.now().isoformat()
        }

    def _check_token(self) -> dict:
        if self.token_refresh_failures >= self.alert_thresholds["token_refresh_failures"]:
            return {
                "status": "error",
                "message": f"Token刷新失败次数: {self.token_refresh_failures}"
            }
        return {"status": "ok"}

    def _check_success_rate(self) -> dict:
        alerts = []
        for action_type, stats in self.today_stats.items():
            total = stats["success"] + stats["failed"]
            if total > 0:
                rate = stats["success"] / total
                if rate < self.alert_thresholds["success_rate"]:
                    alerts.append(f"{action_type}: {rate:.1%}")

        if alerts:
            return {"status": "warning", "message": "; ".join(alerts)}
        return {"status": "ok"}

    def _check_failure_count(self) -> dict:
        total_failures = sum(s["failed"] for s in self.today_stats.values())
        if total_failures > self.alert_thresholds["failure_count"]:
            return {
                "status": "error",
                "message": f"今日失败次数: {total_failures}"
            }
        return {"status": "ok"}

    async def _check_db(self) -> dict:
        try:
            self.db.execute("SELECT 1")
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def send_alert(self, message: str, severity: str = "medium"):
        """发送告警"""
        if self.alert_callback:
            await self.alert_callback(message, severity)
```

### 4.5 热更新配置

```python
# app/services/hot_reload.py
import asyncio
import yaml
from pathlib import Path

class HotConfigReloader:
    """配置热更新 - 无需重启服务"""

    def __init__(self, config_path: str, on_reload=None):
        self.config_path = Path(config_path)
        self.current_config = {}
        self.on_reload = on_reload
        self.mtime = 0

    async def watch_config_changes(self):
        """监控配置文件变化"""
        while True:
            try:
                current_mtime = self.config_path.stat().st_mtime

                if current_mtime != self.mtime:
                    if self.mtime != 0:
                        logger.info("检测到配置文件变化，重新加载")
                        await self.reload_config()
                    self.mtime = current_mtime

            except Exception as e:
                logger.error(f"监控配置文件异常: {e}")

            await asyncio.sleep(2)

    async def reload_config(self):
        """重新加载配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                new_config = yaml.safe_load(f)

            self.current_config.update(new_config)

            if self.on_reload:
                await self.on_reload(new_config)

            return True
        except Exception as e:
            logger.error(f"重载配置失败: {e}")
            return False

    def get(self, key, default=None):
        """获取配置项"""
        return self.current_config.get(key, default)
```

### 4.6 数据备份

```python
# app/services/backup.py
import asyncio
import shutil
import gzip
from datetime import datetime
from pathlib import Path

class BackupService:
    """数据备份服务"""

    def __init__(self, db_path: str, backup_dir: str = "./backups"):
        self.db_path = db_path
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.auto_backup_interval = 3600
        self.max_backups = 24

    async def backup_database(self):
        """自动备份数据库"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"backup_{timestamp}.db"

        try:
            shutil.copy2(self.db_path, backup_file)

            compressed_file = self.backup_dir / f"backup_{timestamp}.db.gz"
            with open(backup_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            backup_file.unlink()
            self._record_backup(compressed_file)
            await self.cleanup_old_backups()

            return str(compressed_file)
        except Exception as e:
            logger.error(f"备份失败: {e}")
            return None

    async def restore_from_backup(self, backup_file: str):
        """从备份恢复"""
        try:
            temp_file = self.backup_dir / "temp_restore.db"
            with gzip.open(backup_file, 'rb') as f_in:
                with open(temp_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            shutil.copy2(temp_file, self.db_path)
            temp_file.unlink()
            return True
        except Exception as e:
            logger.error(f"恢复失败: {e}")
            return False

    async def cleanup_old_backups(self):
        """清理旧备份"""
        backups = sorted(
            self.backup_dir.glob("backup_*.db.gz"),
            key=lambda p: p.stat().st_mtime
        )

        if len(backups) > self.max_backups:
            for old_backup in backups[:-self.max_backups]:
                old_backup.unlink()
                logger.info(f"删除旧备份: {old_backup.name}")

    def _record_backup(self, backup_file: Path):
        """记录备份信息"""
        record = BackupRecord(
            backup_file=str(backup_file),
            backup_type="auto",
            file_size=backup_file.stat().st_size
        )
        self.db.add(record)
        self.db.commit()
```

---

## 五、知识库设计 (SQLite + ChromaDB)

### 数据库表结构

```sql
-- 微信配置
CREATE TABLE wechat_configs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    corp_id TEXT UNIQUE NOT NULL,
    agent_id TEXT NOT NULL,
    secret TEXT NOT NULL,
    token TEXT NOT NULL,
    encoding_aes_key TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 客户表 (外部联系人)
CREATE TABLE customers (
    id TEXT PRIMARY KEY,
    external_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    name TEXT,
    avatar TEXT,
    tags TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 消息去重表
CREATE TABLE message_dedup (
    msg_id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_expires (created_at)
);

-- 知识库文档
CREATE TABLE kb_documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT,
    category TEXT,
    metadata JSON,
    embedding_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 定时任务
CREATE TABLE scheduled_tasks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    task_type TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    content TEXT,
    cron_expression TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 发送记录 (用于限制每天4次群发)
CREATE TABLE send_records (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    task_id TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    INDEX idx_customer_sent (customer_id, sent_at)
);

-- 操作日志
CREATE TABLE operation_logs (
    id TEXT PRIMARY KEY,
    operator_type TEXT,
    operator_id TEXT,
    action_type TEXT,
    target_type TEXT,
    target_id TEXT,
    content_preview TEXT,
    risk_level INTEGER,
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_action (action_type),
    INDEX idx_created (created_at)
);

-- 审计日志
CREATE TABLE audit_logs (
    id TEXT PRIMARY KEY,
    operator_type TEXT,
    operator_id TEXT,
    action_type TEXT,
    target_type TEXT,
    target_id TEXT,
    content_preview TEXT,
    ip_address TEXT,
    user_agent TEXT,
    risk_level INTEGER,
    status TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_operator (operator_id),
    INDEX idx_created_at (created_at)
);

-- 备份记录
CREATE TABLE backup_records (
    id TEXT PRIMARY KEY,
    backup_file TEXT,
    backup_type TEXT,
    file_size INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 发布缓存
CREATE TABLE publish_cache (
    id TEXT PRIMARY KEY,
    article_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    content TEXT,
    url TEXT,
    published_at TIMESTAMP,
    is_notified INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### ChromaDB RAG 实现

```python
# app/services/knowledge_base.py
import chromadb

class KnowledgeBaseService:
    def __init__(self, persist_directory: str = "./chroma_data"):
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            "kb_documents",
            metadata={"description": "企业微信机器人知识库"}
        )

    def add_document(self, doc_id: str, content: str, metadata: dict = None):
        self.collection.add(
            ids=[doc_id],
            documents=[content],
            metadatas=[metadata or {}]
        )

    def search(self, query: str, top_k: int = 5) -> list:
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        return results

    def get_context_string(self, query: str, top_k: int = 3) -> str:
        results = self.search(query, top_k=top_k)
        if not results.get("ids"):
            return ""
        parts = ["【知识库参考】"]
        for i, content in enumerate(results["documents"][0], 1):
            parts.append(f"\n{i}. {content}")
        return "\n".join(parts)

    def get_stats(self) -> dict:
        return {
            "total_documents": self.collection.count(),
            "name": self.collection.name
        }
```

---

## 六、消息流程

```
用户发送消息
        │
        ▼
企业微信平台 --- > [Webhook Callback POST /api/v1/wechat/callback]
        │                         │
        │ (加密XML)              │ 使用WXBizMsgCrypt解密
        │                         v
        │              解析XML (xmltodict)
        │                         │
        │                         v
        │              提取: MsgType, Content, FromUserName, AgentID
        │                         │
        v                         v
[返回"success"]      消息去重检查 (msg_id)
                            │
                            ▼
                    检查消息类型和事件
                            │
                            ├── [Text] ──> 处理文本消息
                            └── [Event] ──>
                                    ├── add_external_contact (新客户)
                                    └── change_external_contact (客户变化)
                                    │
                                    v
                            保存到SQLite + 审计日志
                                    │
                            ┌───────┴───────┐
                            ▼               ▼
                    RAG检索        业务逻辑处理
                            │               │
                            └───────┬───────┘
                                    ▼
                            构建Prompt (System + Context + RAG)
                                    │
                                    ▼
                            调用LLM API
                                    │
                                    ▼
                            加密响应XML
                                    │
                                    ▼
                            返回加密响应
```

---

## 七、核心API端点

### 企业微信平台API

Base URL: `https://qyapi.weixin.qq.com/cgi-bin/`

| 端点 | 方法 | 描述 |
|------|------|------|
| `/gettoken?corpid={corp_id}&corpsecret={corpsecret}` | GET | 获取access_token |
| `/message/send?access_token={token}` | POST | 发送消息 |
| `/message/send_all?access_token={token}` | POST | 群发消息 |
| `/externalcontact/add_contact_way` | POST | 创建联系我二维码 |
| `/externalcontact/list?userid={userid}` | GET | 获取客户列表 |
| `/externalcontact/get?external_userid={id}` | GET | 获取客户详情 |
| `{webhook_url}` | POST | 群机器人发送消息 |

### 应用API端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `GET /api/v1/wechat/verify` | GET | 验证回调URL |
| `POST /api/v1/wechat/callback` | POST | 接收微信回调 |
| `POST /api/v1/wechat/send/text` | POST | 发送文本消息 |
| `POST /api/v1/wechat/send/markdown` | POST | 发送markdown |
| `POST /api/v1/wechat/group/send` | POST | 发送群消息 |
| `POST /api/v1/customers` | POST | 创建客户记录 |
| `GET /api/v1/customers` | GET | 获取客户列表 |
| `POST /api/v1/kb/documents` | POST | 添加知识文档 |
| `GET /api/v1/kb/search` | GET | 搜索知识库 |
| `POST /api/v1/scheduler/tasks` | POST | 创建定时任务 |
| `GET /api/v1/publish/check` | POST | 检查新发布内容 |
| `GET /api/v1/system/health` | GET | 健康检查 |
| `GET /api/v1/system/audit` | GET | 审计日志查询 |

---

## 八、代码结构

```
enterprise-wechat-bot/
|-- app/
|   |-- main.py                    # FastAPI入口
|   |-- config.py                   # 配置
|   |-- api/v1/
|   │   |-- router.py              # 路由注册
|   │   |-- endpoints/
|   │   │   |-- wechat.py          # 微信回调+发送
|   │   │   |-- customers.py        # 客户管理
|   │   │   |-- kb.py              # 知识库
|   │   │   |-- scheduler.py       # 定时任务
|   │   │   |-- publish.py          # 发布系统
|   │   │   |-- system.py          # 系统管理(健康检查/审计)
|   |-- services/
|   │   |-- wechat.py              # 企业微信API
|   │   |-- token_manager.py        # Token自动刷新
|   │   |-- customer.py            # 客户联系管理
|   │   |-- ai.py                  # LLM服务
|   │   |-- knowledge_base.py       # ChromaDB RAG
|   │   |-- scheduler.py           # APScheduler
|   │   |-- publish.py             # 发布系统
|   │   |-- message_dedup.py       # 消息去重
|   │   |-- audit_logger.py        # 操作审计
|   │   |-- health_check.py        # 健康检查
|   │   |-- hot_reload.py          # 热更新配置
|   │   |-- backup.py              # 数据备份
|   |-- utils/
|   │   |-- wechat_crypto.py       # 消息加解密
|   |-- models/                    # SQLAlchemy模型
|   |-- db/                        # 数据库会话
|-- requirements.txt
|-- run.py
```

---

## 九、定时发送 (APScheduler)

```python
# app/services/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = BackgroundScheduler()

class SchedulerService:
    def add_broadcast_task(self, task_id: str, target_type: str,
                          target_id: str, content: str, cron_expression: str):
        parts = cron_expression.split()
        trigger = CronTrigger(
            minute=parts[0], hour=parts[1],
            day=parts[2], month=parts[3], day_of_week=parts[4]
        )
        self.scheduler.add_job(
            func=lambda: self._execute_broadcast(target_type, target_id, content),
            trigger=trigger,
            id=task_id,
            replace_existing=True
        )

    def _execute_broadcast(self, target_type: str, target_id: str, content: str):
        if target_type == "customer":
            if self.check_daily_limit(target_id):
                self.wechat_service.send_text(target_id, content)
        elif target_type == "group":
            self.wechat_service.send_group_message(target_id, content)
```

**Cron表达式示例**:
| 表达式 | 含义 |
|--------|------|
| `0 9 * * *` | 每天9:00 |
| `0 9 * * 1-5` | 工作日9:00 |
| `0 */2 * * *` | 每2小时 |

---

## 十、实现计划

| 阶段 | 内容 | 优先级 |
|------|------|--------|
| Phase 1 | 项目结构、SQLite、ChromaDB集成 | 高 |
| Phase 2 | Token自动刷新 + 消息去重 | 高 |
| Phase 3 | 客户联系API (加好友、欢迎语) | 高 |
| Phase 4 | 消息发送API + 防风控 | 高 |
| Phase 5 | 群里自动回复 (应用回调) | 高 |
| Phase 6 | AI服务集成、RAG检索 | 高 |
| Phase 7 | 知识库管理API | 中 |
| Phase 8 | APScheduler定时任务 | 中 |
| Phase 9 | 发布系统轮询对接 | 中 |
| Phase 10 | 操作审计日志 + 健康检查 | 中 |
| Phase 11 | 热更新配置 + 数据备份 | 中 |
| Phase 12 | 测试与部署 | 中 |

---

## 十一、关键依赖

```
fastapi>=0.100.0
uvicorn>=0.23.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
requests>=2.31.0
apscheduler>=3.10.0
chromadb>=0.4.0
openai>=1.0.0
pycryptodome>=3.18.0
xmltodict>=0.13.0
pyyaml>=6.0
aiohttp>=3.9.0
psutil>=5.9.0
```

---

## 十二、结论

**企业微信官方API是唯一零风险方案**：
- 永不封号
- 官方支持
- 支持自动加好友 (客户联系)
- 支持给好友发消息 (消息/群发API)
- 支持群里自动回复 (应用消息回调)
- 可对接LLM + ChromaDB知识库
- 支持定时发送和触发式回复

**前提**: 需要企业主体（个人可注册个体工商户）

**最重要的限制**:
1. 群发每天最多4次/客户
2. 发消息20次/分钟/企业上限
3. 内容要多样化，避免触发风控

**新增基础设施**:
- Token自动刷新机制
- 消息去重
- 操作审计日志
- 健康检查与告警
- 热更新配置
- 数据备份