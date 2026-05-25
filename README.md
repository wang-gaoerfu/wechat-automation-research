# 微信自动化运营方案

**方案设计者：墨飞科技**

本项目提供两套微信自动化运营解决方案，帮助企业高效管理微信客户，提升运营效率。

---

## 方案概览

| 方案 | 推荐程度 | 风险等级 | 适用场景 |
|------|---------|---------|---------|
| **企业微信（推荐）** | ⭐⭐⭐⭐⭐ | 极低 | 已开通企业微信的企业 |
| **个人微信（备选）** | ⭐⭐ | 中等 | 无企业微信的个人客户 |

### 企业微信方案（推荐）

基于腾讯官方 API 开发，永不封号，稳定合规。

**核心功能：**
- 消息自动回复（关键词触发）
- 定时群发（支持定时向客户推送内容）
- 客户标签管理（自动打标签）
- 自动加好友（生成获客二维码）
- 自动欢迎语（新客添加自动回复）
- 智能助手（Agent + MCP，自然语言控制）
- 知识库 RAG（ChromaDB 语义搜索）

**技术栈：**
- FastAPI + SQLAlchemy
- 企业微信官方 API
- Token 自动刷新管理
- 消息回调 AES 加密

### 个人微信方案（备选）

基于 WeChatFerry DLL Hook 实现，存在封号风险，仅作为备选方案。

**核心功能：**
- 消息自动回复
- 定时群发
- 客户管理（标签、好友、存档）
- 防风控系统（频率限制、内容多样化、行为模拟）

**技术栈：**
- FastAPI + SQLAlchemy
- WeChatFerry RPC 通信
- 消息订阅与处理
- 智能助手（Agent + MCP 架构）

---

## 项目结构

```
wechat-automation-research/
├── enterprise-wechat/          # 企业微信方案（推荐）
│   ├── app/
│   │   ├── api/v1/endpoints/   # API 端点
│   │   ├── services/          # 业务服务
│   │   ├── models/            # 数据模型
│   │   └── db/                # 数据库
│   ├── config/
│   │   └── config.yaml.example
│   ├── tests/
│   ├── requirements.txt
│   └── run.py
│
├── personal-wechat/            # 个人微信方案（备选）
│   ├── app/
│   │   ├── api/v1/endpoints/  # API 端点
│   │   ├── services/          # 业务服务
│   │   │   └── anti_ban/      # 防风控模块
│   │   ├── models/            # 数据模型
│   │   └── db/                # 数据库
│   ├── config/
│   │   └── config.yaml.example
│   ├── tests/
│   ├── requirements.txt
│   └── run.py
│
└── docs/                       # 文档资料
    ├── 企业微信/
    │   ├── 01-方案文档/        # 客户方案文档
    │   ├── 02-技术文档/        # 技术架构文档
    │   └── 03-演示PPT/         # 商务演示
    ├── 个人微信/
    │   └── 01-方案文档/        # 个人微信方案
    └── 通用/                   # 通用文档
```

---

## 快速开始

### 企业微信方案

1. **安装依赖**
```bash
cd enterprise-wechat
pip install -r requirements.txt
```

2. **配置**
```bash
cp config/config.yaml.example config/config.yaml
# 编辑 config.yaml，填入 CORP_ID、CORP_SECRET
```

3. **运行**
```bash
python run.py
```

### 个人微信方案

1. **安装依赖**
```bash
cd personal-wechat
pip install -r requirements.txt
```

2. **配置**
```bash
cp config/config.yaml.example config/config.yaml
# 编辑 config.yaml
```

3. **运行**
```bash
python run.py
```

---

## 报价参考

| 版本 | 标准报价 | 首单（案例） | 第2-5家 |
|------|---------|-------------|---------|
| 企业微信基础版 | ¥8,000 | ¥4,000 | ¥6,000 |
| 企业微信完整版 | ¥13,600 | ¥6,800 | ¥10,200 |
| 个人微信方案 | ¥16,800 | ¥8,400 | ¥12,600 |

**首单低利润作为案例积累，后续客户按标准报价执行。**

---

## 方案对比

| 对比项 | 企业微信方案 | 个人微信方案 |
|--------|------------|------------|
| 合规性 | ✅ 官方合规，零风险 | ⚠ 存在封号风险 |
| 稳定性 | ✅ 企业级稳定 | ⚠ 可能受微信更新影响 |
| 核心功能 | ✅ 全部支持 | ⚠ 部分功能受限 |
| 维护成本 | ✅ 低 | ⚠ 需跟进微信版本 |
| 自动加好友 | ✅ 支持 | ❌ 不支持 |

---

## 文档目录

详细方案文档请参考 `docs/` 目录：

- **客户方案文档**：面向非技术客户的方案说明
- **技术架构文档**：面向技术人员的架构设计
- **报价单**：详细的报价和增值服务
- **演示PPT**：商务演示文稿

---

## 联系信息

**方案设计者：墨飞科技**

如有任何问题或需要进一步演示，欢迎随时联系。

---

## 参考链接

- [企业微信开放平台](https://developer.work.weixin.qq.com)
- [WeChatFerry](https://github.com/starRTC/WeChatFerry)
- [企业微信API文档](https://developer.work.weixin.qq.com/document/)
