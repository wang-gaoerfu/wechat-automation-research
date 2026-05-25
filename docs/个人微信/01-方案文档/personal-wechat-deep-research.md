# 个人微信PC自动化 - 完整设计方案

**调研日期**: 2026-05-24
**版本**: v2.0 (完整版)
**技术栈**: Python + FastAPI + SQLite + ChromaDB + WeChatFerry

---

## 一、系统架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      个人微信自动化综合运营平台                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐         ┌──────────────────────┐                     │
│  │              │         │                      │                     │
│  │  微信PC客户端 │◄───────►│  WeChatFerry DLL     │                     │
│  │  (WeChat.exe)│         │  (注入的Hook模块)     │                     │
│  │              │         │                      │                     │
│  └──────────────┘         └──────────┬───────────┘                     │
│                                       │ RPC通信                         │
│                                       ▼                                 │
│  ┌───────────────────────────────────────────────────────────────┐     │
│  │                    WCF Client (Python)                         │     │
│  │  - send_text(wxid, content)     发送消息                       │     │
│  │  - send_image(wxid, path)       发送图片                       │     │
│  │  - get_contacts()               获取联系人                      │     │
│  │  - get_group_members(roomid)    获取群成员                      │     │
│  │  - subscribe(callback)          订阅消息                        │     │
│  │  - add_friend(wxid, verify)     添加好友                       │     │
│  │  - get_self_info()              获取自身信息                    │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                                │                                       │
│                                ▼                                       │
│  ┌───────────────────────────────────────────────────────────────┐     │
│  │                    FastAPI Server                               │     │
│  │         │               │               │                      │     │
│  │         ▼               ▼               ▼                      │     │
│  │  ┌──────────┐   ┌────────────┐   ┌──────────────┐            │     │
│  │  │ 消息队列  │   │ LLM服务     │   │  知识库RAG    │            │     │
│  │  │ (Queue)  │   │(DeepSeek)  │   │(ChromaDB)    │            │     │
│  │  └──────────┘   └────────────┘   └──────────────┘            │     │
│  │         │               │               │                      │     │
│  │         └───────────────┴───────────────┘                     │     │
│  │                         │                                      │     │
│  │                         ▼                                      │     │
│  │  ┌──────────────────────────────────────────────────┐         │     │
│  │  │              AntiBanEngine (防风控引擎)           │         │     │
│  │  │  - RateLimiter    频率限制                        │         │     │
│  │  │  - ContentGen     内容多样化                      │         │     │
│  │  │  - BehaviorSim   行为模拟                        │         │     │
│  │  │  - AccountMgr    账号管理                        │         │     │
│  │  │  - MonitorSvc    监控告警                        │         │     │
│  │  └──────────────────────────────────────────────────┘         │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐     │
│  │                    基础设施层                                    │     │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │     │
│  │  │ 连接保活      │  │ 版本管理器    │  │ 进程监控     │        │     │
│  │  │ (WCFConnMgr) │  │(VersionMgr)  │  │(ProcMonitor) │        │     │
│  │  └──────────────┘  └──────────────┘  └──────────────┘        │     │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │     │
│  │  │ 数据备份     │  │ 热更新配置    │  │ 操作审计    │        │     │
│  │  │(BackupSvc)  │  │ (HotReload)  │  │ (AuditLog)  │        │     │
│  │  └──────────────┘  └──────────────┘  └──────────────┘        │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 二、核心API接口 (WeChatFerry)

### 2.1 核心RPC接口

| 功能 | 方法 | 说明 |
|------|------|------|
| 发送文本 | `send_text(wxid, content)` | 发送给指定用户/群 |
| 发送图片 | `send_image(wxid, image_path)` | 发送图片 |
| 发送文件 | `send_file(wxid, file_path)` | 发送文件 |
| 获取联系人 | `get_contacts()` | 返回所有联系人 |
| 获取群成员 | `get_group_members(roomid)` | 获取群成员列表 |
| 获取自身信息 | `get_self_info()` | 获取自己的wxid等信息 |
| 监听消息 | `subscribe(callback)` | 实时接收消息回调 |
| 添加好友 | `add_friend(wxid, verify_content)` | 添加好友 |
| 同意好友 | `accept_friend_request(v3, v4)` | 同意好友请求 |
| 获取好友请求 | `get_friend_requests()` | 获取好友请求列表 |

