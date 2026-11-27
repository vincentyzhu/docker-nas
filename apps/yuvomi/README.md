# Yuvomi

Yuvomi 家庭日程、任务与协作模板，使用固定镜像 `ghcr.io/ulsklyc/yuvomi:2.96.0`。

## 部署

将本目录复制到一个部署目录，复制 `.env.example` 为 `.env` 后按需调整。默认从宿主机访问 `http://127.0.0.1:3000` 和 `/health`，首次访问时按页面提示创建管理员。

```bash
cp .env.example .env
docker compose config --quiet
docker compose up -d
docker compose ps
```

使用 HTTPS 反代时，`BASE_URL` 填浏览器访问的完整 HTTPS 地址，`SESSION_SECURE` 设为 `true`。单层反代将 `TRUST_PROXY` 设为 `1`，并传递 `Host`、`X-Forwarded-Proto` 和 `X-Forwarded-For`。宿主机 Nginx 的默认上游为 `http://127.0.0.1:3000`。使用 bridge 模式的 Nginx 时，将 `YUVOMI_BIND_IP` 改为反代可达的 NAS 局域网 IPv4，限制后端端口来源，并同步更新 Nginx 上游。

## 多实例

把同一份模板复制到不同的部署目录，并为每个实例准备自己的 `.env`。例如第一套使用 `yuvomi` 和 `3000`，第二套可以使用 `yuvomi-alt` 和另一个空闲端口。

```dotenv
COMPOSE_PROJECT_NAME=yuvomi-alt
YUVOMI_HOST_PORT=13000
BASE_URL=http://127.0.0.1:13000
```

分别在各自目录验证并启动。每套实例各自保存 `data`、`backups`、`modules` 和 `documents`。备份各实例的这些目录及 `.env`，保留 `data/.secrets` 中的自动生成密钥。若原实例通过环境变量定义 `SESSION_SECRET` 或 `DB_ENCRYPTION_KEY`，迁移时在新 `.env` 中恢复原值。

[Yuvomi v2.96.0 官方发布](https://github.com/ulsklyc/yuvomi/releases/tag/v2.96.0) · [官方部署文档](https://github.com/ulsklyc/yuvomi/blob/v2.96.0/docs/installation.md)
