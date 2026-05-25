# 企业微信自动化项目

基于 FastAPI 的企业微信自动化服务，提供消息发送、客户管理、回调处理等功能。

## 功能特性

- 消息发送（文本、Markdown、群发）
- 客户管理（创建联系我二维码、获取客户列表、自动打标签）
- 回调处理（消息加解密、事件处理）
- Token 自动刷新（提前5分钟）
- 频率控制（20次/分钟）

## 安装

```bash
pip install -r requirements.txt
```

## 配置

复制 `config/config.yaml.example` 为 `config/config.yaml`，并填入你的企业微信配置：

```yaml
wechat:
  corp_id: "YOUR_CORP_ID"
  corp_secret: "YOUR_CORP_SECRET"
  agent_id: "1000002"
  callback_token: "YOUR_CALLBACK_TOKEN"
  callback_aes_key: "YOUR_CALLBACK_AES_KEY"

database:
  url: "sqlite:///./wechat.db"

app:
  host: "0.0.0.0"
  port: 8000
  debug: false
```

或者设置环境变量：

```bash
export CORP_ID=your_corp_id
export CORP_SECRET=your_corp_secret
export AGENT_ID=1000002
export CALLBACK_TOKEN=your_callback_token
export CALLBACK_AES_KEY=your_callback_aes_key
```

## 运行

```bash
python run.py
```

## API 文档

启动后访问 http://localhost:8000/docs 查看 API 文档。

## 测试

```bash
pytest tests/
```