### 2.2 Hook技术原理

**注入方式**:
1. **PEB遍历法**: 遍历进程PEB获取WeChatWin.dll模块基址
2. **CreateRemoteThread**: 在微信进程中创建远程线程
3. **LoadLibrary**: 加载自定义DLL到微信进程空间

**关键Hook点**:
```
WeChatWin.dll!RecvMsg  -> 接收消息回调
WeChatWin.dll!SendMsg  -> 发送消息拦截
WeChatWin.dll!AddContact -> 加好友拦截
WeChatWin.dll!GetContactInfo -> 联系人信息获取
```

---

## 三、数据库设计

### 3.1 完整表结构

```sql
-- 账号表
CREATE TABLE accounts (
    id TEXT PRIMARY KEY,
    wxid TEXT UNIQUE NOT NULL,
    nickname TEXT,
    phone TEXT,
    avatar TEXT,
    status TEXT DEFAULT 'normal',        -- normal, restricted, banned
    risk_level REAL DEFAULT 0.0,         -- 0.0-1.0, 越高风险越大
    account_age_days INTEGER,
    last_active_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 联系人表
CREATE TABLE contacts (
    id TEXT PRIMARY KEY,
    wxid TEXT UNIQUE NOT NULL,
    nickname TEXT,
    alias TEXT,
    avatar TEXT,
    type TEXT,                            -- friend, group, official
    tags TEXT,                            -- JSON数组: ["潜在客户", "VIP"]
    remark TEXT,                          -- 备注
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 群表
CREATE TABLE groups (
    id TEXT PRIMARY KEY,
    roomid TEXT UNIQUE NOT NULL,
    name TEXT,
    owner_wxid TEXT,
    member_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 群成员表
CREATE TABLE group_members (
    id TEXT PRIMARY KEY,
    roomid TEXT NOT NULL,
    wxid TEXT NOT NULL,
    nickname TEXT,
    join_time TIMESTAMP,
    FOREIGN KEY (roomid) REFERENCES groups(roomid),
    UNIQUE(roomid, wxid)
);

-- 消息表
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    msg_id TEXT UNIQUE,
    wxid_from TEXT NOT NULL,
    wxid_to TEXT NOT NULL,
    content TEXT,
    msg_type TEXT,                        -- text, image, file, video, etc
    is_sent INTEGER DEFAULT 0,            -- 0=收到, 1=发送
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_wxid_from (wxid_from),
    INDEX idx_wxid_to (wxid_to),
    INDEX idx_created_at (created_at)
);

-- 发送记录 (用于频率限制)
CREATE TABLE send_records (
    id TEXT PRIMARY KEY,
    wxid_from TEXT NOT NULL,
    wxid_to TEXT NOT NULL,
    action_type TEXT,                     -- message, friend_request, add_friend
    status TEXT,                          -- success, failed
    error_msg TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_wxid_action (wxid_from, action_type),
    INDEX idx_created_at (created_at)
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
    task_type TEXT,                       -- broadcast, reminder, auto_reply
    target_type TEXT,                     -- contact, group, all
    target_id TEXT,
    content TEXT,
    cron_expression TEXT,
    is_active INTEGER DEFAULT 1,
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 操作日志
CREATE TABLE operation_logs (
    id TEXT PRIMARY KEY,
    operator_type TEXT,                   -- system, ai, manual
    operator_id TEXT,
    action_type TEXT,
    target_type TEXT,
    target_id TEXT,
    content_preview TEXT,                  -- 内容预览（脱敏）
    risk_level INTEGER,
    status TEXT,
    error_message TEXT,
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_action_type (action_type),
    INDEX idx_created_at (created_at)
);

-- 审计日志
CREATE TABLE audit_logs (
    id TEXT PRIMARY KEY,
    operator_type TEXT,                   -- system, ai, manual
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

-- 备份记录
CREATE TABLE backup_records (
    id TEXT PRIMARY KEY,
    backup_file TEXT,
    backup_type TEXT,                     -- auto, manual
    file_size INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 四、防风控系统

### 4.1 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    AntiBanEngine (防风控引擎)                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ RateLimiter  │  │ ContentGen   │  │ BehaviorSim  │       │
│  │ 频率限制器    │  │ 内容生成器    │  │ 行为模拟器   │       │
│  │              │  │              │  │              │       │
│  │ • 每日限制   │  │ • 多样化模板 │  │ • 时间分散   │       │
│  │ • 间隔控制   │  │ • emoji混入 │  │ • 操作轨迹   │       │
│  │ • 智能排队   │  │ • 同义替换   │  │ • 模拟人类   │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ AccountMgr  │  │ VersionMgr   │  │ MonitorSvc   │       │
│  │ 账号管理器   │  │ 版本管理器    │  │ 监控服务     │       │
│  │              │  │              │  │              │       │
│  │ • 账号状态   │  │ • 版本检测   │  │ • 成功率统计 │       │
│  │ • 风控等级   │  │ • 自动适配   │  │ • 异常告警   │       │
│  │ • 养号进度   │  │ • DLL更新   │  │ • 阈值告警   │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 频率限制器

```python
# app/services/anti_ban/rate_limiter.py
import time
from collections import defaultdict
from datetime import datetime, timedelta

