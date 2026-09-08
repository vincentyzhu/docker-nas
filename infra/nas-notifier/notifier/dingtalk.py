import base64
import hashlib
import hmac
import time
import urllib.parse
from typing import Any

import requests

from notifier.config import as_int, required_text
from notifier.log import log
from notifier.models import Notification


class DingTalkClient:
    def __init__(self, config: dict[str, Any], http_config: dict[str, Any]) -> None:
        self.webhook = required_text(config.get("webhook"), "dingtalk.webhook")
        self.secret = str(config.get("secret", "")).strip()
        self.timeout = as_int(
            http_config.get("timeout_seconds", 20),
            "http.timeout_seconds",
            minimum=1,
        )
        self.attempts = as_int(
            http_config.get("retry_attempts", 3),
            "http.retry_attempts",
            minimum=1,
        )
        self.retry_delay = as_int(
            http_config.get("retry_delay_seconds", 10),
            "http.retry_delay_seconds",
            minimum=0,
        )

    def _signed_url(self) -> str:
        if not self.secret:
            return self.webhook
        timestamp = str(round(time.time() * 1000))
        digest = hmac.new(
            self.secret.encode("utf-8"),
            f"{timestamp}\n{self.secret}".encode("utf-8"),
            hashlib.sha256,
        ).digest()
        signature = urllib.parse.quote_plus(base64.b64encode(digest))
        separator = "&" if "?" in self.webhook else "?"
        return (
            f"{self.webhook}{separator}timestamp={timestamp}"
            f"&sign={signature}"
        )

    def send(self, notification: Notification) -> None:
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": notification.title,
                "text": notification.text,
            },
        }
        last_error: Exception | None = None

        for attempt in range(1, self.attempts + 1):
            try:
                response = requests.post(
                    self._signed_url(),
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                result = response.json()
                if result.get("errcode") != 0:
                    raise RuntimeError(f"钉钉返回错误：{result}")
                log("钉钉", f"发送成功：{notification.title}")
                return
            except (requests.RequestException, RuntimeError, ValueError) as exc:
                last_error = exc
                if attempt >= self.attempts:
                    break
                log(
                    "钉钉",
                    f"发送失败，第 {attempt}/{self.attempts} 次；"
                    f"{self.retry_delay} 秒后重试：{exc}",
                )
                time.sleep(self.retry_delay)

        raise RuntimeError(
            f"钉钉发送失败，已尝试 {self.attempts} 次：{last_error}"
        )
