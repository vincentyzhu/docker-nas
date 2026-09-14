import unittest
from unittest.mock import Mock, patch

from notifier.models import Notification
from notifier.wecom import WeComClient


class WeComTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = WeComClient(
            {
                "webhook": (
                    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test-key"
                )
            },
            {
                "timeout_seconds": 5,
                "retry_attempts": 2,
                "retry_delay_seconds": 0,
            },
        )

    @patch("notifier.wecom.requests.post")
    def test_send_markdown_payload(self, post: Mock) -> None:
        response = Mock()
        response.json.return_value = {"errcode": 0, "errmsg": "ok"}
        post.return_value = response

        self.client.send(Notification("测试", "## NAS 告警\n\n服务异常"))

        post.assert_called_once_with(
            self.client.webhook,
            json={
                "msgtype": "markdown",
                "markdown": {"content": "## NAS 告警\n\n服务异常"},
            },
            timeout=5,
        )
        response.raise_for_status.assert_called_once_with()

    def test_markdown_chunks_obey_utf8_byte_limit(self) -> None:
        content = "## 测试\n" + "告警" * 1000 + "\n" + "服务" * 1000
        chunks = self.client._markdown_chunks(content)

        self.assertGreater(len(chunks), 1)
        self.assertEqual("".join(chunks), content)
        self.assertTrue(
            all(
                len(chunk.encode("utf-8")) <= self.client.max_markdown_bytes
                for chunk in chunks
            )
        )

    @patch("notifier.wecom.time.sleep")
    @patch("notifier.wecom.requests.post")
    def test_retry_after_platform_error(self, post: Mock, sleep: Mock) -> None:
        failed = Mock()
        failed.json.return_value = {"errcode": 93000, "errmsg": "invalid webhook"}
        succeeded = Mock()
        succeeded.json.return_value = {"errcode": 0, "errmsg": "ok"}
        post.side_effect = [failed, succeeded]

        self.client.send(Notification("测试", "内容"))

        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(0)


if __name__ == "__main__":
    unittest.main()
