# Mirobody

Mirobody 健康数据管理与分析模板。包含 Mirobody `1.6.2`、后台 worker 和带 pgvector 的 PostgreSQL 17。镜像用于 Linux 容器。

## 部署

1. 将本目录复制到 NAS 或 Linux 主机上的独立项目目录，并在本机存储上创建 `data/postgres` 和 `data/upload`。
2. 将 `.env.example` 复制为 `.env`，为六项必填变量分别生成随机值。`DATABASE_DECRYPTION_KEY` 可用 `openssl rand -hex 16` 生成，其余每项可分别运行一次 `openssl rand -hex 32`。已有部署迁移时沿用原有密码和密钥。
3. 在项目目录运行下面的命令。使用 NAS 图形界面时，选取本目录为工作目录，导入 `docker-compose.yml` 和同目录的 `.env`。

```bash
mkdir -p data/postgres data/upload
docker compose config --quiet
docker compose up -d
docker compose ps -a
```

默认从宿主机访问 `http://127.0.0.1:18060/api/health`。确认 Web 和 PostgreSQL 健康、`mirobody_init` 以状态码 0 退出、`mirobody_worker` 保持运行。

## HTTPS 和备份

- 宿主机上的 Nginx 使用上游 `http://127.0.0.1:18060`。如果 Nginx 使用 bridge 网络，将 `MIROBODY_BIND_IP` 改为反代可达的 NAS 局域网 IPv4，并让 Nginx 使用相同的地址和端口。调整宿主机端口时同步修改上游。通过 HTTPS 使用应用，并按实际情况设置 `FORWARDED_ALLOW_IPS` 和 `MCP_PUBLIC_URL`。
- 首次配置模型时，通过 HTTPS 访问 `/setup?token=<SETUP_TOKEN>`。如接入云端模型，先确认参与分析的数据符合你的隐私要求。
- 备份 `data/postgres`、`data/upload`、`config.prod.yaml` 和 `.env`。数据库使用一致性备份，或在停止项目后备份目录。

[Mirobody 1.6.2 官方发布](https://github.com/thetahealth/mirobody/releases/tag/1.6.2) · [官方部署文档](https://docs.mirobody.ai/en/deployment/production)
