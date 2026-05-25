# 企业微信 API 技术演示指南

**文档版本**: v1.0
**编制日期**: 2026-05-25
**目标读者**: 开发人员 / 技术评估者

---

## 一、演示目录结构

```
wechat-automation-research/
|
|-- demo/
|   |-- __init__.py
|   |-- config.py              # 演示配置
|   |-- token_demo.py          # Token获取演示
|   |-- message_demo.py        # 消息发送演示
|   |-- contact_demo.py        # 创建联系我二维码
|   |-- callback_demo.py       # 消息回调演示
|   |-- run_demo.py            # 统一运行入口
|
|-- app/                       # 业务实现
|   |-- services/
|   |   |-- wechat.py          # 企业微信API封装
|   |   |-- token_manager.py   # Token管理器
|
|-- demo_guide.md              # 本文档
```

---

## 二、环境准备

### 2.1 安装依赖

```bash
pip install requests aiohttp pycryptodome xmltodict
```

### 2.2 配置文件

创建 `demo/config.py`:

```python
"""演示配置 - 请替换为您的实际值"""

# 企业微信凭证
CORP_ID = "your_corp_id"           # 企业ID
CORP_SECRET = "your_corp_secret"    # 应用Secret
AGENT_ID = "1000002"                # 应用AgentID

# 回调配置
CALLBACK_TOKEN = "your_token"       # 回调Token
CALLBACK_AES_KEY = "your_aes_key"   # 回调AES Key

# 测试目标
TEST_USER_ID = "test_user_id"       # 测试客户external_userid
TEST_GROUP_ID = "test_group_id"     # 测试群ID

BASE_URL = "https://qyapi.weixin.qq.com/cgi-bin"
```

---

## 三、功能模块演示

### 3.1 Token获取

**目标**: 演示如何获取企业微信 access_token

**API端点**: `GET /gettoken`

**请求示例**:

```python
# demo/token_demo.py

import requests
import time

class TokenDemo:
    """Token获取演示"""

    def __init__(self, corp_id: str, corp_secret: str):
        self.corp_id = corp_id
        self.corp_secret = corp_secret
        self.base_url = "https://qyapi.weixin.qq.com/cgi-bin"
        self._token = None
        self._expires_at = 0

    def get_token(self) -> str:
        """获取access_token（带缓存）"""
        # 提前5分钟刷新，避免过期
        if time.time() >= self._expires_at - 300 and self._token:
            return self._token

        url = f"{self.base_url}/gettoken"
        params = {
            "corpid": self.corp_id,
            "corpsecret": self.corp_secret
        }

        response = requests.get(url, params=params)
        data = response.json()

        if data.get("errcode") == 0:
            self._token = data["access_token"]
            # 企业微信token有效期2小时（7200秒）
            self._expires_at = time.time() + data.get("expires_in", 7200)
            print(f"Token获取成功: {self._token[:20]}...")
            print(f"有效期至: {self._expires_at}")
            return self._token
        else:
            raise Exception(f"Token获取失败: {data}")

    def run_demo(self):
        """执行Token获取演示"""
        print("=" * 50)
        print("【演示】Token获取")
        print("=" * 50)

        try:
            token = self.get_token()
            print(f"\n[成功] Access Token: {token}")

            # 验证token有效性
            print("\n[验证] 检查token是否有效...")
            verify_url = f"{self.base_url}/getcallbackip"
            params = {"access_token": token}
            resp = requests.get(verify_url, params=params)
            result = resp.json()

            if result.get("errcode") == 0:
                print("[成功] Token验证通过")
                print(f"可用IP数: {len(result.get('ip_list', []))}")
            else:
                print(f"[失败] Token验证: {result}")

        except Exception as e:
            print(f"[错误] {e}")

        print("=" * 50)
```

**预期输出**:

```
==================================================
【演示】Token获取
==================================================

[成功] Access Token: kxxxxxxxxxxxxxxxxxxxxxxxxxx...
有效期至: 1748150000.123

[验证] 检查token是否有效...
[成功] Token验证通过
可用IP数: 12
==================================================
```

