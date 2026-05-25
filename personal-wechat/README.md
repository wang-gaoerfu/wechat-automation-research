# Personal WeChat Automation

A FastAPI-based service for WeChat automation using WeChatFerry (WCF).

## Features

- **WeChatFerry Integration**: Connect to WeChat via WCF RPC
- **Message Handling**: Send/receive text, images, files
- **Contact Management**: Sync and manage contacts
- **Anti-Ban Protection**:
  - Rate limiting (daily limits, intervals)
  - Content diversity generation
  - Behavior simulation
- **REST API**: FastAPI-based API endpoints

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Copy the example config and modify as needed:

```bash
cp config/config.yaml.example config/config.yaml
```

### Environment Variables

- `WCF_HOST`: WeChatFerry host (default: localhost)
- `WCF_PORT`: WeChatFerry port (default: 10086)

## Usage

Start the service:

```bash
python run.py
```

Or with uvicorn directly:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## API Endpoints

### System
- `GET /api/v1/system/health` - Health check
- `GET /api/v1/system/status/wcf` - WCF connection status
- `POST /api/v1/system/reconnect` - Force reconnect

### Message
- `POST /api/v1/message/text` - Send text message
- `POST /api/v1/message/image` - Send image message

### Contact
- `GET /api/v1/contact/list` - Get contact list
- `GET /api/v1/contact/{wxid}` - Get contact info
- `POST /api/v1/contact/sync` - Sync contacts to DB

### WeChat
- `POST /api/v1/wechat/callback` - Message callback webhook

## Testing

```bash
pytest tests/ -v
```

## Project Structure

```
personal-wechat/
├── app/
│   ├── api/v1/endpoints/   # API endpoints
│   ├── services/           # Business logic
│   │   ├── anti_ban/       # Anti-ban modules
│   │   ├── wcf_client.py   # WCF wrapper
│   │   └── ...
│   ├── models/             # Pydantic models
│   ├── db/                 # Database
│   ├── config.py           # Configuration
│   └── main.py             # FastAPI app
├── tests/                  # Unit tests
├── config/                 # Config files
├── run.py                  # Entry point
└── requirements.txt
```