class RateLimiter:
    """频率限制器 - 防止触发风控"""

    def __init__(self):
        # 每天每个动作的最大次数
        self.daily_limits = {
            "message": 500,              # 每天最多发500条消息
            "add_friend": 10,            # 每天最多加10个好友
            "send_friend_request": 20,
            "group_broadcast": 50,       # 群发消息
            "like_moment": 30,           # 朋友圈点赞
        }

        # 每次操作的最小间隔(秒)
        self.min_intervals = {
            "message": 3,
            "add_friend": 60,
            "send_friend_request": 30,
            "group_broadcast": 5,
        }

        # 调用计数
        self.call_counts = defaultdict(list)

    def check_rate_limit(self, wxid, action_type) -> bool:
        """检查是否超过频率限制"""
        today_count = self._get_today_count(wxid, action_type)
        limit = self.daily_limits.get(action_type, 100)
        return today_count < limit

    def _get_today_count(self, wxid, action_type) -> int:
        """获取今天的调用次数"""
        today_start = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        key = f"{wxid}:{action_type}"

        # 清理过期记录
        self.call_counts[key] = [
            t for t in self.call_counts[key]
            if t >= today_start.timestamp()
        ]

        return len(self.call_counts[key])

    def get_wait_time(self, wxid, action_type) -> float:
        """获取需要等待的时间"""
        base_delay = self.min_intervals.get(action_type, 5)
        # 添加随机波动: ±50%
        return base_delay * random.uniform(0.5, 1.5)

    def record_call(self, wxid, action_type):
        """记录一次调用"""
        key = f"{wxid}:{action_type}"
        self.call_counts[key].append(time.time())

    def is_in_restricted_hours(self) -> bool:
        """检查是否在限制时段"""
        hour = datetime.now().hour
        # 凌晨2-6点不操作
        return 2 <= hour < 6
```

### 4.3 内容多样化生成器

```python
# app/services/anti_ban/content_gen.py
import random