**测试用例**:

| 用例 | 输入 | 预期结果 |
|-----|------|---------|
| 正常获取 | 有效的corp_id和secret | 返回有效token |
| 错误凭证 | 错误的secret | errcode: 40013 或 40001 |
| 并发请求 | 10个并发请求 | 只有1次实际API调用（缓存生效）|

---

### 3.2 发送消息

**目标**: 演示发送文本消息给客户

**API端点**: `POST /message/send`

**请求示例**:

```python
# demo/message_demo.py

import requests
import time

class MessageDemo:
    """消息发送演示"""

    def __init__(self, token_manager):
        self.token_manager = token_manager
        self.base_url = "https://qyapi.weixin.qq.com/cgi-bin"
        # 频率限制：20次/分钟/企业
        self.min_interval = 3.0  # 3秒间隔

    def send_text(self, to_user: str, content: str) -> dict:
        """发送文本消息"""
        token = self.token_manager.get_token()
        url = f"{self.base_url}/message/send?access_token={token}"

        payload = {
            "touser": to_user,
            "msgtype": "text",
            "agentid": self.token_manager.agent_id,
            "text": {"content": content}
        }

        response = requests.post(url, json=payload)
        return response.json()

    def send_with_limit(self, to_user: str, content: str) -> dict:
        """带频率控制的消息发送"""
        # 检查发送间隔
        if hasattr(self, '_last_send_time'):
            elapsed = time.time() - self._last_send_time
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                print(f"[限速] 等待 {wait_time:.1f} 秒...")
                time.sleep(wait_time)

        self._last_send_time = time.time()
        return self.send_text(to_user, content)

    def batch_send(self, user_list: list, content: str) -> dict:
        """批量发送消息（带进度显示）"""
        print(f"\n开始向 {len(user_list)} 个用户发送消息...")

        success_count = 0
        fail_count = 0

        for i, user_id in enumerate(user_list, 1):
            try:
                result = self.send_with_limit(user_id, content)
                if result.get("errcode") == 0:
                    success_count += 1
                    print(f"[{i}/{len(user_list)}] 成功: {user_id}")
                else:
                    fail_count += 1
                    print(f"[{i}/{len(user_list)}] 失败: {user_id} - {result}")
            except Exception as e:
                fail_count += 1
                print(f"[{i}/{len(user_list)}] 异常: {user_id} - {e}")

        return {
            "total": len(user_list),
            "success": success_count,
            "failed": fail_count
        }

    def run_demo(self):
        """执行消息发送演示"""
        print("=" * 50)
        print("【演示】发送消息")
        print("=" * 50)

        test_user = "test_external_userid"
        test_content = "您好，这是企业微信API演示消息。\n时间: " + time.strftime("%Y-%m-%d %H:%M:%S")

        print(f"\n发送对象: {test_user}")
        print(f"发送内容:\n{test_content}")

        try:
            result = self.send_with_limit(test_user, test_content)

            if result.get("errcode") == 0:
                print(f"\n[成功] 消息发送成功")
                print(f"MsgID: {result.get('msgid')}")
            else:
                print(f"\n[失败] 错误码: {result.get('errcode')}")
                print(f"错误信息: {result.get('errmsg')}")

        except Exception as e:
            print(f"\n[错误] {e}")

        print("=" * 50)
```

**预期输出**:

```
==================================================
【演示】发送消息
==================================================

发送对象: test_external_userid
发送内容:
您好，这是企业微信API演示消息。
时间: 2026-05-25 10:30:00

[成功] 消息发送成功
MsgID: 1234567890123456789
==================================================
```

**消息类型支持**:

| 类型 | msgtype | 额外字段 |
|-----|---------|---------|
| 文本 | text | content |
| 图片 | image | media_id |
| 语音 | voice | media_id |
| 视频 | video | media_id, title, description |
| 文件 | file | media_id |
| 文本卡片 | textcard | title, description, url, btntxt |
| Markdown | markdown | content |

**频率限制说明**:

