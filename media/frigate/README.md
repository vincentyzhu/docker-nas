# Frigate

本目录组合部署 Frigate、Mosquitto 和通用钉钉通知容器。

部署前：

1. 修改 `config/config.yml` 中的摄像头、RTSP、硬件加速和检测配置。
2. 修改 `notify/config.yml` 中的 NAS 地址、网页域名、摄像头筛选和钉钉机器人信息。
3. 确认 `/dev/dri/renderD128` 存在；不使用 Intel 核显时应同步调整 `devices` 和 `privileged`。
4. 确认 `localtime`、`mqtt/config/mosquitto.conf`、数据目录和通知配置文件均存在。
5. 执行 `docker compose config` 后再启动。

模板使用默认 bridge 网络，因此通知容器通过 `NAS_IP:1883` 访问 Mosquitto，不使用容器名解析。当前 Mosquitto 允许匿名连接，1883 端口只能用于可信局域网，不应暴露到公网。

Frigate 核心服务不要添加 `init: true`。当前镜像在现有部署环境中启用 Docker init 会导致启动进程被接管、核心服务无法正常启动；Mosquitto 和通知容器不受此限制。

当前通知只发送事件文字和 Frigate 网页入口，不附带截图；MQTT 用户认证、ACL 和事件截图列为后续增强，不属于本次迭代。
