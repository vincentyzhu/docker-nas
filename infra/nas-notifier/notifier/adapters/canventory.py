import os
from decimal import Decimal, InvalidOperation
from typing import Any

import requests

from notifier.config import as_int, required_text
from notifier.log import log
from notifier.models import Notification


class CanventoryAdapter:
    mode = "scheduled"

    def __init__(self, config: dict[str, Any], timeout: int) -> None:
        self.api_url = required_text(
            config.get("api_url"), "source.api_url"
        ).rstrip("/")
        self.web_url = str(config.get("web_url", self.api_url)).rstrip("/")
        self.username = required_text(
            config.get("username"), "source.username"
        )
        self.password = required_text(
            os.getenv("CANVENTORY_PASSWORD", config.get("password")),
            "CANVENTORY_PASSWORD 或 source.password",
        )
        self.home_id = None
        if "home_id" in config:
            self.home_id = as_int(config["home_id"], "source.home_id", minimum=1)
        self.timeout = timeout

    def _token(self) -> str:
        response = requests.post(
            f"{self.api_url}/api/auth/token",
            data={"username": self.username, "password": self.password},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return str(response.json()["access_token"])

    def _alerts(self, token: str) -> dict[str, Any]:
        response = requests.get(
            f"{self.api_url}/api/items/alerts",
            headers={"Authorization": f"Bearer {token}"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict):
            raise ValueError("Canventory 提醒接口没有返回对象")
        return result

    def _check_home(self, token: str) -> str:
        response = requests.get(
            f"{self.api_url}/api/homes/mine",
            headers={"Authorization": f"Bearer {token}"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        homes = response.json()
        if (
            not isinstance(homes, list)
            or len(homes) != 1
            or not isinstance(homes[0], dict)
            or homes[0].get("id") != self.home_id
        ):
            raise RuntimeError("通知账号必须仅属于配置的家庭，已跳过推送")
        return str(homes[0].get("name") or f"家庭 {self.home_id}")

    @staticmethod
    def _quantity(item: dict[str, Any]) -> str:
        raw = item.get("quantity", 0)
        try:
            value = Decimal(str(raw))
            number = format(value.normalize(), "f")
        except (InvalidOperation, ValueError):
            number = str(raw)
        unit = str(item.get("quantity_unit", "")).strip()
        return f"{number}{unit}" if unit else number

    @staticmethod
    def _date(value: Any) -> str:
        return str(value or "")[:10]

    def collect(self, send_empty: bool) -> Notification | None:
        token = self._token()
        home_name = self._check_home(token) if self.home_id is not None else None
        alerts = self._alerts(token)
        expired = alerts.get("expired_items", []) or []
        critical = alerts.get("critical_items", []) or []
        warning = alerts.get("warning_items", []) or []
        total = len(expired) + len(critical) + len(warning)

        if total == 0 and not send_empty:
            log("Canventory", "无临期或过期物品，跳过推送")
            return None

        title = f"{home_name} · 冰箱库存到期提醒" if home_name else "冰箱库存到期提醒"
        lines = [f"## 🥫 {title}", ""]
        sections = (
            (
                expired,
                "### 🚨 已过期",
                lambda item: f"过期于 {self._date(item.get('expiration_date'))}",
            ),
            (
                critical,
                "### ⚠️ 3 天内到期",
                lambda item: f"{item.get('days_until_expiration', '')} 天后到期",
            ),
            (
                warning,
                "### 📋 7 天内到期",
                lambda item: f"{item.get('days_until_expiration', '')} 天后到期",
            ),
        )
        for items, heading, date_text in sections:
            if not items:
                continue
            lines.append(f"{heading}（{len(items)} 件）")
            for item in items:
                category = str(item.get("category", "")).strip()
                category_text = f"，{category}" if category else ""
                lines.append(
                    f"- {item.get('item_name', '未命名物品')} "
                    f"×{self._quantity(item)}"
                    f"（{date_text(item)}{category_text}）"
                )
            lines.append("")

        if total == 0:
            lines.extend(("当前没有临期或过期物品。", ""))
        plain_lines = [line.removeprefix("## ").removeprefix("### ") for line in lines]
        plain_lines.append(f"打开 Canventory 查看：{self.web_url}")
        lines.extend(("---", f"[打开 Canventory 查看]({self.web_url})"))
        log("Canventory", f"检查完成，符合条件 {total} 件")
        return Notification(title, "\n".join(lines), "\n".join(plain_lines))
