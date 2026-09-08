# Vaultwarden

Vaultwarden 是兼容 Bitwarden 客户端的自托管密码管理服务。账号数据、附件、密钥和运行配置均保存在 `./data`，应对整个目录进行定期备份。

## 配置方式

本模板统一使用 `./data/config.json`，不再在 Compose 中重复设置域名、管理密码和 SMTP。这样可以避免 `config.json` 与环境变量同时存在时发生覆盖。

Vaultwarden 不会在第一次启动时根据 Compose 环境变量生成 `config.json`。该文件通常由 `/admin` 页面第一次保存设置时生成；本模板为了方便首次部署，提供一个不含真实密钥的 `config.example.json`。

部署步骤：

```bash
cp ./data/config.example.json ./data/config.json
vim ./data/config.json
docker compose config
docker compose up -d
```

至少需要修改：

- `domain`：填写实际 HTTPS 地址，并与 Nginx 的 `server_name` 对应。
- `admin_token`：填写 `/admin` 管理后台密码，推荐使用 Argon2 PHC 字符串。
- `smtp_from`、`smtp_username`、`smtp_password`：需要邮件功能时填写。

示例中的 SMTP 字段使用中文提示值，目的是避免遗漏；这些内容不是有效邮箱配置，复制后必须替换。`admin_token` 刻意保持为空，避免公开模板内置一个所有人都知道的管理后台明文密码。

模板端口为 `80:80`。实际部署应通过带有效证书的 Nginx HTTPS 反向代理访问，不要将 Vaultwarden 或 `/admin` 直接暴露到公网。

## 管理后台密码

`admin_token` 是 `/admin` 管理后台的登录凭据。建议使用 Vaultwarden 内置命令生成 Argon2 PHC 字符串：

```bash
docker exec -it vaultwarden /vaultwarden hash
```

将命令生成的完整内容直接写入 JSON，保留单个 `$`：

```json
{
  "admin_token": "$argon2id$v=19$m=65540,t=3,p=4$..."
}
```

登录 `/admin` 时输入生成哈希时使用的原始密码，不是整段 Argon2 哈希。

## `config.json` 注意事项

- `config.json` 中的值优先于同名环境变量，因此不要再在 Compose 中重复维护这些设置。
- `config.example.json` 只用于创建首次配置，可以提交到 Git。
- 实际的 `config.json` 可能包含域名、SMTP 账号、授权码和管理令牌，已被 `.gitignore` 排除，禁止提交。
- `config.json` 是标准 JSON，不能加入 `//` 或 `#` 注释，否则 Vaultwarden 无法解析。
- 通过 `/admin` 修改配置后必须点击 `Save`，Vaultwarden 才会把设置写回该文件。

如果已经存在可用的 `./data/config.json`，升级模板时保留该文件即可，无需从示例重新生成。
