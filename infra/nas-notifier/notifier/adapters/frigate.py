from __future__ import annotations

import json
import time
from typing import Any

import paho.mqtt.client as mqtt

from notifier.config import ConfigError, as_bool, as_int, required_text
from notifier.log import log
from notifier.models import Notification, NotificationSender
from notifier.policy import NotificationPolicy


DEFAULT_LABEL_NAMES = {
    "person": "人员",
    "car": "车辆",
    "dog": "狗",
    "cat": "猫",
    "bird": "鸟",
}

DEFAULT_LABEL_EMOJI = {
    "person": "🚶",
    "car": "🚗",
    "dog": "🐕",
    "cat": "🐈",
    "bird": "🐦",
}


class FrigateAdapter:
    mode = "event"

    def __init__(
        self,
        config: dict[str, Any],
        sender: NotificationSender,
        policy: NotificationPolicy | None = None,
    ) -> None:
        mqtt_config = config.get("mqtt") or {}
        if not isinstance(mqtt_config, dict):
            raise ConfigError("source.mqtt 必须是对象")

        self.host = required_text(
            mqtt_config.get("host"), "source.mqtt.host"
        )
        self.port = as_int(
            mqtt_config.get("port", 1883),
            "source.mqtt.port",
            minimum=1,
        )
        topic_prefix = str(mqtt_config.get("topic_prefix", "frigate")).strip("/")
        self.topic = str(
            mqtt_config.get("topic", f"{topic_prefix}/events")
        ).strip()
        self.username = str(mqtt_config.get("username", "")).strip()
        self.password = str(mqtt_config.get("password", ""))
        self.use_tls = as_bool(
            mqtt_config.get("tls", False),
            "source.mqtt.tls",
        )
        self.keepalive = as_int(
            mqtt_config.get("keepalive", 60),
            "source.mqtt.keepalive",
            minimum=1,
        )
        self.client_id = str(
            mqtt_config.get("client_id", "nas-notifier-frigate")
        ).strip()

        labels = config.get("watch_labels", ["person", "car", "dog", "cat"])
        if not isinstance(labels, list) or not all(isinstance(x, str) for x in labels):
            raise ConfigError("source.watch_labels 必须是字符串列表")
        self.watch_labels = {label.strip() for label in labels if label.strip()}

        cameras = config.get("watch_cameras", [])
        if not isinstance(cameras, list) or not all(
            isinstance(x, str) for x in cameras
        ):
            raise ConfigError("source.watch_cameras 必须是字符串列表")
        self.watch_cameras = {camera.strip() for camera in cameras if camera.strip()}

        event_types = config.get("event_types", ["new"])
        if not isinstance(event_types, list) or not all(
            isinstance(x, str) for x in event_types
        ):
            raise ConfigError("source.event_types 必须是字符串列表")
        self.event_types = {value.strip() for value in event_types if value.strip()}

        self.cooldown = as_int(
            config.get("cooldown_seconds", 0),
            "source.cooldown_seconds",
            minimum=0,
        )
        self.web_url = str(config.get("web_url", "")).rstrip("/")
        camera_names = config.get("camera_names", {}) or {}
        label_names = config.get("label_names", {}) or {}
        if not isinstance(camera_names, dict) or not isinstance(label_names, dict):
            raise ConfigError("source.camera_names 和 source.label_names 必须是对象")
        self.camera_names = camera_names
        self.label_names = {
            **DEFAULT_LABEL_NAMES,
            **label_names,
        }

        self.sender = sender
        self.policy = policy or NotificationPolicy()
        self.last_notify: dict[str, float] = {}

    def _display_camera(self, camera: str) -> str:
        return str(self.camera_names.get(camera, camera))

    def _display_label(self, label: str) -> str:
        return str(self.label_names.get(label, label.upper()))

    def _notification(
        self,
        camera: str,
        label: str,
        event_id: str,
        event_time: float | None,
    ) -> Notification:
        emoji = DEFAULT_LABEL_EMOJI.get(label, "📹")
        camera_text = self._display_camera(camera)
        label_text = self._display_label(label)
        timestamp = event_time or time.time()
        time_text = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
        lines = [
            f"## {emoji} Frigate 检测告警",
            "",
            f"- **摄像头**：{camera_text}",
            f"- **检测对象**：{label_text}",
            f"- **时间**：{time_text}",
            f"- **事件 ID**：`{event_id}`",
        ]
        if self.web_url:
            lines.extend(("", f"[👉 查看实时画面]({self.web_url})"))
        return Notification(f"{emoji} {label_text}检测", "\n".join(lines))

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        del userdata, flags, properties
        if reason_code == 0:
            client.subscribe(self.topic)
            log("Frigate", f"MQTT 已连接，订阅：{self.topic}")
        else:
            log("Frigate", f"MQTT 连接失败：{reason_code}")

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        disconnect_flags: mqtt.DisconnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        del client, userdata, disconnect_flags, properties
        log("Frigate", f"MQTT 已断开：{reason_code}，等待自动重连")

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        message: mqtt.MQTTMessage,
    ) -> None:
        del client, userdata
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            log("Frigate", "收到无法解析的 MQTT 消息，已忽略")
            return

        event_type = str(payload.get("type", ""))
        if event_type not in self.event_types:
            return
        after = payload.get("after") or {}
        if not isinstance(after, dict):
            return

        label = str(after.get("label", ""))
        camera = str(after.get("camera", ""))
        event_id = str(after.get("id", ""))
        if not label or not camera or not event_id:
            log("Frigate", "事件缺少 label、camera 或 id，已忽略")
            return
        if self.watch_labels and label not in self.watch_labels:
            return
        if self.watch_cameras and camera not in self.watch_cameras:
            return
        if not self.policy.allows():
            return

        if self.cooldown > 0:
            cooldown_key = f"{camera}:{label}"
            now = time.time()
            previous = self.last_notify.get(cooldown_key, 0)
            if now - previous < self.cooldown:
                log(
                    "Frigate",
                    f"冷却期内跳过：{camera} → {label}，事件 {event_id}",
                )
                return
            self.last_notify[cooldown_key] = now

        try:
            event_time = float(after.get("start_time"))
        except (TypeError, ValueError):
            event_time = None

        try:
            self.sender.send(
                self._notification(camera, label, event_id, event_time)
            )
            log(
                "Frigate",
                f"事件已推送：{self._display_camera(camera)} → "
                f"{self._display_label(label)}，事件 {event_id}",
            )
        except Exception as exc:  # noqa: BLE001
            log("Frigate", f"事件推送失败：{event_id}；{exc}")

    def run_forever(self) -> None:
        log(
            "通知服务",
            f"Frigate 实时事件模式；冷却时间={self.cooldown} 秒；启动不推送",
        )
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=self.client_id,
        )
        if self.username:
            client.username_pw_set(self.username, self.password)
        if self.use_tls:
            client.tls_set()
        client.reconnect_delay_set(min_delay=1, max_delay=30)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        client.connect_async(self.host, self.port, keepalive=self.keepalive)
        client.loop_forever(retry_first_connection=True)