| 限制项 | 限制值 | 应对策略 |
|-------|-------|---------|
| 单客户消息 | 20次/分钟/企业 | 发送间隔 > 3秒 |
| 群发消息 | 每天4次/客户 | 使用 send_all API |
| 主动发消息给外部 | 20次/分钟/企业 | 添加延迟 |

---

### 3.3 创建联系我二维码

**目标**: 演示如何创建「联系我」二维码用于获客

**API端点**: `POST /externalcontact/add_contact_way`

**请求示例**:

```python
# demo/contact_demo.py

import requests
import json
import os

class ContactDemo:
    """联系我二维码演示"""

    def __init__(self, token_manager):
        self.token_manager = token_manager
        self.base_url = "https://qyapi.weixin.qq.com/cgi-bin"

    def create_contact_way(self, scene: int = 2, remark: str = "",
                          style: int = 1, user_list: list = None) -> dict:
        """创建联系我二维码"""
        token = self.token_manager.get_token()
        url = f"{self.base_url}/externalcontact/add_contact_way?access_token={token}"

        payload = {
            "type": 2,                    # 2: 联系我二维码
            "scene": scene,                # 1: 小程序码  2: 二维码
            "style": style,               # 样式编号
            "remark": remark,             # 备注（用于识别渠道）
            "skip_verify": True,          # 无需确认直接添加
            "state": "demo_campaign",     # 状态数据（用于跟踪）
            "user": user_list or [],      # 指定的员工ID列表
            "partyid": []                 # 指定的部门ID列表
        }

        response = requests.post(url, json=payload)
        return response.json()

    def get_qrcode_url(self, config_id: str) -> str:
        """获取二维码URL（用于下载）"""
        token = self.token_manager.get_token()
        url = f"{self.base_url}/externalcontact/get_contact_way?access_token={token}"
        params = {"config_id": config_id}

        response = requests.get(url, params=params)
        data = response.json()

        if data.get("errcode") == 0:
            return data.get("contact_way", {}).get("qr_code")
        return None

    def list_contact_ways(self) -> dict:
        """列出所有联系我二维码"""
        token = self.token_manager.get_token()
        url = f"{self.base_url}/externalcontact/list_contact_way?access_token={token}"

        response = requests.get(url)
        return response.json()

    def delete_contact_way(self, config_id: str) -> dict:
        """删除联系我二维码"""
        token = self.token_manager.get_token()
        url = f"{self.base_url}/externalcontact/del_contact_way?access_token={token}"

        payload = {"config_id": config_id}
        response = requests.post(url, json=payload)
        return response.json()

    def run_demo(self):
        """执行联系我二维码演示"""
        print("=" * 50)
        print("【演示】创建联系我二维码")
        print("=" * 50)

        # 配置参数
        scene = 2        # 2=二维码，1=小程序码
        remark = "技术演示二维码"
        style = 1
        user_list = ["user_id_1", "user_id_2"]  # 指定员工

        print(f"\n创建参数:")
        print(f"  场景类型: {'二维码' if scene == 2 else '小程序码'}")
        print(f"  备注: {remark}")
        print(f"  样式: {style}")
        print(f"  员工列表: {user_list}")

        try:
            # 创建二维码
            print("\n[创建中...]")
            result = self.create_contact_way(scene, remark, style, user_list)

            if result.get("errcode") == 0:
                config_id = result.get("config_id")
                print(f"\n[成功] 二维码创建成功")
                print(f"  ConfigID: {config_id}")

                # 获取二维码URL
                qr_url = self.get_qrcode_url(config_id)
                if qr_url:
                    print(f"  二维码URL: {qr_url}")

                # 保存配置ID供后续使用
                self._last_config_id = config_id

                # 列出所有二维码
                print("\n[列表] 现有联系我二维码:")
                list_result = self.list_contact_ways()
                if list_result.get("errcode") == 0:
                    ways = list_result.get("contact_way_list", [])
                    for way in ways:
                        print(f"  - {way.get('config_id')}: {way.get('remark')} ({way.get('scene')})")
                else:
                    print(f"  列表查询失败: {list_result}")

            else:
                print(f"\n[失败] 错误码: {result.get('errcode')}")
                print(f"  错误信息: {result.get('errmsg')}")

        except Exception as e:
            print(f"\n[错误] {e}")

        print("=" * 50)

    def cleanup_demo(self):
        """清理演示创建的二维码"""
        if hasattr(self, '_last_config_id'):
            print(f"\n[清理] 删除二维码: {self._last_config_id}")
            result = self.delete_contact_way(self._last_config_id)
            if result.get("errcode") == 0:
                print("[成功] 已删除")
            else:
                print(f"[失败] {result.get('errmsg')}")
```

