# ============================================================
# Frigate 事件通知脚本
# 监听 Frigate MQTT 事件，通过钉钉机器人发送告警
#
# 部署说明:
#   - 本脚本与 frigate/mosquitto 在同一 compose 内运行
#   - 通过容器名直接通信，无需暴露端口到宿主机
#   - 环境变量通过 docker-compose.yml 注入
#
# 依赖: paho-mqtt, requests（见 requirements.txt）
# ============================================================

import base64
import hashlib
import hmac
import json
import time
import urllib.parse
import requests
import paho.mqtt.client as mqtt
import os

# ========== 配置（通过 docker-compose 环境变量注入） ==========
# 同一 compose 内 mosquitto 容器名，无需修改
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
# mosquitto 内部端口 1883
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "frigate/events")

# 钉钉机器人 Webhook — 替换为实际地址
DINGTALK_WEBHOOK = os.getenv("DINGTALK_WEBHOOK", "")
# 钉钉机器人加签密钥 — 替换为实际值（机器人未设置加签则留空）
DINGTALK_SECRET = os.getenv("DINGTALK_SECRET", "")

# Frigate API 地址 — 同一 compose 内用容器名
FRIGATE_URL = os.getenv("FRIGATE_URL", "http://frigate:5000")

# 关注的对象类型
WATCH_LABELS = {"person", "car", "dog", "cat"}

# 冷却时间（秒），同类型事件不重复发送
COOLDOWN = 30
# ==============================================

last_notify: dict[str, float] = {}


def dingtalk_sign(secret: str) -> str:
    """钉钉加签：返回 &timestamp=xxx&sign=xxx"""
    timestamp = str(round(time.time() * 1000))
    sign = hmac.new(
        secret.encode(), f"{timestamp}\n{secret}".encode(), hashlib.sha256
    ).digest()
    sign_b64 = base64.b64encode(sign)
    sign_encoded = urllib.parse.quote_plus(sign_b64)
    return f"&timestamp={timestamp}&sign={sign_encoded}"


def build_dingtalk_markdown(camera: str, label: str, event_id: str) -> str:
    """构建钉钉 Markdown 消息"""
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    emoji_map = {"person": "🚶", "car": "🚗", "dog": "🐕", "cat": "🐈", "bird": "🐦"}
    emoji = emoji_map.get(label, "📹")

    return json.dumps(
        {
            "msgtype": "markdown",
            "markdown": {
                "title": f"{emoji} {label.upper()} 检测",
                "text": (
                    f"## {emoji} Frigate 检测告警\n\n"
                    f"- **摄像头**: {camera}\n"
                    f"- **检测对象**: {label.upper()}\n"
                    f"- **时间**: {now}\n"
                    f"- **事件ID**: `{event_id}`\n\n"
                    f"[👉 查看实时画面]({FRIGATE_URL})"
                ),
            },
        },
        ensure_ascii=False,
    )


def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print(f"[MQTT] 已连接到 {MQTT_HOST}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC)
        print(f"[MQTT] 已订阅: {MQTT_TOPIC}")
    else:
        print(f"[MQTT] 连接失败: {reason_code}")


def on_disconnect(client, userdata, flags, reason_code, properties=None):
    print(f"[MQTT] 断开连接: {reason_code}，将自动重连")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
    except json.JSONDecodeError:
        return

    event_type = payload.get("type", "")
    if event_type != "new":
        return

    after = payload.get("after", {})
    label = after.get("label", "")
    camera = after.get("camera", "")
    event_id = after.get("id", "")

    # 只关注指定类型
    if label not in WATCH_LABELS:
        return

    # 冷却检查
    cooldown_key = f"{camera}:{label}"
    now = time.time()
    if cooldown_key in last_notify and now - last_notify[cooldown_key] < COOLDOWN:
        return
    last_notify[cooldown_key] = now

    # 构建带签名的 URL
    url = DINGTALK_WEBHOOK
    if DINGTALK_SECRET:
        url += dingtalk_sign(DINGTALK_SECRET)

    # 发送钉钉通知
    markdown = build_dingtalk_markdown(camera, label, event_id)
    try:
        resp = requests.post(
            url,
            data=markdown.encode(),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        result = resp.json()
        if result.get("errcode") == 0:
            print(f"[钉钉] 已发送: {camera} → {label}")
        else:
            print(f"[钉钉] 发送失败: {result}")
    except Exception as e:
        print(f"[钉钉] 请求异常: {e}")


def main():
    print("[通知服务] 启动中...")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # 自动重连
    client.connect_async(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    main()
