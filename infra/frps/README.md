# FRPS

公网服务器上的 FRP 服务端模板，使用 Docker Hub 的 `fatedier/frps:v0.71.0` 镜像和 host 网络监听 `6111`，管理面板仅监听 `127.0.0.1:6001`。

部署步骤：

1. 复制 `.env.example` 为 `.env`，填写 Token 和面板账号密码。
2. 按需设置 `frps.toml` 中的 `allowPorts`，只开放实际使用的远程端口。
3. 保证 `FRPS_TOKEN` 与 FRPC 使用的 `FRP_TOKEN` 完全一致。
4. 执行 `docker compose config` 检查变量，再执行 `docker compose up -d`。

不要把 `.env` 提交到仓库。管理面板默认只允许本机访问，如需公网访问，应通过 HTTPS 反向代理并限制访问来源。

升级时应将 FRPS 和 FRPC 调整到同一版本，并先核对该版本的配置变更。
