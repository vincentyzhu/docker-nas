# Mihomo 与 MetaCubeXD

Mihomo 提供代理核心和 API，MetaCubeXD 提供 Web 管理界面。

部署步骤：

1. 将 Mihomo 配置文件放入 `config/`。
2. 把 Compose 中 `DEFAULT_BACKEND_URL` 的 `NAS_IP` 替换为 NAS 局域网 IP。
3. 启动后访问 MetaCubeXD 的 80 端口，并确认可以连接 `http://NAS_IP:9090`。

本模板明确使用默认 bridge 网络。默认 bridge 不解析其他容器名，因此不要把后端地址写成 `http://mihomo:9090`。如果以后改用用户自定义网络，才可以使用 Compose 服务名进行内部访问。
