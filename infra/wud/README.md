# WUD

WUD 用于检测本机 Docker 容器的镜像更新。本模板默认通过钉钉自定义机器人发送中文批量通知，并保留可选的 SMTP 邮件配置。

## 文件说明

- `docker-compose.yml`：WUD 服务、钉钉 Command Trigger 和可选 SMTP 配置。
- `dingtalk-notify.sh`：将 WUD 的更新数据转换为钉钉 Markdown 消息。
- `.env.example`：公开占位配置；复制后的 `.env` 不会被 Git 跟踪。
- `store/`：WUD 运行数据目录，不应提交到仓库。

## 部署

```bash
cp .env.example .env
vim .env
docker compose config
docker compose up -d
```

模板端口为 `3000:3000`。复制到 NAS 后如需使用其他宿主机端口，只修改冒号左侧，例如 `6141:3000`。

`WUD_BASIC_HASH` 应填写 htpasswd 格式的密码哈希。由于哈希通常包含 `$`，请在 `.env` 中保留单引号，例如：

```dotenv
WUD_BASIC_HASH='$apr1$example$replace-with-real-hash'
```

## 镜像升级策略

模板使用 `getwud/wud:8`：会获得 8.x 系列的小版本和安全修复，但不会自动跨越到可能不兼容的 9.x。更新前建议备份 `store/`，然后执行：

```bash
docker compose pull
docker compose up -d
```

准备升级大版本时，应先阅读 WUD 的迁移说明，并重点复测 Command Trigger、Basic Auth 和环境变量名称。

## 通知与排错

- 默认使用批量模式，一次扫描发现多个更新时合并成一条钉钉消息。
- 脚本会核对 HTTP 状态和钉钉返回的 `errcode`，不再把 HTTP 200 的业务错误误判为成功。
- 网络超时、HTTP 429 和 5xx 默认最多尝试 3 次；Webhook、签名等配置错误不会重复发送。
- 查看运行日志：`docker compose logs -f wud`。
- 若钉钉不可达，可先从 WUD 容器内测试 DNS 和 HTTPS；bridge 网络还需要确认 NAS/路由器存在正确的容器网段回程路由。

## 可选 SMTP

SMTP 配置默认全部注释。需要邮件通知时，填写 `.env` 中的 `WUD_SMTP_*`，再取消 Compose 内 SMTP 段落的注释。钉钉与 SMTP 可以同时启用。

## 安全说明

`/var/run/docker.sock` 即使以只读方式挂载，仍可暴露较高的 Docker 主机权限。不要将 WUD 直接暴露到公网；如需远程访问，应通过受控反向代理并启用认证。
