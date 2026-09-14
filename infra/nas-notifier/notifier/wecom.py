import time
from typing import Any

import requests

from notifier.config import as_int, required_text
from notifier.log import log
from notifier.models import Notification


class WeComClient:
    max_markdown_bytes = 4096

    def __init__(self, config: dict[str, Any], http_config: dict[str, Any]) -> None:
        self.webhook = required_text(config.get("webhook"), "wecom.webhook")
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

    @classmethod
    def _markdown_chunks(cls, content: str) -> list[str]:
        """Split Markdown on line boundaries without breaking UTF-8 characters."""
        chunks: list[str] = []
        current = ""

        for line in content.splitlines(keepends=True):
            if len((current + line).encode("utf-8")) <= cls.max_markdown_bytes:
                current += line
                continue

            if current:
                chunks.append(current)
                current = ""

            for character in line:
                if len((current + character).encode("utf-8")) > cls.max_markdown_bytes:
                    chunks.append(current)
                    current = ""
                current += character

        if current or not chunks:
            chunks.append(current)
        return chunks

    def _redact(self, error: Exception) -> str:
        return str(error).replace(self.webhook, "<已隐藏Webhook>")

    def _send_chunk(self, content: str) -> None:
        payload = {
            "msgtype": "markdown",
            "markdown": {"content": content},
        }
        last_error: Exception | None = None

        for attempt in range(1, self.attempts + 1):
            try:
                response = requests.post(
                    self.webhook,
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                result = response.json()
                if result.get("errcode") != 0:
                    errcode = result.get("errcode", "未知")
                    errmsg = result.get("errmsg", "未知错误")
                    raise RuntimeError(
                        f"企业微信返回错误：errcode={errcode}，errmsg={errmsg}"
                    )
                return
            except (requests.RequestException, RuntimeError, ValueError) as exc:
                last_error = exc
                if attempt >= self.attempts:
                    break
                log(
                    "企业微信",
                    f"发送失败，第 {attempt}/{self.attempts} 次；"
                    f"{self.retry_delay} 秒后重试：{self._redact(exc)}",
                )
                time.sleep(self.retry_delay)

        if last_error is None:
            raise RuntimeError("企业微信发送失败：未知错误")
        raise RuntimeError(
            f"企业微信发送失败，已尝试 {self.attempts} 次："
            f"{self._redact(last_error)}"
        )

    def send(self, notification: Notification) -> None:
        chunks = self._markdown_chunks(notification.text)
        for chunk in chunks:
            self._send_chunk(chunk)
        suffix = f"，共 {len(chunks)} 条" if len(chunks) > 1 else ""
        log("企业微信", f"发送成功：{notification.title}{suffix}")
