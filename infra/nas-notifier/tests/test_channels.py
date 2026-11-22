import unittest
from unittest.mock import patch

from notifier.config import ConfigError
from notifier.dingtalk import DingTalkClient
from notifier.main import build_sender
from notifier.models import Notification
from notifier.wecom import WeComClient
from notifier.wecom_relay import WeComRelayClient


class ChannelTests(unittest.TestCase):
    @staticmethod
    def config(channel: str | None = None) -> dict:
        notifier = {"type": "canventory"}
        if channel is not None:
            notifier["channel"] = channel
        return {
            "notifier": notifier,
            "dingtalk": {
                "webhook": "https://oapi.dingtalk.com/robot/send?access_token=test"
            },
            "wecom": {
                "webhook": (
                    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test"
                )
            },
            "http": {},
            "wecom_relay": {"url": "https://relay.example.com/notify/friend"},
        }

    def test_old_config_defaults_to_dingtalk(self) -> None:
        channel, sender = build_sender(self.config())

        self.assertEqual(channel, "dingtalk")
        self.assertIsInstance(sender, DingTalkClient)

    def test_wecom_channel_builds_wecom_client(self) -> None:
        channel, sender = build_sender(self.config("wecom"))

        self.assertEqual(channel, "wecom")
        self.assertIsInstance(sender, WeComClient)

    def test_unknown_channel_is_rejected(self) -> None:
        with self.assertRaisesRegex(ConfigError, "wecom_relay"):
            build_sender(self.config("unknown"))

    @patch.dict("os.environ", {"WECOM_RELAY_TOKEN": "test-friend-token"})
    @patch("notifier.wecom_relay.requests.post")
    def test_relay_routes_plain_text_to_configured_recipient(self, post) -> None:
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"status": "ok"}
        channel, sender = build_sender(self.config("wecom_relay"))
        self.assertEqual(channel, "wecom_relay")
        self.assertIsInstance(sender, WeComRelayClient)
        sender.send(Notification("家庭 B", "**库存提醒**", "库存提醒"))
        post.assert_called_once_with(
            "https://relay.example.com/notify/friend",
            headers={"Authorization": "Bearer test-friend-token"},
            json={"content": "库存提醒"},
            timeout=20,
            allow_redirects=False,
        )

    @patch.dict("os.environ", {"WECOM_RELAY_TOKEN": "test-owner-token"})
    @patch("notifier.wecom_relay.requests.post")
    def test_relay_does_not_retry_ambiguous_failure(self, post) -> None:
        post.return_value.status_code = 502
        _, sender = build_sender(self.config("wecom_relay"))
        with self.assertRaisesRegex(RuntimeError, "HTTP 502"):
            sender.send(Notification("家庭 A", "库存提醒"))
        post.assert_called_once()


if __name__ == "__main__":
    unittest.main()