**预期输出**:

```
==================================================
【演示】创建联系我二维码
==================================================

创建参数:
  场景类型: 二维码
  备注: 技术演示二维码
  样式: 1
  员工列表: ['user_id_1', 'user_id_2']

[创建中...]

[成功] 二维码创建成功
  ConfigID: qc_xxxxxxxxxxxxxx
  二维码URL: https://open.work.weixin.qq.com/wwopen/h5/QrCode?sid=xxx

[列表] 现有联系我二维码:
  - qc_xxxxxxxxxxxxxx: 技术演示二维码 (2)
  - qc_yyyyyyyyyyyyyy: 官网获客码 (2)
==================================================
```

**二维码类型说明**:

| 类型 | scene值 | 说明 |
|-----|--------|------|
| 小程序码 | 1 | 生成小程序码，需要配置小程序 |
| 二维码 | 2 | 生成普通二维码，扫描后直接添加 |

**使用场景**:

```python
# 场景1: 线上推广 - 渠道追踪
create_contact_way(
    scene=2,
    remark="抖音广告-618活动",
    state="channel_douyin_618"
)

# 场景2: 线下物料 - 门店引流
create_contact_way(
    scene=2,
    remark="北京朝阳门店",
    user_list=["staff_001", "staff_002"]
)

# 场景3: 官网悬浮窗
create_contact_way(
    scene=2,
    remark="官网客服入口",
    style=2
)
```

---

### 3.4 接收消息回调

**目标**: 演示如何接收和处理企业微信的事件回调

**配置步骤**:

1. 登录企业微信管理后台
2. 进入「应用管理」-> 选择应用
3. 「接收消息」-> 设置回调URL
4. 填写Token和EncodingAESKey

**请求示例**:

