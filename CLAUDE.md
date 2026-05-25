# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a WeChat automation research project containing two main solution approaches:

1. **Enterprise WeChat Solution** (`enterprise-wechat-design.md`) - Official API approach using WeChat Work (企业微信) open platform
2. **Personal WeChat Solution** (`personal-wechat-deep-research.md`) - Hook-based approach using WeChatFerry

**Recommended**: Enterprise WeChat for compliance and stability; Personal WeChat as backup for scenarios without enterprise credentials.

## Architecture

### Enterprise WeChat Architecture
```
[Publish System] → [FastAPI Server] → [ChromaDB RAG] → [WeChat Work API] → [Users]
```

Key components:
- FastAPI backend with SQLite + ChromaDB
- Token manager with auto-refresh
- Message deduplication
- Audit logging

### Personal WeChat Architecture
```
[WeChat PC Client] ← [WeChatFerry DLL Hook] → [WCF Client] → [FastAPI Server]
```

Key components:
- WeChatFerry RPC client for Windows DLL injection
- Anti-ban engine (rate limiter, content diversification, behavior simulation)
- Version-adaptive offsets management

## Client-Facing Documents

| Document | Purpose |
|----------|---------|
| `微信自动化运营方案-客户版.docx` | Main proposal for clients (non-technical) |
| `微信自动化方案-报价.docx` | Pricing quote for clients |
| `微信自动化方案-技术架构.md` | Technical architecture for dev team |

## Key Constraints

### Enterprise WeChat Limits
- Mass broadcast: Max 4 messages per customer per day
- External contact API: 20 requests/minute/enterprise
- Contact: Unverified accounts have limited features; "联系我"二维码 requires enterprise verification

### Personal WeChat Risks
- Hook injection may trigger ban
- Version-dependent (supported versions: 3.9.10.19, 3.9.8.15, 3.9.6.29)
- Offset values in documentation are placeholders - actual values require reverse engineering

## Development Priorities

1. **Enterprise WeChat** - Primary solution, recommended for all clients
2. **MCP + Agent** - Smart assistant layer using Model Context Protocol for natural language control
3. **Personal WeChat** - Backup solution, only for clients without enterprise credentials

## Dependencies

```
fastapi>=0.100.0
uvicorn>=0.23.0
sqlalchemy>=2.0.0
chromadb>=0.4.0
openai>=1.0.0
apscheduler>=3.10.0
```

## Implementation Phases

1. Project structure, SQLite, ChromaDB integration
2. Token auto-refresh + message deduplication
3. Customer contact API (add friend, welcome message)
4. Message sending + anti-ban controls
5. Group auto-reply (application callback)
6. AI service integration, RAG retrieval
7. Knowledge base management API
8. APScheduler timed tasks
9. Publish system polling integration
10. Audit logging + health checks + hot-reload + backup
