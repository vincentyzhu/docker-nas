# Nginx

NAS 服务统一 HTTP/HTTPS 入口，并通过 `nginx-logrotate` 轮转访问日志和错误日志。

部署步骤：

1. 将证书和私钥放入 `certs/`。
2. 复制 `conf.d/default.conf.example` 为新的 `.conf` 文件。
3. 修改域名、证书文件名和 `proxy_pass` 的宿主机端口。
4. 执行 `docker compose config` 后启动容器。
5. 在容器中执行 `nginx -t`，确认实际证书和站点配置有效。

默认 bridge 网络下，Nginx 使用 `host.docker.internal:<宿主机端口>` 访问其他服务。Compose 已通过 `host-gateway` 提供该地址。真实证书和 `.conf` 文件已被 Git 忽略，仓库只保存示例。

日志轮转由本 Compose 中的 `nginx-logrotate` 独占管理；部署前应确认宿主机没有另一套 logrotate 同时处理相同日志。