class ContentDiversifier:
    """内容多样化生成器 - 避免发送重复内容"""

    def __init__(self):
        self.templates = [
            "您好 {content}",
            "你好 {content}",
            "Hi {content}",
            "Hello {content}",
            "{content}",
        ]

        self.greetings = ["你好", "您好", "Hi", "Hello", "嗨", ""]
        self.suffixes = ["😊", "🤝", "请查收", "～", "✓", ""]
        self.emojis = ["😊", "👍", "🤔", "🙂", "👋", "✨", "📌", "💡"]

        # 同义词替换表
        self.synonyms = {
            "感谢": ["谢谢", "多谢", "thx", "蟹蟹"],
            "请问": ["我想问", "想请教", "咨询一下"],
            "帮助": ["帮忙", "协助", "支持下"],
        }

    def diversify(self, content: str) -> str:
        """生成多样化的内容"""
        # 1. 随机选择模板
        template = random.choice(self.templates)
        result = template.format(content=content)

        # 2. 添加随机前缀
        greeting = random.choice(self.greetings)
        if greeting:
            result = f"{greeting}，{result}"

        # 3. 添加随机后缀
        suffix = random.choice(self.suffixes)
        if suffix:
            result = f"{result} {suffix}"

        # 4. 随机决定是否加emoji
        if random.random() < 0.3:
            emojis = random.sample(self.emojis, k=random.randint(1, 2))
            result = f"{result} {' '.join(emojis)}"

        return result

    def replace_synonyms(self, content: str) -> str:
        """同义词替换"""
        for word, alternatives in self.synonyms.items():
            if word in content and random.random() < 0.3:
                content = content.replace(word, random.choice(alternatives))
        return content

    def generate_follow_up(self, original: str) -> str:
        """生成跟进内容"""
        followups = [
            f"补充一下：{original}",
            f"另外，{original}",
            f"顺便说一下：{original}",
            original,  # 有时保持原样
        ]
        return random.choice(followups)
```

### 4.4 行为模拟器

```python
# app/services/anti_ban/behavior.py
import random
import asyncio
from datetime import datetime

class BehaviorSimulator:
    """行为模拟器 - 模拟人类操作模式"""

    def __init__(self):
        self.action_delays = {
            "send_message": (3, 8),        # 3-8秒
            "add_friend": (60, 180),       # 1-3分钟
            "view_profile": (5, 15),       # 5-15秒
            "like_moment": (5, 15),
            "send_friend_request": (30, 120),
        }

    def calculate_delay(self, action_type: str) -> float:
        """根据操作类型计算随机延迟"""
        min_d, max_d = self.action_delays.get(action_type, (3, 8))
        return random.uniform(min_d, max_d)

    def should_operate(self, account) -> tuple:
        """判断当前是否应该操作"""
        # 不在凌晨2-6点操作
        hour = datetime.now().hour
        if 2 <= hour < 6:
            return False, "凌晨时段不操作"

        # 高风险账号增加延迟
        if account.risk_level > 0.5:
            delay = self.calculate_delay("send_message") * 2
            return True, f"高风险账号，延迟{delay:.0f}秒"

        return True, "正常操作"

    async def simulate_human_delay(self, base_delay: float):
        """模拟人类操作延迟"""
        # 在基础延迟上添加随机波动
        delay = base_delay * random.uniform(0.8, 1.5)
        await asyncio.sleep(delay)

    def generate_click_position(self):
        """生成随机点击位置（模拟鼠标移动）"""
        # 返回相对于元素中心的随机偏移
        return (
            random.randint(-10, 10),
            random.randint(-10, 10)
        )
```

### 4.5 账号管理器

```python
# app/services/anti_ban/account_mgr.py

class AccountManager:
    """账号管理器 - 管理账号状态和风控等级"""

    def __init__(self, db):
        self.db = db

    def get_account(self, wxid: str):
        """获取账号信息"""
        account = self.db.query(Account).filter(
            Account.wxid == wxid
        ).first()

        if not account:
            account = Account(
                wxid=wxid,
                risk_level=0.1,  # 新账号默认低风险
                status='normal'
            )
            self.db.add(account)
            self.db.commit()

        return account

    def update_risk_level(self, wxid: str, operation_success: bool):
        """根据操作结果更新风控等级"""
        account = self.get_account(wxid)

        if operation_success:
            # 成功操作降低风险
            account.risk_level = max(0, account.risk_level - 0.01)
        else:
            # 失败操作增加风险
            account.risk_level = min(1.0, account.risk_level + 0.1)

        # 如果风险等级过高，设置限制
        if account.risk_level > 0.8:
            account.status = 'restricted'

        self.db.commit()

    def get_operating_interval(self, wxid: str) -> float:
        """根据账号状态获取操作间隔"""
        account = self.get_account(wxid)

        if account.risk_level > 0.7:
            return 60  # 高风险账号：1分钟间隔
        elif account.risk_level > 0.4:
            return 30  # 中风险账号：30秒间隔
        else:
            return 10  # 低风险账号：10秒间隔
