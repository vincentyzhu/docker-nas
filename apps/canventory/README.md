# Canventory

Canventory 冰箱库存部署模板，并通过通用 `nas-notifier` 容器发送钉钉临期提醒。

本模板暂时使用官方镜像：

```yaml
image: elthamini/canventory:latest
```

官方镜像不包含中文界面、数量单位和按保质期天数换算到期日期的二次开发。后续发布自定义镜像时，只需替换 Compose 中的镜像地址，现有 `./data` 数据目录可以继续挂载使用。

部署前编辑：

- `docker-compose.yml`：替换 `APP_URL`、`SECRET_KEY` 和 `NAS_IP`
- `notify/config.yml`：替换 API 地址、网页域名、通知账号及钉钉配置

通知账号需要加入目标家庭，并在 Canventory 中将该家庭切换为当前使用的家庭；否则通知服务可能读取不到需要提醒的物品。多家庭分别推送时，应为每个家庭运行独立通知容器并配置各自的账号和 Webhook。

通知默认每天 `08:00` 检查，容器重启不立即推送，没有临期物品时保持安静。

离线导入通用通知镜像时，将通知服务的镜像改为：

```yaml
image: nas-notifier:local
```
