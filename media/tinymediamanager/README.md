# tinyMediaManager

使用官方镜像 `tinymediamanager/tinymediamanager`，通过 noVNC 在浏览器中访问影视媒体库管理界面。

## 访问密码

Compose 模板已启用 `PASSWORD` 环境变量。部署前，在 NAS 本地将 `"..."` 替换为自己的访问密码，并保留其他环境变量：

```yaml
    environment:
      # 其他现有环境变量继续保留
      PASSWORD: "..."  # 必须在 NAS 本地替换为实际密码
```

这是远程图形界面的访问密码，连接 noVNC 时输入即可，无独立用户名配置。官方镜像使用 `PASSWORD`，不要套用其他镜像的 `VNC_PASSWORD` 或 `WEB_AUTHENTICATION_*` 配置。

实际密码只保留在 NAS 本地部署配置中，不提交到本仓库。公网访问时应使用 HTTPS 入口保护传输。

## 部署与更新

在 NAS 的本服务 Compose 目录执行：

```bash
# 校验成功后，再执行下一条命令；quiet 避免在终端输出含密码的完整配置
docker compose config --quiet

# 配置变化后重新创建容器，期间界面会短暂中断
docker compose up -d --no-deps tinymediamanager
```

仅执行 `docker compose restart` 不会应用修改后的环境变量。更新前确认 `./data:/data` 数据挂载保持正确，数据库与应用配置由该目录持久化保存。

更新后使用浏览器无痕窗口重新连接 `http://NAS地址:4000`（按 NAS 实际端口或 HTTPS 域名替换），检查：

- 未提供密码时无法进入图形界面。
- 输入错误密码无法连接。
- 输入正确密码可以进入图形界面。

## 资源与运行状态

Compose 模板默认设置以下资源上限，用于观察并控制资源占用：

```yaml
    cpus: "4.0"        # CPU 最多使用相当于 4 个核心的算力
    mem_limit: 4g      # 整个容器的内存上限为 4 GB
    memswap_limit: 4g  # 内存与 swap 总上限为 4 GB，即禁用 swap
```

这不是预留资源，也不是将容器绑定到指定核心。内存达到上限可能触发 OOM 终止进程；如已配置 Java 最大堆内存，应低于容器内存上限，为其他开销留出空间。

重新创建容器后观察（使用实际容器名）：

```bash
docker stats tinymediamanager
docker inspect --format 'CPU配额={{.HostConfig.NanoCpus}} 内存上限={{.HostConfig.Memory}} 内存与swap总上限={{.HostConfig.MemorySwap}}' tinymediamanager
```

预期 CPU 配额为 `4000000000`（4 核），内存与内存加 swap 总上限均为 `4294967296` 字节（4 GiB）。确认 NAS Docker 支持并实际应用这些限制；如提示不支持 swap 限制，应以 NAS 内核与 Docker 的检查结果为准。

本仓库提供配置模板与验证步骤，不代表 NAS 已完成更新或登录验证。

参考：[tinyMediaManager 官方 Docker 文档](https://www.tinymediamanager.org/docs/docker)。
