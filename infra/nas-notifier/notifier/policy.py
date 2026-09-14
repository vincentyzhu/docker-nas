from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Any

from chinese_calendar import is_workday

from notifier.config import ConfigError, as_bool, as_dict


CALENDARS = {"every_day", "weekdays", "china_workdays"}


def parse_clock_time(value: Any, name: str) -> time:
    text = str(value).strip()
    try:
        return datetime.strptime(text, "%H:%M").time()
    except ValueError as exc:
        raise ConfigError(f"{name} 必须为 24 小时制 HH:MM，例如 09:00") from exc


@dataclass(frozen=True)
class TimeRange:
    start: time
    end: time

    def contains(self, value: time) -> bool:
        if self.start == self.end:
            return True
        if self.start < self.end:
            return self.start <= value < self.end
        return value >= self.start or value < self.end

    def describe(self) -> str:
        return f"{self.start:%H:%M}-{self.end:%H:%M}"


class NotificationPolicy:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        policy = as_dict(config, "notification_policy")
        self.enabled = as_bool(
            policy.get("enabled", False),
            "notification_policy.enabled",
        )
        self.calendar = str(policy.get("calendar", "every_day")).strip().lower()
        if self.calendar not in CALENDARS:
            choices = "、".join(sorted(CALENDARS))
            raise ConfigError(f"notification_policy.calendar 必须是 {choices}")

        ranges = policy.get("time_ranges", [])
        if not isinstance(ranges, list):
            raise ConfigError("notification_policy.time_ranges 必须是列表")

        parsed_ranges: list[TimeRange] = []
        for index, value in enumerate(ranges):
            item = as_dict(value, f"notification_policy.time_ranges[{index}]")
            parsed_ranges.append(
                TimeRange(
                    parse_clock_time(
                        item.get("start"),
                        f"notification_policy.time_ranges[{index}].start",
                    ),
                    parse_clock_time(
                        item.get("end"),
                        f"notification_policy.time_ranges[{index}].end",
                    ),
                )
            )
        self.time_ranges = tuple(parsed_ranges)

        if self.enabled and self.calendar == "china_workdays":
            try:
                is_workday(datetime.now().date())
            except NotImplementedError as exc:
                raise ConfigError(
                    "中国法定工作日日历不支持当前年份，请更新 chinesecalendar"
                ) from exc

    def allows(self, now: datetime | None = None) -> bool:
        if not self.enabled:
            return True

        current = now or datetime.now()
        if self.calendar == "weekdays" and current.weekday() >= 5:
            return False
        if self.calendar == "china_workdays" and not is_workday(current.date()):
            return False

        if not self.time_ranges:
            return True
        return any(item.contains(current.time()) for item in self.time_ranges)

    def validate_scheduled_time(self, value: Any) -> None:
        if not self.enabled or not self.time_ranges:
            return
        scheduled = parse_clock_time(value, "schedule.notify_time")
        if not any(item.contains(scheduled) for item in self.time_ranges):
            raise ConfigError(
                "schedule.notify_time 不在 notification_policy.time_ranges 内"
            )

    def describe(self) -> str:
        if not self.enabled:
            return "未启用"
        calendar_names = {
            "every_day": "每天",
            "weekdays": "周一至周五",
            "china_workdays": "中国法定工作日",
        }
        ranges = "、".join(item.describe() for item in self.time_ranges) or "全天"
        return f"{calendar_names[self.calendar]} {ranges}"
