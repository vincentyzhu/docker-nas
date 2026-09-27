# Frigate

本目录组合部署 Frigate、Mosquitto 和通用钉钉通知容器。

部署前：

1. 修改 `config/config.yml` 中的摄像头、RTSP、硬件加速和检测配置。
2. 修改 `config/config.yml` 和 `notify/config.yml` 中的 MQTT 账号密码；同时填写通知配置中的 NAS 地址、网页域名、摄像头筛选和钉钉机器人信息。
3. 确认 `/dev/dri/renderD128` 存在；不使用 Intel 核显时应同步调整 `devices` 和 `privileged`。
4. 按下文在 `mqtt/data/passwd` 创建 MQTT 密码文件，并确认 `localtime`、`mqtt/config/mosquitto.conf`、数据目录和通知配置文件均存在。
5. 执行 `docker compose config` 后再启动。

模板使用默认 bridge 网络，因此通知容器通过 `NAS_IP:1883` 访问 Mosquitto，不使用容器名解析。Mosquitto 禁止匿名连接，1883 端口未加密，只能用于可信局域网，不应暴露到公网。

## MQTT 账号认证

在本目录执行以下命令，交互式设置 Frigate 和通知服务各自的密码。`-c` 只用于首次创建密码文件；如果 `mqtt/data/passwd` 已存在，第一条命令也应去掉 `-c`，以免覆盖其他账号。

```bash
docker compose run --rm --no-deps -u 0:0 --entrypoint mosquitto_passwd mosquitto -c /mosquitto/data/passwd frigate
docker compose run --rm --no-deps -u 0:0 --entrypoint mosquitto_passwd mosquitto /mosquitto/data/passwd notifier
docker compose run --rm --no-deps -u 0:0 --entrypoint chown mosquitto 1883:1883 /mosquitto/data/passwd
```

把两次设置的密码分别填入 `config/config.yml` 的 `mqtt.password` 和 `notify/config.yml` 的 `source.mqtt.password`。这两个文件在仓库中只保留占位符，实际密码仅填写在私有部署副本中；密码文件位于 Git 忽略的 `mqtt/data/` 目录。

修改后执行 `docker compose config -q`。新部署执行 `docker compose up -d`；已有部署执行 `docker compose up -d --no-deps --force-recreate mosquitto frigate notify`，然后检查三个服务的日志。匿名连接应被拒绝，Frigate 和通知服务应能正常连接 MQTT。

Frigate 核心服务不要添加 `init: true`。当前镜像在现有部署环境中启用 Docker init 会导致启动进程被接管、核心服务无法正常启动；Mosquitto 和通知容器不受此限制。

通知容器会把符合筛选条件的新事件发送到钉钉，内容包含事件文字和 Frigate 网页入口。