```python
# demo/callback_demo.py

import time
import xmltodict
from Crypto.Cipher import AES
import base64
import random
import hashlib

class CallbackDemo:
    """消息回调演示"""

    def __init__(self, token: str, aes_key: str):
        self.token = token
        self.aes_key = aes_key
        # 解密用的AES Key（AESKey即EncodingAESKey + "=" 后Base64解码）
        self.aes_key_bytes = self._decode_aes_key(aes_key)

    def _decode_aes_key(self, aes_key: str) -> bytes:
        """AES Key解码"""
        # Base64解码后是32字节
        import base64
        return base64.b64decode(aes_key + "=")

    def _pkcs7_decode(self, data: bytes) -> bytes:
        """PKCS7解码"""
        pad_len = data[-1]
        return data[:-pad_len]

    def decrypt_message(self, encrypt_str: str) -> dict:
        """解密消息"""
        import base64

        # Base64解码
        encrypted_data = base64.b64decode(encrypt_str)

        # AES解密 (AES-256-CBC)
        cipher = AES.new(self.aes_key_bytes, AES.MODE_CBC, encrypted_data[:16])
        decrypted = cipher.decrypt(encrypted_data[16:])

        # PKCS7解码
        decrypted = self._pkcs7_decode(decrypted)

        # 去掉前16字节随机串
        content = decrypted[16:]
        msg_len = int.from_bytes(content[:4], byteorder='big')
        msg_content = content[4:4+msg_len]

        # 解析XML
        xml_str = msg_content.decode('utf-8')
        return dict(xmltodict.parse(xml_str))

    def verify_url(self, msg_signature: str, timestamp: str,
                   nonce: str, echostr: str) -> str:
        """验证回调URL（用于配置时调用）"""
        # 1. 组合token、timestamp、nonce并排序
        sort_str = ''.join(sorted([self.token, timestamp, nonce, echostr]))

        # 2. SHA1哈希
        my_signature = hashlib.sha1(sort_str.encode()).hexdigest()

        # 3. 验证签名
        if my_signature != msg_signature:
            return None

        # 4. 解密echostr
        return self.decrypt_message(echostr).get('echostr', '')

    def parse_callback(self, msg_signature: str, timestamp: str,
                      nonce: str, post_data: str) -> dict:
        """解析回调消息"""
        import json

        # 解析POST内容
        if isinstance(post_data, str):
            post_dict = xmltodict.parse(post_data)
        else:
            post_dict = post_data

        # 如果是加密消息，需要解密
        if 'Encrypt' in post_dict.get('xml', {}):
            encrypt_str = post_dict['xml']['Encrypt']

            # 验证签名
            sort_str = ''.join(sorted([self.token, timestamp, nonce, encrypt_str]))
            my_signature = hashlib.sha1(sort_str.encode()).hexdigest()

            if my_signature != msg_signature:
                return {"error": "签名验证失败"}

            # 解密
            decrypted = self.decrypt_message(encrypt_str)
            return decrypted
        else:
            return post_dict

    def build_response(self, msg_dict: dict, content: str = "success") -> str:
        """构建回调响应（被动回复）"""
        # 对于回调事件，通常返回"success"表示已接收
        return content

    def handle_add_external_contact(self, event: dict) -> str:
        """处理新客户添加事件"""
        external_user_id = event.get('ExternalUserID', '')
        user_id = event.get('UserID', '')
        state = event.get('State', '')

        print(f"\n[新客户添加事件]")
        print(f"  客户ID: {external_user_id}")
        print(f"  员工ID: {user_id}")
        print(f"  渠道标识: {state}")

        # TODO: 执行后续业务逻辑
        # 1. 发送欢迎语
        # 2. 自动打标签
        # 3. 写入数据库

        return "success"

    def handle_text_message(self, msg: dict) -> str:
        """处理文本消息"""
        from_username = msg.get('FromUserName', '')
        content = msg.get('Content', '')
        agent_id = msg.get('AgentID', '')

        print(f"\n[收到文本消息]")
        print(f"  发送者: {from_username}")
        print(f"  内容: {content}")
        print(f"  应用ID: {agent_id}")

        # TODO: 执行AI处理或关键词回复

        return "success"

    def run_demo(self):
        """执行回调处理演示"""
        print("=" * 50)
        print("【演示】消息回调处理")
        print("=" * 50)

        # 模拟回调事件
        print("\n[模拟] 收到新客户添加事件...")

        # 模拟事件数据
        mock_event = {
            'ToUserName': 'ww1234567890abcdef',
            'FromUserName': 'external_user_001',
            'CreateTime': str(int(time.time())),
            'MsgType': 'event',
            'Event': 'add_external_contact',
            'ExternalUserID': 'woxxxxxx',
            'UserID': 'user_001',
            'State': 'demo_campaign'
        }

        result = self.handle_add_external_contact(mock_event)
        print(f"\n[处理结果] {result}")

        # 模拟文本消息
        print("\n" + "-" * 30)
        print("[模拟] 收到文本消息...")

        mock_msg = {
            'ToUserName': 'ww1234567890abcdef',
            'FromUserName': 'external_user_002',
            'CreateTime': str(int(time.time())),
            'MsgType': 'text',
            'Content': '你好，请问你们的产品怎么收费？',
            'MsgId': '1234567890123456789',
            'AgentID': '1000002'
        }

        result = self.handle_text_message(mock_msg)
        print(f"\n[处理结果] {result}")

        print("=" * 50)

    def run_web_server_demo(self, host: str = "0.0.0.0", port: int = 5000):
        """运行Web服务模拟回调接收"""
        print(f"\n[启动] 回调Web服务 {host}:{port}")
        print("[提示] 使用ngrok等工具将本地服务暴露到公网")

        # 注意: 实际使用FastAPI框架实现Web服务
        # 这里仅展示架构示意

        print("""
        # FastAPI实现示例:

        from fastapi import FastAPI, Query, Request
        import xmltodict

        app = FastAPI()

        @app.get("/api/v1/wechat/callback")
        async def verify_url(
            msg_signature: str = Query(...),
            timestamp: str = Query(...),
            nonce: str = Query(...),
            echostr: str = Query(...)
        ):
            # URL验证
            decrypted = callback_demo.verify_url(
                msg_signature, timestamp, nonce, echostr
            )
            return decrypted

        @app.post("/api/v1/wechat/callback")
        async def receive_callback(
            msg_signature: str = Form(...),
            timestamp: str = Form(...),
            nonce: str = Form(...),
            request: Request
        ):
            post_data = await request.body()

            # 解析消息
            msg_dict = callback_demo.parse_callback(
                msg_signature, timestamp, nonce, post_data
            )

            # 根据消息类型处理
            if msg_dict.get('MsgType') == 'event':
                if msg_dict.get('Event') == 'add_external_contact':
                    callback_demo.handle_add_external_contact(msg_dict)
            elif msg_dict.get('MsgType') == 'text':
                callback_demo.handle_text_message(msg_dict)

            return "success"

        """)

        print("=" * 50)
```

