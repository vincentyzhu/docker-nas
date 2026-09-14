import sys
from typing import Any

import requests

from notifier.config import ConfigError, as_bool, as_int, load_config
from notifier.dingtalk import DingTalkClient
from notifier.log import log
from notifier.models import NotificationSender
from notifier.policy import NotificationPolicy
from notifier.schedule import run_daily
from notifier.wecom import WeComClient


def build_sender(config: dict[str, Any]) -> tuple[str, NotificationSender]:
    channel = (
        str(config["notifier"].get("channel", "dingtalk")).strip().lower()
    )
    if channel == "dingtalk":
        return channel, DingTalkClient(config["dingtalk"], config["http"])
    if channel == "wecom":
        return channel, WeComClient(config["wecom"], config["http"])
    raise ConfigError("notifier.channel 必须是 dingtalk 或 wecom")


def build_adapter(
    notifier_type: str,
    source_config: dict[str, Any],
    timeout: int,
    sender: NotificationSender,
    policy: NotificationPolicy | None = None,
) -> Any:
    if notifier_type == "canventory":
        from notifier.adapters.canventory import CanventoryAdapter

        return CanventoryAdapter(source_config, timeout)
    if notifier_type == "homebox":
        from notifier.adapters.homebox import HomeboxAdapter

        return HomeboxAdapter(source_config, timeout)
    if notifier_type == "frigate":
        from notifier.adapters.frigate import FrigateAdapter

        return FrigateAdapter(source_config, sender, policy)
    raise ConfigError(f"不支持的通知类型：{notifier_type}")


def main() -> None:
    try:
        config = load_config()
        notifier_type = str(config["notifier"]["type"]).lower()
        timeout = as_int(
            config["http"].get("timeout_seconds", 20),
            "http.timeout_seconds",
            minimum=1,
        )
        channel, sender = build_sender(config)
        policy = NotificationPolicy(config["notification_policy"])
        adapter = build_adapter(
            notifier_type,
            config["source"],
            timeout,
            sender,
            policy,
        )
        log(
            "通知服务",
            f"启动，类型={notifier_type}，通道={channel}，"
            f"通知策略={policy.describe()}",
        )

        if adapter.mode == "event":
            adapter.run_forever()
            return

        send_empty = as_bool(
            config["schedule"].get("send_empty", False),
            "schedule.send_empty",
        )
        notify_time = config["schedule"].get("notify_time", "08:00")
        policy.validate_scheduled_time(notify_time)

        def run_once() -> None:
            if not policy.allows():
                log("通知策略", "当前不在允许通知日期或时段，跳过本次检查")
                return
            try:
                notification = adapter.collect(send_empty)
                if notification is not None:
                    sender.send(notification)
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else "未知"
                body = exc.response.text[:300] if exc.response is not None else str(exc)
                log(notifier_type, f"HTTP 错误 {status}：{body}")
            except Exception as exc:  # noqa: BLE001
                log(notifier_type, f"检查失败：{exc}")

        run_daily(config["schedule"], run_once)
    except ConfigError as exc:
        log("配置错误", str(exc))
        sys.exit(2)
    except KeyboardInterrupt:
        log("通知服务", "收到停止信号，正在退出")


if __name__ == "__main__":
    main()
