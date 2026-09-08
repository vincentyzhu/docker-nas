# NAS Notifier

一个可复用的 Docker 通知容器。目前用同一镜像支持：

- Canventory 食品临期/过期提醒
- Homebox 即将过保提醒（不包含已经过保的物品）
- Frigate MQTT 实时事件提醒

通知统一发送到钉钉自定义机器人，保留中文日志、定时执行、启动推送开关、空结果推送开关和失败重试。真实账号、API Key、Webhook 均放在外部 YAML 配置中，不写入镜像。

## 部署方式

公开服务模板默认在线拉取 GHCR 镜像：

```yaml
image: ghcr.io/vincentyzhu/nas-notifier:latest
```

无法访问 GHCR 的 NAS 可以在有 Docker 的电脑构建并导出镜像，然后将服务模板中的镜像改为：

```yaml
image: nas-notifier:local
```

两种方式使用相同的 YAML 配置文件，不要同时运行在线版和离线版容器，否则会重复推送。

## 工作方式

一个容器实例只运行一种通知类型。三个服务共用同一个 `nas-notifier` 镜像，但分别挂载 `canventory.yml`、`homebox.yml`、`frigate.yml`。

- Canventory/Homebox：每天指定时间检查；默认每天 `08:00`，重启不推送。
- Frigate：持续监听 MQTT；启动不推送；默认冷却时间为 `0`，每个符合条件的 `new` 事件都推送。
- 当前 Frigate 仅发送文字和网页入口，暂不附带截图。

## 本机构建

在 Windows PowerShell 进入本目录：

```powershell
docker build -t nas-notifier:local .
```

首次运行前复制配置模板并填写真实值：

```powershell
Copy-Item .\config\canventory.example.yml .\config\canventory.yml
Copy-Item .\config\homebox.example.yml .\config\homebox.yml
Copy-Item .\config\frigate.example.yml .\config\frigate.yml
```

`.gitignore` 已排除真实 `config/*.yml`，只保留 `*.example.yml`，不要把凭据提交到 GitHub。

## 本机启动与查看日志

先验证 Compose 内容：

```powershell
docker compose -f docker-compose.example.yml config
```

启动三个通知实例：

```powershell
docker compose -f docker-compose.example.yml up -d
docker compose -f docker-compose.example.yml logs -f
```

只启动其中一个，例如 Homebox：

```powershell
docker compose -f docker-compose.example.yml up -d homebox-notify
```

## 离线导入 NAS

本机导出这一个通用镜像：

```powershell
docker image save -o nas-notifier-offline.tar nas-notifier:local
```

把 `nas-notifier-offline.tar` 导入 NAS 镜像管理页面，再将本项目目录中的 Compose 和配置文件复制到 NAS。NAS 运行时只需要 `image: nas-notifier:local`，不需要再次构建。

升级时重新构建并导出同名镜像，在 NAS 删除旧通知容器后用新镜像重新创建；外部配置文件可以继续使用。

从旧通知容器迁移时，先停止并删除原来的 `canventory-notify`、`homebox-notify`、`frigate-notify`，再创建通用容器。不要同时运行新旧两套，否则会重复推送。

临时测试定时通知时，可把对应配置中的 `run_on_start` 改为 `true` 后重启该通知容器；验证完成后改回 `false` 并再次重启。Frigate 可直接制造一个符合筛选条件的新检测事件进行测试。

## 配置说明

通用配置：

- `notifier.type`：`canventory`、`homebox` 或 `frigate`
- `notifier.timezone`：默认 `Asia/Shanghai`
- `dingtalk.webhook`：钉钉自定义机器人 Webhook
- `dingtalk.secret`：机器人开启加签时填写，否则留空
- `http.timeout_seconds`：HTTP 超时秒数
- `http.retry_attempts`：钉钉发送总尝试次数
- `http.retry_delay_seconds`：失败后重试间隔

定时类型配置：

- `schedule.notify_time`：每天执行时间，格式 `HH:MM`
- `schedule.run_on_start`：是否在容器启动时立即检查并推送
- `schedule.send_empty`：没有结果时是否也发送通知

Frigate 配置：

- `watch_labels`：需要通知的对象类型
- `watch_cameras`：需要通知的摄像头；空列表代表全部
- `event_types`：默认只处理 `new`
- `cooldown_seconds`：默认 `0`，不做冷却
- `mqtt.host` / `mqtt.port`：MQTT 地址和端口
- `mqtt.topic_prefix`：Frigate MQTT 前缀，默认订阅 `<前缀>/events`

## 网络说明

示例沿用默认 `bridge` 网络。通知容器通过 `NAS_IP:映射端口` 访问 Canventory、Homebox 和 Mosquitto，不依赖容器名解析。

如果出现“宿主机可联网、所有 bridge 容器访问公网超时”，应检查上游路由器/iStoreOS 是否存在 Docker 子网回程路由或 MASQUERADE 规则。这个问题不是通知脚本或 DNS 造成的；修复后需把规则持久化，避免路由器重启后复发。

## 发布到 GitHub

独立仓库可以使用 `.github/workflows/docker-publish.yml` 发布镜像；集成到 Docker-NAS 后，由仓库根目录的 `.github/workflows/nas-notifier.yml` 在相关源码更新时构建 `linux/amd64` 和 `linux/arm64` 镜像并发布到 GitHub Container Registry：

```text
ghcr.io/<GitHub用户名>/nas-notifier:latest
```

首次发布后，在 GitHub Packages 中把镜像可见性设为 Public，其他用户即可直接拉取。公开仓库中只提交 `*.example.yml`，不要提交实际配置文件。

工作流会先运行全部单元测试；只有测试通过才会构建并推送 `linux/amd64`、`linux/arm64` 镜像。

## 基础测试

镜像构建完成后，可将源码只读挂载进容器执行测试：

```powershell
docker run --rm -v "${PWD}:/work" -w /work nas-notifier:local python -m unittest discover -s tests -v
```