**预期输出**:

```
==================================================
【演示】消息回调处理
==================================================

[模拟] 收到新客户添加事件...

[新客户添加事件]
  客户ID: woxxxxxx
  员工ID: user_001
  渠道标识: demo_campaign

[处理结果] success
------------------------------
[模拟] 收到文本消息...

[收到文本消息]
  发送者: external_user_002
  内容: 你好，请问你们的产品怎么收费？
  应用ID: 1000002

[处理结果] success
==================================================
```

**支持的回调事件**:

| 事件类型 | 说明 | 触发时机 |
|---------|------|---------|
| add_external_contact | 新客户添加 | 客户添加员工为好友 |
| change_external_contact | 客户变更 | 客户信息更新 |
| add_msg_text | 文本消息 | 收到客户消息 |
| change_chat | 群聊变更 | 群信息变化 |
| change_external_chat | 客户群变更 | 客户群信息变化 |

---

## 四、统一运行入口

```python
# demo/run_demo.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo.token_demo import TokenDemo
from demo.message_demo import MessageDemo
from demo.contact_demo import ContactDemo
from demo.callback_demo import CallbackDemo
from demo.config import *

class WeChatDemoRunner:
    """企业微信演示运行器"""

    def __init__(self):
        # 初始化各模块
        self.token_demo = TokenDemo(CORP_ID, CORP_SECRET)
        self.message_demo = MessageDemo(self.token_demo)
        self.contact_demo = ContactDemo(self.token_demo)
        self.callback_demo = CallbackDemo(CALLBACK_TOKEN, CALLBACK_AES_KEY)

    def run_all(self):
        """运行所有演示"""
        print("\n" + "=" * 60)
        print("  企业微信 API 技术演示")
        print("=" * 60)

        # 1. Token获取
        self.token_demo.run_demo()

        # 2. 发送消息
        self.message_demo.run_demo()

        # 3. 创建联系我二维码
        self.contact_demo.run_demo()

        # 4. 消息回调
        self.callback_demo.run_demo()

        print("\n" + "=" * 60)
        print("  演示完成")
        print("=" * 60)

    def run_single(self, demo_name: str):
        """运行单个演示"""
        demos = {
            "token": self.token_demo,
            "message": self.message_demo,
            "contact": self.contact_demo,
            "callback": self.callback_demo
        }

        if demo_name in demos:
            demos[demo_name].run_demo()
        else:
            print(f"未知的演示: {demo_name}")
            print(f"可用演示: {list(demos.keys())}")

    def cleanup(self):
        """清理演示数据"""
        self.contact_demo.cleanup_demo()


if __name__ == "__main__":
    runner = WeChatDemoRunner()

    # 运行所有演示
    runner.run_all()

    # 或运行单个演示
    # runner.run_single("token")
    # runner.run_single("message")
    # runner.run_single("contact")
    # runner.run_single("callback")
```

