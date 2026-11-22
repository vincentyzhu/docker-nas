import os
from typing import Any
from urllib.parse import urlsplit

import requests

from notifier.config import ConfigError, as_int, required_text
from notifier.log import log
from notifier.models import Notification


class WeComRelayClient:
    def __init__(self, config: dict[str, Any], http_config: dict[str, Any]) -> None:
        self.url = required_text(config.get("url"), "wecom_relay.url")
        try:
            url = urlsplit(self.url)
        except ValueError:
            raise ConfigError("wecom_relay.url 无效") from None
        if (
            url.scheme != "https"
            or not url.hostname
            or not url.path.startswith("/notify/")
            or url.username is not None
            or url.query
            or url.fragment
        ):
            raise ConfigError("wecom_relay.url 必须是 HTTPS 通知地址")
        self.token = required_text(os.getenv("WECOM_RELAY_TOKEN"), "WECOM_RELAY_TOKEN")
        self.timeout = as_int(
            http_config.get("timeout_seconds", 20), "http.timeout_seconds", minimum=1
        )

    def send(self, notification: Notification) -> None:
        payload = {"content": notification.plain_text or notification.text}
        try:
            response = requests.post(
                self.url,
                headers={"Authorization": f"Bearer {self.token}"},
                json=payload,
                timeout=self.timeout,
                allow_redirects=False,
            )
        except requests.RequestException:
            raise RuntimeError("企业微信中继连接失败，发送结果未知") from None

        if response.status_code != 200:
            raise RuntimeError(f"企业微信中继发送失败：HTTP {response.status_code}")
        try:
            result = response.json()
        except ValueError:
            raise RuntimeError("企业微信中继返回无效 JSON") from None
        if not isinstance(result, dict) or result.get("status") != "ok":
            raise RuntimeError("企业微信中继未确认发送成功")
        log("企业微信中继", f"发送成功：{notification.title}")