```

### 4.6 监控服务

```python
# app/services/anti_ban/monitor.py
from collections import defaultdict
from datetime import datetime

class MonitorService:
    """监控服务 - 监控操作成功率，异常告警"""

    def __init__(self, db):
        self.db = db
        self.today_stats = defaultdict(lambda: {"success": 0, "failed": 0})
        self.alert_thresholds = {
            "success_rate": 0.95,         # 成功率低于95%告警
            "failure_count": 10,          # 失败次数超10次告警
            "latency_ms": 3000,           # 延迟超3秒告警
        }

    def record_success(self, action_type: str):
        self.today_stats[action_type]["success"] += 1

    def record_failure(self, action_type: str):
        self.today_stats[action_type]["failed"] += 1

    def get_success_rate(self, action_type: str) -> float:
        """获取成功率"""
        stats = self.today_stats[action_type]
        total = stats["success"] + stats["failed"]
        if total == 0:
            return 1.0
        return stats["success"] / total

    def should_alert(self, action_type: str = None) -> list:
        """检查是否需要告警"""
        alerts = []

        check_types = [action_type] if action_type else list(self.today_stats.keys())

        for at in check_types:
            rate = self.get_success_rate(at)
            if rate < self.alert_thresholds["success_rate"]:
                alerts.append({
                    "type": at,
                    "issue": "success_rate",
                    "message": f"{at}成功率低于95%: {rate:.1%}",
                    "severity": "high" if rate < 0.9 else "medium"
                })

            stats = self.today_stats[at]
            if stats["failed"] > self.alert_thresholds["failure_count"]:
                alerts.append({
                    "type": at,
                    "issue": "failure_count",
                    "message": f"{at}失败次数: {stats['failed']}",
                    "severity": "high"
                })

        return alerts

    async def send_alert(self, alert: dict):
        """发送告警"""
        # 企业微信机器人通知
        webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
        message = f"【个人微信自动化告警】\n{alert['message']}"

        # TODO: 实际发送告警
        print(f"ALERT: {message}")
```

---

## 五、基础设施服务

### 5.1 连接保活管理器

```python
# app/services/wcf_client.py
import asyncio
import logging

logger = logging.getLogger(__name__)

class WCFConnectionManager:
    """WeChatFerry连接管理器 - 保活机制"""

    def __init__(self):
        self.client = None
        self.reconnect_interval = 30  # 秒
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5

    async def connect(self):
        """建立连接"""
        try:
            from wcf import WCFClient
            self.client = WCFClient()
            self.client.start()
            self.is_connected = True
            self.reconnect_attempts = 0
            logger.info("WCF连接成功")
        except Exception as e:
            logger.error(f"WCF连接失败: {e}")
            self.is_connected = False
            raise

    async def ensure_connected(self):
        """确保连接正常，不正常则重连"""
        while True:
            if not self.is_connected():
                await self.reconnect()
            await asyncio.sleep(self.reconnect_interval)

    async def reconnect(self):
        """重连逻辑"""
        self.reconnect_attempts += 1

        if self.reconnect_attempts > self.max_reconnect_attempts:
            logger.error("WCF重连次数超限，发送告警")
            # await self.send_alert("WCF连接失败次数超限")
            return

        for attempt in range(self.max_reconnect_attempts):
            try:
                logger.info(f"WCF重连尝试 {attempt + 1}")
                await self.connect()
                logger.info("WCF重连成功")
                return
            except Exception as e:
                wait_time = 2 ** attempt  # 指数退避
                logger.warning(f"WCF重连失败，等待{wait_time}秒: {e}")
                await asyncio.sleep(wait_time)

    def is_connected(self) -> bool:
        """检查连接状态"""
        if not self.client:
            return False
        try:
            # 尝试获取自身信息检测连接
            self.client.get_self_info()
            return True
        except:
            return False
