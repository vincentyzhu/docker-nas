# Homebox

Homebox 家庭物品管理模板，并通过通用 `nas-notifier` 容器发送钉钉质保提醒。

通知行为：

- 默认每天 `08:00` 检查
- 容器启动或重启时不立即推送
- 没有符合条件的物品时不推送
- 只通知今天和未来 `remind_days` 天内到期的物品
- 不通知已经过保、已归档、终身质保、位置或未填写质保日期的物品

部署前必须保持原有 `HBOX_AUTH_API_KEY_PEPPER` 不变，并在 Homebox 的 API Keys 页面创建专用 Key。真实 Key、Webhook 和域名只填写到 NAS 上的 `notify/config.yml`，不要提交到公开仓库。

通知服务默认直接从 GHCR 拉取：

```yaml
image: ghcr.io/vincentyzhu/nas-notifier:latest
```

无法访问 GHCR 时，可在其他电脑构建并离线导入镜像，然后将通知服务的镜像改为：

```yaml
image: nas-notifier:local
```
