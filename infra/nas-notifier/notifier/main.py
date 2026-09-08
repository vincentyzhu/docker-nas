import sys
from typing import Any

import requests

from notifier.config import ConfigError, as_bool, as_int, load_config
from notifier.dingtalk import DingTalkClient
from notifier.log import log
from notifier.schedule import run_daily


def build_adapter(
    notifier_type: str,
    source_config: dict[str, Any],
    timeout: int,
    dingtalk: DingTalkClient,
) -> Any:
    if notifier_type == "canventory":
        from notifier.adapters.canventory import CanventoryAdapter

        return CanventoryAdapter(source_config, timeout)
    if notifier_type == "homebox":
        from notifier.adapters.homebox import HomeboxAdapter

        return HomeboxAdapter(source_config, timeout)
    if notifier_type == "frigate":
        from notifier.adapters.frigate import FrigateAdapter

        return FrigateAdapter(source_config, dingtalk)
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
        dingtalk = DingTalkClient(config["dingtalk"], config["http"])
        adapter = build_adapter(
            notifier_type,
            config["source"],
            timeout,
            dingtalk,
        )
        log("通知服务", f"启动，类型={notifier_type}")

        if adapter.mode == "event":
            adapter.run_forever()
            return

        send_empty = as_bool(
            config["schedule"].get("send_empty", False),
            "schedule.send_empty",
        )

        def run_once() -> None:
            try:
                notification = adapter.collect(send_empty)
                if notification is not None:
                    dingtalk.send(notification)
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