```

### 5.2 版本管理器

```python
# app/services/version_manager.py

class VersionManager:
    """微信版本管理器 - 自动适配不同微信版本"""

    def __init__(self):
        self.current_version = None
        self.supported_versions = {
            "3.9.10.19": {
                "offsets": {
                    "recv_msg": 0x12345678,
                    "send_msg": 0x23456789,
                }
            },
            "3.9.8.15": {
                "offsets": {
                    "recv_msg": 0x11111111,
                    "send_msg": 0x22222222,
                }
            },
            "3.9.6.29": {
                "offsets": {
                    "recv_msg": 0xAAAABBBB,
                    "send_msg": 0xCCCCDDDD,
                }
            }
        }
        self.version_db_url = "https://wechatferry.com/versions.json"

    def detect_version(self) -> str:
        """检测当前微信版本"""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\WOW6432Node\Tencent\WeChat"
            )
            version, _ = winreg.QueryValueEx(key, "Version")
            self.current_version = version
            return version
        except:
            return "unknown"

    def is_version_supported(self) -> bool:
        """检查版本是否支持"""
        return self.current_version in self.supported_versions

    def get_offsets(self) -> dict:
        """获取当前版本的函数偏移量"""
        if not self.current_version:
            self.detect_version()

        if self.current_version not in self.supported_versions:
            # 尝试使用最新版本的偏移量
            latest = max(self.supported_versions.keys())
            logger.warning(
                f"版本 {self.current_version} 未测试，使用 {latest} 的偏移量"
            )
            return self.supported_versions[latest]["offsets"]

        return self.supported_versions[self.current_version]["offsets"]

    async def check_and_update(self):
        """检查版本并自动适配"""
        current = self.detect_version()

        if current != self.current_version:
            logger.info(f"微信版本变更: {self.current_version} -> {current}")

            if current not in self.supported_versions:
                logger.warning(f"新版本 {current} 可能不兼容")

            self.current_version = current
```

### 5.3 进程监控服务

```python
# app/services/process_monitor.py
import asyncio
import psutil
import logging

logger = logging.getLogger(__name__)

class WeChatProcessMonitor:
    """微信进程监控 - 监控微信进程状态"""

    def __init__(self, wcf_manager):
        self.wcf_manager = wcf_manager
        self.check_interval = 30
        self.process_name = "WeChat.exe"

    async def start_monitoring(self):
        """开始监控"""
        while True:
            try:
                if not self.is_wechat_running():
                    logger.warning("微信进程已退出")
                    await self.handle_wechat_exit()
            except Exception as e:
                logger.error(f"进程监控异常: {e}")

            await asyncio.sleep(self.check_interval)

    def is_wechat_running(self) -> bool:
        """检查微信进程是否运行"""
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == self.process_name:
                return True
        return False

    async def handle_wechat_exit(self):
        """处理微信退出"""
        # 1. 停止所有自动化任务
        logger.info("停止所有自动化任务")

        # 2. 标记连接断开
        self.wcf_manager.is_connected = False

        # 3. 等待微信重新启动
        logger.info("等待微信重新启动...")
        while not self.is_wechat_running():
            await asyncio.sleep(5)

        logger.info("检测到微信重新启动")

        # 4. 重新注入DLL并连接
        await self.wcf_manager.reconnect()

        # 5. 恢复连接后继续监控
        logger.info("恢复自动化任务")