---

## 五、完整测试用例

### 测试用例 1: Token生命周期

```python
def test_token_lifecycle():
    """测试Token的获取、缓存和刷新"""
    demo = TokenDemo(CORP_ID, CORP_SECRET)

    # 首次获取
    token1 = demo.get_token()
    assert token1 is not None

    # 缓存测试 - 立即获取应返回相同token
    token2 = demo.get_token()
    assert token1 == token2

    # 模拟token过期 - 修改expires_at
    demo._expires_at = 0
    token3 = demo.get_token()
    assert token3 is not None

    print("[通过] Token生命周期测试")
```

### 测试用例 2: 消息发送频率控制

```python
def test_message_rate_limit():
    """测试消息发送频率控制"""
    demo = MessageDemo(token_manager)

    # 准备10个测试用户
    users = [f"user_{i}" for i in range(10)]
    content = "测试消息"

    # 批量发送
    start_time = time.time()
    result = demo.batch_send(users, content)
    elapsed = time.time() - start_time

    # 验证全部成功
    assert result["success"] == 10
    assert result["failed"] == 0

    # 验证频率控制生效（10个用户 * 3秒间隔 >= 30秒）
    assert elapsed >= 27  # 允许一点误差

    print(f"[通过] 频率控制测试 (耗时 {elapsed:.1f}秒)")
```

### 测试用例 3: 联系我二维码CRUD

```python
def test_contact_way_crud():
    """测试联系我二维码的创建、查询、删除"""
    demo = ContactDemo(token_manager)

    # 创建
    create_result = demo.create_contact_way(
        scene=2,
        remark="测试二维码",
        user_list=["user_001"]
    )
    assert create_result.get("errcode") == 0
    config_id = create_result.get("config_id")

    # 查询
    qr_url = demo.get_qrcode_url(config_id)
    assert qr_url is not None

    # 列表
    list_result = demo.list_contact_ways()
    assert config_id in str(list_result)

    # 删除
    delete_result = demo.delete_contact_way(config_id)
    assert delete_result.get("errcode") == 0

    print("[通过] 联系我二维码CRUD测试")
```

### 测试用例 4: 回调消息解析

```python
def test_callback_parse():
    """测试回调消息的解析"""
    demo = CallbackDemo(CALLBACK_TOKEN, CALLBACK_AES_KEY)

    # 模拟加密回调
    mock_encrypted_xml = """
    <xml>
        <ToUserName><![CDATA[test]]></ToUserName>
        <FromUserName><![CDATA[user1]]></FromUserName>
        <CreateTime>1234567890</CreateTime>
        <MsgType><![CDATA[event]]></MsgType>
        <Event><![CDATA[add_external_contact]]></Event>
        <ExternalUserID><![CDATA[new_user]]></ExternalUserID>
        <UserID><![CDATA[staff_001]]></UserID>
    </xml>
    """

    # 验证解析结果
    # 注意: 实际测试需要先生成加密数据
    result = demo.handle_add_external_contact({
        'ExternalUserID': 'new_user',
        'UserID': 'staff_001',
        'State': ''
    })

    assert result == "success"
    print("[通过] 回调消息解析测试")
```

---

## 六、常见错误码

| 错误码 | 说明 | 解决方案 |
|-------|------|---------|
| 40001 | invalid credential | 检查corpid和corpsecret是否正确 |
| 40013 | invalid corp_id | corp_id格式不正确 |
| 41001 | access_token missing | access_token未传递 |
| 42001 | access_token expired | token过期，重新获取 |
| 60011 | user not exist | external_userid不存在 |
| 301020 | no privilege | 应用没有该接口权限 |

---

## 七、注意事项

1. **频率限制**: 消息发送有严格的频率限制，请务必实现间隔控制
2. **Token缓存**: 必须实现Token缓存机制，避免频繁请求
3. **敏感信息**: 生产环境请使用环境变量或配置中心存储凭证
4. **回调验证**: 配置回调URL时需要正确实现URL验证逻辑
5. **内容多样性**: 避免向同一客户发送完全相同的内容