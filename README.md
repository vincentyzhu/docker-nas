# NAS 自托管服务集合

面向家庭 NAS 的一套 Docker 自托管服务集合，覆盖网络代理、媒体下载、文件处理、创作应用、通用工具、密码管理等常见场景，用统一的 Compose 规范组织，按需部署。

## 特性

- **统一规范**：多数服务采用一致的 restart、init、权限限制、日志轮转和资源限额；资源需求差异较大的服务会在模板中单独说明
- **自文档化**：每个 compose 文件头部写明了用途、部署前准备、端口说明，无需翻阅外部文档
- **独立部署**：每个服务独立成目录，按需启停，可根据自己的网络环境调整配置
- **模板优先**：保留服务常用端口；镜像按服务特点选择 `latest` 或明确版本，升级前应先阅读发行说明
- **统一通知**：`nas-notifier` 使用同一镜像为 Canventory、Homebox 和 Frigate 发送中文钉钉通知

## 目录结构

按功能分类组织，新增服务时归入对应分类即可：

| 目录 | 定位 |
|------|------|
| `infra/` | 基础设施：网络、代理、证书、通知 |
| `media/` | 媒体与下载 |
| `files/` | 文件处理 |
| `apps/` | 应用与创作 |
| `tools/` | 通用工具与文件分享 |
| `security/` | 安全与远程 |

通用通知镜像源码位于 `infra/nas-notifier/`。Canventory、Homebox 和 Frigate 的部署目录只保留各自的 `notify/config.yml`，账号、API Key、Webhook 和域名均通过外部配置提供。

## 服务索引

端口均为公开模板中的默认映射；复制到 NAS 后可以按实际规划修改宿主机端口。多端口或 host 网络服务应以各自 Compose 头部说明为准。

| 分类 | 服务 | 用途 | 默认端口 |
|------|------|------|----------|
| 应用 | Canventory | 食品库存与到期提醒 | 8000 |
| 应用 | DrawDB | 数据库关系图设计 | 80 |
| 应用 | Draw.io | 流程图与图表编辑 | 8080 |
| 应用 | Drawnix | 白板与图形绘制 | 80 |
| 应用 | Homebox | 家庭物品与质保管理 | 7745 |
| 应用 | SiYuan | 知识库与笔记 | 6806 |
| 文件 | BentoPDF | 浏览器端 PDF 工具 | 8080 |
| 文件 | Image Watermark Tool | 图片水印处理 | 3000 |
| 文件 | Morphos Server | 文件格式转换 | 8080 |
| 文件 | Pic Smaller | 图片压缩 | 3001 |
| 文件 | Stirling PDF | 综合 PDF 工具 | 8080 |
| 基础设施 | Certimate | SSL 证书申请与续期 | 8090 |
| 基础设施 | FRPC | FRP 内网穿透客户端 | host 网络 |
| 基础设施 | FRPS | FRP 公网服务端 | host 网络 |
| 基础设施 | Mihomo / MetaCubeXD | 网络代理与管理面板 | 7897、9090、80 |
| 基础设施 | Nginx | HTTP/HTTPS 统一入口 | 80、443 |
| 基础设施 | RustDesk Server | 远程桌面 ID 与中继 | 21115–21117 |
| 基础设施 | Sun Panel | NAS 导航面板 | 3002 |
| 基础设施 | WUD | 容器镜像更新检测 | 3000 |
| 媒体 | Frigate | AI 视频监控、MQTT 与通知 | 8971、5000、8554、8555、1883 |
| 媒体 | Music Tag Web | 音乐标签整理 | 8002 |
| 媒体 | qBittorrent | BT 下载管理 | 8080、6881 |
| 媒体 | TinyMediaManager | 影视元数据管理 | 4000 |
| 安全 | Nexterm | SSH、VNC、RDP 与 SFTP 管理 | 6191 |
| 安全 | Vaultwarden | Bitwarden 兼容密码管理 | 80 |
| 工具 | IT Tools | 常用开发与运维工具 | 80 |
| 工具 | 极速箱 | 在线工具集合 | 3000 |
| 工具 | Omni Tools | 浏览器端工具集合 | 80 |
| 工具 | WebDAV | 文件共享 | 6065 |

## 快速开始

```bash
git clone <仓库地址>
cd <分类>/<服务名>
docker compose up -d
```

目录中存在 `.env.example` 时，应先复制为 `.env` 并填写所有必填值：

```bash
cp .env.example .env
docker compose config
docker compose up -d
```

## 注意事项

- 敏感配置（域名、密钥、账号等）均以占位符标注，部署前请替换为实际值
- `.env`、真实通知配置、证书和私钥已通过 `.gitignore` 排除；提交前仍应检查 `git diff`
- 部分服务需要挂载 `docker.sock` 或硬件直通，部署前请先阅读对应 compose 文件的头部注释
- 运行时产生的数据目录已在 `.gitignore` 中排除，不会随仓库提交
- 镜像标签按服务特点选择 `latest`、主版本或固定版本；升级前请阅读对应服务的发行说明
- 服务默认端口可能重复；只部署需要的服务即可，同时运行端口重复的服务时请自行调整端口映射
- Frigate 模板中的 Mosquitto 允许匿名访问，只适合可信局域网，不应通过 FRP、Nginx 或公网防火墙对外开放