```

### 5.4 数据备份服务

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
        self.auto_backup_interval = 3600  # 1小时
        self.max_backups = 24  # 保留最近24份

    async def backup_database(self):
        """自动备份数据库"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"backup_{timestamp}.db"

        try:
            # 复制数据库文件
            shutil.copy2(self.db_path, backup_file)

            # 压缩
            compressed_file = self.backup_dir / f"backup_{timestamp}.db.gz"
            with open(backup_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # 删除未压缩版本
            backup_file.unlink()

            # 记录备份
            self._record_backup(compressed_file)

            # 清理旧备份
            await self.cleanup_old_backups()

            return str(compressed_file)
        except Exception as e:
            logger.error(f"备份失败: {e}")
            return None

    async def restore_from_backup(self, backup_file: str):
        """从备份恢复"""
        try:
            # 解压
            temp_file = self.backup_dir / "temp_restore.db"
            with gzip.open(backup_file, 'rb') as f_in:
                with open(temp_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # 恢复
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

### 5.5 热更新配置

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
        self.on_reload = on_reload  # 回调函数
        self.mtime = 0

    async def watch_config_changes(self):
        """监控配置文件变化"""
        while True:
            try:
                current_mtime = self.config_path.stat().st_mtime

                if current_mtime != self.mtime:
                    if self.mtime != 0:  # 排除首次加载
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

### 5.6 消息去重

```python
# app/services/message_dedup.py
import time
from collections import defaultdict

class MessageDeduplicator:
    """消息去重 - 防止重复处理同一消息"""

    def __init__(self, cache_ttl: int = 3600):
        self.seen = defaultdict(dict)  # {msg_id: timestamp}
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

---

## 六、知识库RAG设计

### 6.1 ChromaDB集成

```python
# app/services/knowledge_base.py
import chromadb
from typing import List

class KnowledgeBaseService:
    """知识库RAG服务"""

    def __init__(self, persist_directory: str = "./chroma_data"):
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            "wechat_kb",
            metadata={"description": "微信机器人知识库"}
        )

    def add_document(self, doc_id: str, title: str, content: str,
                    category: str = None, metadata: dict = None):
        """添加知识文档"""
        meta = metadata or {}
        meta.update({
            "title": title,
            "category": category,
            "content_preview": content[:200]
        })

        self.collection.add(
            ids=[doc_id],
            documents=[content],
            metadatas=[meta]
        )

    def search(self, query: str, top_k: int = 5,
               category: str = None) -> List[dict]:
        """语义搜索"""
        where_filter = {"category": category} if category else None

        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        formatted = []
        if results["ids"]:
            for i in range(len(results["ids"][0])):
                formatted.append({
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "relevance_score": 1 - results["distances"][0][i]
                })

        return formatted

    def get_context_for_llm(self, query: str, top_k: int = 3) -> str:
        """构建LLM上下文"""
        results = self.search(query, top_k=top_k)

        if not results:
            return ""

        parts = ["【知识库参考】"]
        for i, doc in enumerate(results, 1):
            parts.append(f"\n{i}. {doc['content']}")

        return "\n".join(parts)

    def delete_document(self, doc_id: str):
        """删除文档"""
        self.collection.delete(ids=[doc_id])

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_documents": self.collection.count(),
            "name": self.collection.name
        }
```

---

## 七、消息流程

```
用户发消息到微信
        │
        ▼
[WeChatFerry DLL Hook拦截]
        │
        ▼
[WCF Client接收消息] ──► [消息去重检查]
        │                    │
        │              [重复则跳过]
        │                    │
        ▼                    ▼
[防风控检查]         [消息队列]
        │                    │
        ├── 频率检查          │
        ├── 账号状态检查       │
        ├── 时间段检查         │
        └── 风控等级检查       │
              │              │
              ▼              ▼
        [行为模拟延迟]   [知识库RAG检索]
              │              │
              │              ▼
              │      [LLM生成回复]
              │              │
              │              ▼
              │      [内容多样化处理]
              │              │
              ▼              ▼
[微信显示消息] ◄─── [安全发送]
```

---

## 八、核心代码结构

