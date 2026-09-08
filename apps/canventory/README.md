# Canventory

Canventory 冰箱库存部署模板，并通过通用 `nas-notifier` 容器发送钉钉临期提醒。

本模板使用 Canventory 官方镜像：

```yaml
image: elthamini/canventory:latest
```

部署前编辑：

- `docker-compose.yml`：替换 `APP_URL`、`SECRET_KEY` 和 `NAS_IP`
- `notify/config.yml`：替换 API 地址、网页域名、通知账号及钉钉配置

通知账号需要加入目标家庭，并在 Canventory 中将该家庭切换为当前使用的家庭；否则通知服务可能读取不到需要提醒的物品。多家庭分别推送时，应为每个家庭运行独立通知容器并配置各自的账号和 Webhook。

通知默认每天 `08:00` 检查，容器重启不立即推送，没有临期物品时保持安静。

通知服务默认直接从 GHCR 拉取：

```yaml
image: ghcr.io/vincentyzhu/nas-notifier:latest
```

无法访问 GHCR 时，可在其他电脑构建并离线导入镜像，然后将通知服务的镜像改为：

```yaml
image: nas-notifier:local
```
