# FRPC

NAS 上的 FRP 客户端模板，使用 Docker Hub 的 `fatedier/frpc:v0.71.0` 镜像和 host 网络直接访问宿主机已发布的服务端口。

部署步骤：

1. 复制 `.env.example` 为 `.env`，填写公网 FRPS 地址和 Token。
2. 在 `frpc.toml` 中为需要穿透的服务添加 `[[proxies]]` 段。
3. 确认远程端口位于 FRPS 的 `allowPorts` 范围内。
4. 执行 `docker compose config`，确认无缺失变量后再启动。

同一个远程端口只能由一个代理占用。新增或调整端口时，应同步检查 NAS 端口表、FRPS 放行范围、公网防火墙和 Nginx 上游。

升级时应将 FRPC 和 FRPS 调整到同一版本，并先核对该版本的配置变更。
