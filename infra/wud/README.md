# WUD

WUD 用于检测本机 Docker 容器的镜像更新。本模板默认通过钉钉自定义机器人发送中文批量通知，并保留可选的 SMTP 邮件配置。

## 文件说明

- `docker-compose.yml`：WUD 服务、钉钉 Command Trigger 和可选 SMTP 配置。
- `dingtalk-notify.sh`：将 WUD 的更新数据转换为钉钉 Markdown 消息。
- `.env.example`：公开占位配置；复制后的 `.env` 不会被 Git 跟踪。
- `store/`：WUD 运行数据目录，9.x 默认使用 `wud.sqlite`，不应提交到仓库。

## 部署

```bash
cp .env.example .env
chmod 600 .env
vim .env
docker compose config --quiet
docker compose up -d
```

模板端口为 `3000:3000`。复制到 NAS 后如需使用其他宿主机端口，只修改冒号左侧，例如 `6141:3000`。

### 管理员登录

WUD 9.x 强制登录。本模板通过 `.env` 中的以下变量配置管理员，两项均不能为空：

```dotenv
WUD_AUTH_ADMIN_USER=请替换为管理员用户名
WUD_AUTH_ADMIN_PASSWORD='请替换为强密码'
```

- `WUD_AUTH_ADMIN_PASSWORD` 填写实际登录密码，WUD 会自动使用 bcrypt 哈希后写入数据库。不要把旧的 `WUD_BASIC_HASH` 直接填入此项。
- `.env` 中保留密码外层单引号，避免 `$` 被 Compose 插值。按官方当前限制，密码不要包含冒号 `:`。
- 登录后可在 `Configuration > Users` 管理用户和角色，在个人资料页管理密码和 API Token。管理员环境变量会在启动时参与账号初始化或更新，调整密码时应同步核对 `.env` 中的配置。
- `.env` 保存实际密码，应限制文件权限；校验使用 `docker compose config --quiet`，避免完整配置输出密码。

## 镜像升级策略

模板使用 `getwud/wud:9`，持续跟随 9.x 系列的小版本和补丁更新，不会自动跨越到 10.x。执行 `docker compose pull wud` 拉取更新，再执行 `docker compose up -d wud` 重建容器以应用更新；仅修改标签不会定时自动更新容器。升级前先停止 WUD，并备份完整 `store/` 和部署配置。

### 从 8.4.0 升级

以下操作在 NAS 的现有 WUD Compose 目录执行。先使用旧配置停止服务并备份，成功后再替换文件；备份目录放在当前目录的同级位置：

```bash
docker compose stop wud
wud_backup="../wud-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -m 700 "$wud_backup"
cp -a docker-compose.yml .env dingtalk-notify.sh store "$wud_backup/"
```

备份完成后，复制新版 `docker-compose.yml`，保留 NAS 自定义的宿主机端口、挂载路径及其他部署设置。用 `vim .env` 编辑现有环境文件，不要用 `.env.example` 覆盖已有钉钉或 SMTP 凭据：

1. 将 `WUD_BASIC_USER` 改为 `WUD_AUTH_ADMIN_USER`，可保留原用户名。
2. 删除 `WUD_BASIC_HASH`，新增 `WUD_AUTH_ADMIN_PASSWORD`，填写原来的实际登录密码或新密码；不知道原密码时设置新密码，不能从哈希恢复密码。
3. 新 Compose 已移除 `WUD_AUTH_BASIC_VINCENT_USER/HASH`，改为引用新的管理员变量。保留 `./store:/store`，确保该目录可写。

```bash
docker compose config --quiet
docker compose pull wud
docker compose up -d wud
docker compose logs --tail=100 wud
```

首次启动会自动将旧 `wud.json` 中的容器、历史和应用状态迁移到 `wud.sqlite`，并将旧文件改名为 `wud.json.migrated`。不要删除旧数据后再升级。

启动后检查管理员登录、容器列表、历史记录、手动扫描及钉钉通知；启用了 SMTP 时也验证邮件发送。外部脚本如调用 WUD REST API，还需核对认证和错误解析：错误详情改为 `message` 字段，可使用个人 API Token 访问接口。

### 回退到 8.4.0

先停止 WUD，将当前 `store/` 改名保留以便排错，再从升级前的备份恢复完整 `store/`、旧 Compose、`.env` 和通知脚本。将旧 Compose 镜像明确设为 `getwud/wud:8.4.0`，校验配置后重新启动。不要只改回镜像并继续使用迁移后的数据目录。

官方参考：[9.x 更新说明](https://getwud.app/docs/changelog/v9/)、[管理员认证](https://getwud.app/docs/configuration/authentications/basic/)、[存储迁移](https://getwud.app/docs/configuration/storage/)。

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
