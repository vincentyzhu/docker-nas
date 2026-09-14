import unittest

from notifier.config import ConfigError
from notifier.dingtalk import DingTalkClient
from notifier.main import build_sender
from notifier.wecom import WeComClient


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
        with self.assertRaisesRegex(ConfigError, "dingtalk 或 wecom"):
            build_sender(self.config("unknown"))


if __name__ == "__main__":
    unittest.main()