```
personal-wechat-bot/
|-- app/
|   |-- main.py                      # FastAPI入口
|   |-- config.py                     # 配置
|   |-- api/
|   |   |-- v1/
|   |   │   |-- router.py            # 路由注册
|   |   │   |-- endpoints/
|   |   │   │   |-- wechat.py        # 消息回调
|   |   │   │   |-- contacts.py      # 联系人管理
|   |   │   │   |-- groups.py        # 群管理
|   |   │   │   |-- kb.py            # 知识库
|   |   │   │   |-- scheduler.py     # 定时任务
|   │   │   │   |-- publish.py      # 发布系统
|   |   │   │   |-- system.py       # 系统管理
|   |-- services/
|   |   |-- wcf_client.py            # WeChatFerry客户端
|   |   |-- wcf_connection.py         # 连接管理
|   |   |-- anti_ban/
|   |   │   |-- __init__.py
|   |   │   |-- engine.py            # 防风控引擎
|   |   │   |-- rate_limiter.py      # 频率限制
|   |   │   |-- content_gen.py       # 内容生成
|   |   │   |-- behavior.py          # 行为模拟
|   |   │   |-- account_mgr.py       # 账号管理
|   |   │   |-- monitor.py           # 监控服务
|   |   |-- ai.py                    # LLM服务
|   |   |-- knowledge_base.py         # ChromaDB RAG
|   |   |-- scheduler.py             # APScheduler
|   |   |-- version_manager.py       # 版本管理
|   |   |-- process_monitor.py        # 进程监控
|   |   |-- backup.py                # 数据备份
|   |   |-- hot_reload.py            # 热更新
|   |   |-- message_dedup.py         # 消息去重
|   |-- models/
|   |   |-- account.py
|   |   |-- contact.py
|   |   |-- group.py
|   |   |-- message.py
|   |   |-- kb.py
|   |   |-- task.py
|   |-- db/
|   |   |-- base.py
|   |   |-- session.py
|-- wcf_inject/                       # DLL注入相关
|   |-- injector.py
|   |-- README.md
|-- requirements.txt
|-- run.py
```

---

## 九、实现计划

| 阶段 | 内容 | 优先级 |
|------|------|--------|
| Phase 1 | 项目结构、数据库、WeChatFerry集成 | 高 |
| Phase 2 | 连接保活、重连机制 | 高 |
| Phase 3 | 防风控引擎 (频率限制+内容多样化) | 高 |
| Phase 4 | 消息收发 + 自动回复 | 高 |
| Phase 5 | 知识库RAG + LLM集成 | 高 |
| Phase 6 | 联系人/群管理 | 中 |
| Phase 7 | 定时任务 + 发布系统对接 | 中 |
| Phase 8 | 版本自动适配 | 中 |
| Phase 9 | 进程监控 + 异常处理 | 中 |
| Phase 10 | 数据备份 + 热更新 | 中 |
| Phase 11 | 监控告警 + 操作审计 | 中 |
| Phase 12 | 测试 + 养号策略调优 | 中 |

---

## 十、关键依赖

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
psutil>=5.9.0
pyyaml>=6.0
```

---

## 十一、安全注意事项

### 11.1 严禁行为

| 行为 | 风险等级 |
|------|---------|
| 批量添加陌生好友 | ⬤⬤⬤⬤⬤ 极高 |
| 同一内容发给100人 | ⬤⬤⬤⬤ 高 |
| 使用修改版微信 | ⬤⬤⬤⬤ 高 |
| 登录超过5个设备 | ⬤⬤⬤ 高 |
| 凌晨2-6点大量操作 | ⬤⬤⬤⬤ 高 |
| 被多人举报 | ⬤⬤⬤⬤⬤ 极高 |

### 11.2 安全操作原则

1. **慢**: 操作间隔要长，随机化
2. **像人**: 内容多样化，不要太机械
3. **养号**: 新账号不要马上自动化
4. **被动**: 优先被动回复，少主动推送
5. **分散**: 时间分散、操作分散

---

## 十二、总结

**个人微信自动化方案**:
- 技术栈: Python + FastAPI + SQLite + ChromaDB + WeChatFerry
- 核心优势: 功能灵活，不依赖企业资质
- 核心风险: Hook方式存在封号风险

**关键防护措施**:
1. 完整的防风控引擎
2. 连接保活 + 自动重连
3. 版本自动适配
4. 进程异常监控
5. 数据备份
6. 热更新配置
7. 操作审计日志

**适用场景**:
- 无企业条件的个人用户
- 需要高度定制化的自动化场景
- 愿意承担一定封号风险的用户

**强烈建议**: 优先考虑企业微信方案，个人微信仅作为备选或技术探索。