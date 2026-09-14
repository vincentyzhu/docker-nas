# WUD

WUD 用于检测本机 Docker 容器的镜像更新。本模板默认通过钉钉自定义机器人发送中文批量通知，通知脚本也支持企业微信群机器人，并保留可选的 SMTP 邮件配置。

## 文件说明

- `docker-compose.yml`：WUD 服务、机器人 Command Trigger 和可选 SMTP 配置。
- `dingtalk-notify.sh`：将 WUD 的更新数据转换为钉钉或企业微信 Markdown 消息。为兼容现有 Compose 挂载，文件名保持不变。
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

## 通知配置

`dingtalk-notify.sh` 通过 `NOTIFY_CHANNEL` 选择钉钉或企业微信群机器人。一次脚本调用只会向一个机器人通道发送；SMTP 是 WUD 的独立触发器，启用后可与当前机器人通道同时通知。

`.env` 只用于 Compose 变量替换，模板会将两个机器人通道的相关变量传入 WUD 容器；未选中的通道可以留空。不要将真实 Webhook、密钥或邮箱授权码提交到仓库。

### 机器人通道选择

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `NOTIFY_CHANNEL` | `dingtalk` | `dingtalk` 使用钉钉机器人，`wecom` 使用企业微信群机器人；其他值会使脚本退出。 |

### 钉钉自定义机器人

| 变量 | 要求 | 说明 |
| --- | --- | --- |
| `DINGTALK_WEBHOOK` | 使用钉钉时必填 | 完整的 HTTPS Webhook 地址。 |
| `DINGTALK_SECRET` | 可选 | 机器人开启“加签”安全设置时填写；每次重试都会重新生成时间戳和签名。 |
| `DINGTALK_MAX_ATTEMPTS` | 默认 `3` | 总尝试次数，可用范围 `1-10`。 |
| `DINGTALK_RETRY_DELAY_SECONDS` | 默认 `5` | 重试间隔秒数，可用范围 `0-60`。 |

`.env` 示例：

```dotenv
NOTIFY_CHANNEL=dingtalk
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=请替换
DINGTALK_SECRET=请替换或留空
DINGTALK_MAX_ATTEMPTS=3
DINGTALK_RETRY_DELAY_SECONDS=5
```

### 企业微信群机器人

| 变量 | 要求 | 说明 |
| --- | --- | --- |
| `WECOM_WEBHOOK` | 使用企业微信时必填 | 完整的 HTTPS 群机器人 Webhook 地址；群机器人没有独立加签密钥变量。 |
| `WECOM_MAX_ATTEMPTS` | 默认 `3` | 总尝试次数，可用范围 `1-10`。 |
| `WECOM_RETRY_DELAY_SECONDS` | 默认 `5` | 重试间隔秒数，可用范围 `0-60`。 |

`.env` 示例：

```dotenv
NOTIFY_CHANNEL=wecom
WECOM_WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=请替换
WECOM_MAX_ATTEMPTS=3
WECOM_RETRY_DELAY_SECONDS=5
```

企业微信 Markdown 单条上限按 UTF-8 计算为 4096 字节，脚本会优先在换行处自动拆分，不会拆断中文字符。

### SMTP 邮件

SMTP 配置默认全部注释。需要邮件通知时，填写 `.env` 中的以下变量，再取消 Compose 内 SMTP 段落的注释。模板默认使用 QQ 邮箱 `smtp.qq.com:465` 和隐式 TLS；使用其他邮件服务时，同步修改 Compose 中的主机、端口和 TLS 设置。

| 变量 | 启用 SMTP 时 | 说明 |
| --- | --- | --- |
| `WUD_SMTP_USER` | 必填 | SMTP 登录用户名，QQ 邮箱通常填完整邮箱地址。 |
| `WUD_SMTP_PASS` | 必填 | SMTP 授权码或专用密码，不是 QQ 登录密码。 |
| `WUD_SMTP_FROM` | 必填 | 发件人地址。 |
| `WUD_SMTP_TO` | 必填 | 收件人地址。 |

```dotenv
WUD_SMTP_USER=sender@example.com
WUD_SMTP_PASS=请替换为SMTP授权码
WUD_SMTP_FROM=sender@example.com
WUD_SMTP_TO=receiver@example.com
```

## 管理员登录

WUD 9.x 强制登录。本模板通过 `.env` 中的以下变量配置管理员，两项均不能为空：

```dotenv
WUD_AUTH_ADMIN_USER=请替换为管理员用户名
WUD_AUTH_ADMIN_PASSWORD='请替换为强密码'
```

- `WUD_AUTH_ADMIN_PASSWORD` 填写实际登录密码，WUD 会自动使用 bcrypt 哈希后写入数据库。
- `.env` 中保留密码外层单引号，避免 `$` 被 Compose 插值。按官方当前限制，密码不要包含冒号 `:`。
- 登录后可在 `Configuration > Users` 管理用户和角色，在个人资料页管理密码和 API Token。管理员环境变量会在启动时参与账号初始化或更新，调整密码时应同步核对 `.env` 中的配置。
- `.env` 保存实际密码，应限制文件权限；校验使用 `docker compose config --quiet`，避免完整配置输出密码。

## 镜像更新策略

模板使用 `getwud/wud:9`，持续跟随 9.x 系列的小版本和补丁更新，不会自动跨越到 10.x。执行 `docker compose pull wud` 拉取更新，再执行 `docker compose up -d wud` 重建容器以应用更新；仅修改标签不会定时自动更新容器。更新前先停止 WUD，并备份完整 `store/` 和部署配置。

## 通知与排错

- 默认使用批量模式，一次扫描发现多个更新时合并成机器人消息。
- 脚本会同时校验 HTTP 状态和平台返回的 `errcode`，不会将 HTTP 200 的业务错误误判为成功。
- 网络超时、HTTP 429 和 5xx 默认最多尝试 3 次；Webhook、签名等配置错误不会重复发送。
- 日志只记录 Webhook 的主机和路径，不输出 access token、key 或签名查询参数。
- 查看运行日志：`docker compose logs -f wud`。
- 若机器人地址不可达，可先从 WUD 容器内测试 DNS 和 HTTPS；bridge 网络还需要确认 NAS/路由器存在正确的容器网段回程路由。

## 安全说明

`/var/run/docker.sock` 即使以只读方式挂载，仍可暴露较高的 Docker 主机权限。不要将 WUD 直接暴露到公网；如需远程访问，应通过受控反向代理并启用认证。
