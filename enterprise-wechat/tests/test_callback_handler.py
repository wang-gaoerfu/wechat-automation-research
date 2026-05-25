"""回调处理器测试"""
from unittest.mock import patch, MagicMock

import pytest

from app.services.callback_handler import CallbackHandler


class TestCallbackHandler:
    """CallbackHandler 测试类"""

    @pytest.fixture
    def mock_config(self):
        """模拟配置"""
        with patch("app.services.callback_handler.get_config") as mock:
            config = type("Config", (), {})()
            config.wechat.callback_token = "test_token"
            config.wechat.callback_aes_key = "0123456789abcdef0123456789abcdef"
            config.app.debug = True
            mock.return_value = config
            yield mock

    @pytest.fixture
    def callback_handler(self, mock_config):
        """创建 CallbackHandler 实例"""
        return CallbackHandler()

    def test_parse_xml(self, callback_handler):
        """测试 XML 解析"""
        xml_str = """<xml>
            <ToUserName><![CDATA[toUser]]></ToUserName>
            <FromUserName><![CDATA[fromUser]]></FromUserName>
            <CreateTime>1234567890</CreateTime>
            <MsgType><![CDATA[text]]></MsgType>
            <Content><![CDATA[Hello]]></Content>
            <MsgId>1234567890</MsgId>
        </xml>"""

        result = callback_handler._parse_xml(xml_str)

        assert result["ToUserName"] == "toUser"
        assert result["FromUserName"] == "fromUser"
        assert result["MsgType"] == "text"
        assert result["Content"] == "Hello"
        assert result["MsgId"] == "1234567890"

    def test_handle_message(self, callback_handler):
        """测试处理普通消息"""
        data = {
            "MsgType": "text",
            "Content": "test",
            "FromUserName": "user1"
        }

        result = callback_handler._handle_message(data)

        assert result["status"] == "ok"
        assert result["msg_type"] == "text"

    def test_handle_add_external_contact(self, callback_handler):
        """测试处理添加客户事件"""
        data = {
            "Event": "add_external_contact",
            "UserID": "user1",
            "ExternalUserID": "external1",
            "State": "scene1"
        }

        result = callback_handler._handle_add_external_contact(data)

        assert result["status"] == "processed"
        assert result["action"] == "add_external_contact"
        assert result["user_id"] == "user1"
        assert result["external_userid"] == "external1"

    def test_handle_event_del_external_contact(self, callback_handler):
        """测试处理删除客户事件"""
        data = {
            "Event": "del_external_contact",
            "UserID": "user1",
            "ExternalUserID": "external1"
        }

        result = callback_handler._handle_event("del_external_contact", data)

        assert result["status"] == "processed"
        assert result["action"] == "del_external_contact"

    def test_handle_event_change_external_contact(self, callback_handler):
        """测试处理客户变更事件"""
        data = {
            "Event": "change_external_contact",
            "UserID": "user1",
            "ExternalUserID": "external1"
        }

        result = callback_handler._handle_event("change_external_contact", data)

        assert result["status"] == "processed"
        assert result["action"] == "change_external_contact"

    def test_handle_event_unknown(self, callback_handler):
        """测试处理未知事件"""
        data = {"Event": "unknown_event"}

        result = callback_handler._handle_event("unknown_event", data)

        assert result["status"] == "ignored"