# 本机配置

默认路径为 `~/.config/codex/feishu-notify/config.json`。Windows 对应当前用户主目录下 `.config/codex/feishu-notify/config.json`。配置不随 skill 安装复制，也不进入 Git。

## 字段

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| `enabled` | boolean | 为 true 才允许发送 |
| `group_name` | string | 显示用的群名称；并非查找或路由群的依据 |
| `webhook_url` | string | 飞书中国版群自定义机器人的完整 V2 Webhook |
| `signing_secret` | string | 与该机器人“签名校验”一致的密钥 |

真正决定目标群的是 Webhook。脚本固定只接受 HTTPS 的 `open.feishu.cn` 和 `/open-apis/bot/v2/hook/` 路径，拒绝额外参数、其他域名或占位值；不跟随 HTTP 重定向。

兼容原配置的 `FSKEY`（Webhook 最后一段 token）与 `FSSIGN`（签名密钥）。读旧配置无需迁移；通过 `write` 或 `enable` 写入后使用新字段。此项目不会读取 `feishu-bridge/config.json`。

## 配置命令

```sh
python3 scripts/configure.py status
python3 scripts/configure.py write --group-name 'Codex通知'
python3 scripts/configure.py disable
python3 scripts/configure.py enable
```

`write` 默认在本机终端隐藏读取两项凭据；已存在文件时需要明确的 `--replace`。自动配置可用两次 `capture`，或通过工具的标准输入向 `write --stdin` 提供完整私密 JSON。不要把凭据当命令行参数或写入 shell 历史。

所有命令支持指定路径，参数必须在子命令前：

```sh
python3 scripts/configure.py --config ~/.config/codex/feishu-notify/setup-test.json status
python3 scripts/send.py --config ~/.config/codex/feishu-notify/setup-test.json --dry-run
```

后一条还需要从 stdin 传入任务 JSON。项目目录内的真实配置写入会被拒绝；`config.example.json` 仅展示结构，不可发送。

## 状态含义

`ready: true` 表示 enabled 与字段都有效，只是离线状态。`accepted: true` 表示飞书接口接受本次发送。群中看到消息才表示实际到达，手机推送还取决于群静音与设备设置。

## 权限及存储

配置脚本使用同目录临时文件原子替换，以减少写入中断造成的损坏；macOS/Linux 文件权限设为 `0600`，新建的配置目录使用 `0700`。已存在目录的权限不会自动改写。Windows 的文件保护仍依赖用户目录 ACL。

这是明文 JSON，适合个人本机配置；不提供系统钥匙串或加密保险库功能。不要将真实文件放进共享目录、仓库或公开截图。发现凭据曾公开时，应在飞书重新生成对应密钥，再更新本机配置。
