import os
import time
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when the notifier configuration is missing or invalid."""


def as_dict(value: Any, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f"配置项 {name} 必须是对象")
    return value


def as_bool(value: Any, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ConfigError(f"配置项 {name} 必须是 true 或 false")


def as_int(value: Any, name: str, minimum: int | None = None) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"配置项 {name} 必须是整数") from exc
    if minimum is not None and result < minimum:
        raise ConfigError(f"配置项 {name} 不能小于 {minimum}")
    return result


def required_text(value: Any, name: str) -> str:
    result = str(value or "").strip()
    if not result or result.upper().startswith(("CHANGE-ME", "REDACTED")):
        raise ConfigError(f"请配置 {name}")
    return result


def load_config() -> dict[str, Any]:
    path = Path(os.getenv("CONFIG_FILE", "/config/config.yml"))
    if not path.is_file():
        raise ConfigError(f"配置文件不存在：{path}")

    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"读取配置文件失败：{exc}") from exc

    config = as_dict(loaded, "根节点")
    notifier = as_dict(config.get("notifier"), "notifier")
    notifier_type = str(notifier.get("type", "")).strip().lower()
    if notifier_type not in {"canventory", "homebox", "frigate"}:
        raise ConfigError(
            "notifier.type 必须是 canventory、homebox 或 frigate"
        )

    timezone = str(notifier.get("timezone", "Asia/Shanghai")).strip()
    if not timezone:
        raise ConfigError("notifier.timezone 不能为空")
    os.environ["TZ"] = timezone
    if hasattr(time, "tzset"):
        time.tzset()

    config["notifier"] = notifier
    config["dingtalk"] = as_dict(config.get("dingtalk"), "dingtalk")
    config["wecom"] = as_dict(config.get("wecom"), "wecom")
    config["http"] = as_dict(config.get("http"), "http")
    config["source"] = as_dict(config.get("source"), "source")
    config["schedule"] = as_dict(config.get("schedule"), "schedule")
    config["notification_policy"] = as_dict(
        config.get("notification_policy"),
        "notification_policy",
    )
    return config
