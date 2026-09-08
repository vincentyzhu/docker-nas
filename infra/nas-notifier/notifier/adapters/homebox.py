import urllib.parse
from datetime import date, datetime
from typing import Any

import requests

from notifier.config import as_int, required_text
from notifier.log import log
from notifier.models import Notification


class HomeboxAdapter:
    mode = "scheduled"
    page_size = 100

    def __init__(self, config: dict[str, Any], timeout: int) -> None:
        base_url = required_text(
            config.get("api_url"), "source.api_url"
        ).rstrip("/")
        self.api_url = base_url if base_url.endswith("/api") else f"{base_url}/api"
        self.web_url = str(config.get("web_url", base_url)).rstrip("/")
        self.api_key = required_text(
            config.get("api_key"), "source.api_key"
        )
        self.remind_days = as_int(
            config.get("remind_days", 30),
            "source.remind_days",
            minimum=0,
        )
        self.timeout = timeout

    def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = requests.get(
            f"{self.api_url}{path}",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
            },
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict):
            raise ValueError(f"Homebox 接口 {path} 没有返回对象")
        return result

    def _summaries(self) -> list[dict[str, Any]]:
        page = 1
        entities: list[dict[str, Any]] = []
        while True:
            result = self._get(
                "/v1/entities",
                params={"page": page, "pageSize": self.page_size},
            )
            items = result.get("items", [])
            if not isinstance(items, list):
                raise ValueError("Homebox 返回的 entities.items 不是列表")
            entities.extend(items)
            total = int(result.get("total", len(entities)))
            if not items or len(entities) >= total:
                return entities
            page += 1

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                parsed = date.fromisoformat(text[:10])
            except ValueError:
                log("Homebox", f"无法识别质保日期，已跳过：{text}")
                return None
        return None if parsed.year <= 1 else parsed

    @staticmethod
    def _is_location(summary: dict[str, Any]) -> bool:
        entity_type = summary.get("entityType") or {}
        return bool(entity_type.get("isLocation"))

    def _warranties(self) -> list[dict[str, Any]]:
        today = date.today()
        alerts: list[dict[str, Any]] = []
        for summary in self._summaries():
            if summary.get("archived") or self._is_location(summary):
                continue
            entity_id = summary.get("id")
            if not entity_id:
                continue
            encoded_id = urllib.parse.quote(str(entity_id), safe="")
            entity = self._get(f"/v1/entities/{encoded_id}")
            if entity.get("archived") or entity.get("lifetimeWarranty"):
                continue
            expires = self._parse_date(entity.get("warrantyExpires"))
            if expires is None:
                continue
            days = (expires - today).days
            # 已过保物品不再提醒，只保留今天和未来提醒窗口内到期的物品。
            if days < 0 or days > self.remind_days:
                continue
            parent = entity.get("parent") or {}
            alerts.append(
                {
                    "name": entity.get("name") or summary.get("name") or "未命名物品",
                    "expires": expires,
                    "days": days,
                    "location": parent.get("name", ""),
                }
            )
        return sorted(alerts, key=lambda item: (item["days"], item["name"]))

    @staticmethod
    def _safe(value: Any) -> str:
        return str(value).replace("[", "［").replace("]", "］")

    def _line(self, item: dict[str, Any], show_days: bool = False) -> str:
        name = self._safe(item["name"])
        location = self._safe(item.get("location", ""))
        location_text = f"，位置：{location}" if location else ""
        days_text = f"还有 {item['days']} 天，" if show_days else ""
        return (
            f"- {name}（{days_text}质保至 "
            f"{item['expires'].isoformat()}{location_text}）"
        )

    def collect(self, send_empty: bool) -> Notification | None:
        alerts = self._warranties()
        if not alerts and not send_empty:
            log("Homebox", "无符合条件的质保提醒，跳过推送")
            return None

        due_today = [item for item in alerts if item["days"] == 0]
        upcoming = [item for item in alerts if item["days"] > 0]
        lines = ["## 🧰 Homebox 质保到期提醒", ""]
        for items, title, show_days in (
            (due_today, "### ⚠️ 今天到期", False),
            (upcoming, f"### 📋 {self.remind_days} 天内到期", True),
        ):
            if not items:
                continue
            lines.append(f"{title}（{len(items)} 件）")
            lines.extend(self._line(item, show_days) for item in items)
            lines.append("")

        if not alerts:
            lines.extend(
                (f"当前没有今天或未来 {self.remind_days} 天内到期的物品。", "")
            )
        lines.extend(("---", f"[打开 Homebox 查看]({self.web_url})"))
        log("Homebox", f"检查完成，符合条件 {len(alerts)} 件")
        return Notification("Homebox 质保到期提醒", "\n".join(lines))
