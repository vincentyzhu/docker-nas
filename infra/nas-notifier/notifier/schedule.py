import time
from datetime import datetime, timedelta
from typing import Any, Callable

from notifier.config import ConfigError, as_bool
from notifier.log import log


def parse_notify_time(value: Any) -> tuple[int, int]:
    try:
        parsed = datetime.strptime(str(value), "%H:%M")
    except ValueError as exc:
        raise ConfigError(
            "schedule.notify_time 必须为 24 小时制 HH:MM，例如 08:00"
        ) from exc
    return parsed.hour, parsed.minute


def next_scheduled_run(
    hour: int,
    minute: int,
    now: datetime | None = None,
) -> datetime:
    current = now or datetime.now()
    scheduled = current.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )
    if scheduled <= current:
        scheduled += timedelta(days=1)
    return scheduled


def run_daily(config: dict[str, Any], run_once: Callable[[], None]) -> None:
    notify_time = str(config.get("notify_time", "08:00"))
    hour, minute = parse_notify_time(notify_time)
    run_on_start = as_bool(
        config.get("run_on_start", False),
        "schedule.run_on_start",
    )

    log(
        "通知服务",
        f"定时模式，每天 {notify_time} 检查；"
        f"启动推送={'开启' if run_on_start else '关闭'}",
    )
    if run_on_start:
        run_once()

    while True:
        scheduled = next_scheduled_run(hour, minute)
        wait_seconds = max(1, (scheduled - datetime.now()).total_seconds())
        log("通知服务", f"下次检查：{scheduled:%Y-%m-%d %H:%M:%S}")
        time.sleep(wait_seconds)
        run_once()
