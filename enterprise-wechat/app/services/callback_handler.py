"""回调处理服务"""
import base64
import hashlib
import logging
import random
import struct
import time
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, Tuple

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from app.config import get_config

logger = logging.getLogger(__name__)


class CallbackHandler:
    """回调处理器（消息加解密）"""

    def __init__(self):
        self._config = get_config()

    def verify_url(
        self,
        msg_signature: str,
        timestamp: str,
        nonce: str,
        echostr: str
    ) -> str:
        """验证回调 URL"""
        # 解密 echostr
        decrypted = self._decrypt(echostr, msg_signature, timestamp, nonce)
        return decrypted

    def handle_callback(
        self,
        msg_signature: str,
        timestamp: str,
        nonce: str,
        body: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理回调事件"""
        # 将 body 转为 XML 字符串
        xml_content = body.get("xml", "")

        # 解密消息
        decrypted_xml = self._decrypt(xml_content, msg_signature, timestamp, nonce)

        # 解析 XML
        event_dict = self._parse_xml(decrypted_xml)

        msg_type = event_dict.get("MsgType", "")
        event = event_dict.get("Event", "")

        logger.info(f"收到回调事件: msg_type={msg_type}, event={event}")

        # 处理不同事件
        if msg_type == "event":
            return self._handle_event(event, event_dict)
        else:
            return self._handle_message(event_dict)

    def _handle_event(self, event: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理事件"""
        handlers = {
            "add_external_contact": self._handle_add_external_contact,
            "del_external_contact": self._handle_del_external_contact,
            "change_external_contact": self._handle_change_external_contact,
        }

        handler = handlers.get(event)
        if handler:
            return handler(data)
        return {"status": "ignored", "event": event}

    def _handle_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理普通消息"""
        msg_type = data.get("MsgType", "")
        logger.info(f"处理消息类型: {msg_type}")
        return {"status": "ok", "msg_type": msg_type}

    def _handle_add_external_contact(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理添加客户事件"""
        user_id = data.get("UserID", "")
        external_userid = data.get("ExternalUserID", "")
        state = data.get("State", "")

        logger.info(f"新添加客户: user={user_id}, external={external_userid}, state={state}")

        # TODO: 可以在这里自动打标签或发送欢迎消息
        return {
            "status": "processed",
            "action": "add_external_contact",
            "user_id": user_id,
            "external_userid": external_userid
        }

    def _handle_del_external_contact(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理删除客户事件"""
        user_id = data.get("UserID", "")
        external_userid = data.get("ExternalUserID", "")

        logger.info(f"删除客户: user={user_id}, external={external_userid}")
        return {"status": "processed", "action": "del_external_contact"}

    def _handle_change_external_contact(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理客户变更事件"""
        user_id = data.get("UserID", "")
        external_userid = data.get("ExternalUserID", "")

        logger.info(f"客户变更: user={user_id}, external={external_userid}")
        return {"status": "processed", "action": "change_external_contact"}

    def _decrypt(
        self,
        encrypt_str: str,
        msg_signature: str,
        timestamp: str,
        nonce: str
    ) -> str:
        """解密消息"""
        token = self._config.wechat.callback_token
        encoding_aes_key = self._config.wechat.callback_aes_key

        # 验证签名
        sort_list = sorted([token, timestamp, nonce, encrypt_str])
        sign = hashlib.sha1("".join(sort_list).encode()).hexdigest()

        if sign != msg_signature:
            logger.warning(f"签名验证失败: {sign} != {msg_signature}")
            raise ValueError("签名验证失败")

        # AES 解密
        aes_key = base64.b64decode(encoding_aes_key + "=")
        encrypt_bytes = base64.b64decode(encrypt_str)

        # 去掉前 16 字节的随机串
        cipher = Cipher(
            algorithms.AES(aes_key),
            modes.CBC(aes_key[:16]),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(encrypt_bytes) + decryptor.finalize()

        # 去掉后 4 字节的随机内容
        pad_length = decrypted[-1]
        content = decrypted[16:-pad_length]

        # 去掉前 4 字节的消息长度
        msg_len = struct.unpack(">I", content[:4])[0]
        msg_content = content[4:4 + msg_len].decode("utf-8")

        return msg_content

    def _encrypt(self, reply_msg: str, timestamp: str, nonce: str) -> str:
        """加密消息（回复时使用）"""
        token = self._config.wechat.callback_token
        encoding_aes_key = self._config.wechat.callback_aes_key

        # 随机生成 16 字节
        random_str = bytes([random.randint(0, 255) for _ in range(16)])

        # 构造加密内容
        content = random_str + struct.pack(">I", len(reply_msg)) + reply_msg.encode("utf-8")

        # PKCS7 填充
        block_size = 32
        pad_length = block_size - (len(content) % block_size)
        content += bytes([pad_length] * pad_length)

        # AES 加密
        aes_key = base64.b64decode(encoding_aes_key + "=")
        cipher = Cipher(
            algorithms.AES(aes_key),
            modes.CBC(aes_key[:16]),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(content) + encryptor.finalize()

        # 构造签名
        sort_list = sorted([token, timestamp, nonce, base64.b64encode(encrypted).decode()])
        sign = hashlib.sha1("".join(sort_list).encode()).hexdigest()

        return base64.b64encode(encrypted).decode()

    def _parse_xml(self, xml_str: str) -> Dict[str, Any]:
        """解析 XML 为字典"""
        parser = ET.XMLParser(resolve_entities=False)
        root = ET.fromstring(xml_str, parser=parser)
        result = {}

        for child in root:
            result[child.tag] = child.text or ""

        return result