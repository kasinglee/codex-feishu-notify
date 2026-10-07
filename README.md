# Codex 飞书任务通知

让 Codex 在你说“做完发飞书”后，把当前任务的结果摘要发送到飞书群。支持完成、未完成、失败和配置测试；通过自定义机器人 Webhook 发送，并使用签名校验。

**额外提供 Codex 配置引导**：把本项目交给具备 computer use 的 Codex，它可以检查环境、协助创建群和机器人、保存本机配置，再发送测试消息。扫码登录、组织权限或工具要求的确认仍由用户完成。

当前范围是单向通知。双向聊天和远程控制不在此版本中。

## 直接交给 Codex 配置

将仓库链接或克隆后的目录交给 Codex，并发送：

> 阅读这个项目的 README.md、SKILL.md 和 references/setup.md，帮我安装并配置飞书单向通知。优先复用已有有效配置；如果没有，为我创建一个仅自己加入的“Codex通知”群和自定义机器人，启用签名校验，将密钥保存到本机用户配置目录。我允许向这个通知群发送一条配置测试消息。用 computer use 完成界面操作；遇到扫码登录、组织权限或工具要求的确认时告诉我当前步骤。不要把密钥发到聊天或提交 Git。

Codex 应先完成本地检查，再根据实际界面继续。**仅仅阅读 README 不会触发创建机器人或发送消息**；上面的请求明确了你希望进行的操作。没有 computer use 的 Codex 也可以安装脚本，并指导你完成飞书界面步骤。

## 准备条件

| 条件 | 用途 | 缺少时怎么处理 |
| --- | --- | --- |
| Python 3.10+ | 运行发送、配置和安装脚本 | 从 [Python 官网](https://www.python.org/downloads/) 安装；脚本无需 pip 依赖 |
| 飞书账号 | 接收通知、管理目标群 | 从 [飞书官网](https://www.feishu.cn/) 注册或登录，由用户完成扫码和验证 |
| 飞书桌面 App | 本次实机确认的群与机器人创建路径 | 从 [官网下载页](https://www.feishu.cn/download) 安装；也可由用户在可用的飞书客户端手工完成 |
| 可用的浏览器 | 登录辅助、查看官方说明或下载客户端 | 可用 Chrome 等；已登录桌面 App 时无需先登录开发者后台 |
| Codex 的 computer use 能力 | 自动操作浏览器和桌面 App | 不具备时使用下面的手工路径；单纯 CLI 无法自动点击桌面 |
| 目标群的机器人管理权限 | 添加自定义机器人 | 使用自己创建的通知群；组织禁用机器人时请联系管理员 |

自定义机器人直接在群中创建，添加后即进入该群。这个流程不要求申请开发者应用，也不需要 App ID、App Secret、公网服务或常驻桥接进程。参考 [飞书自定义机器人官方指南](https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot)。

## 安装 skill

克隆后，在项目根目录运行：

```sh
git clone https://github.com/kasinglee/codex-feishu-notify.git
cd codex-feishu-notify
python3 scripts/install.py
```

新安装默认放在 `~/.agents/skills/feishu-notify`。如果本机已有此 skill，安装器会识别旧目录或符号链接，先提示已有安装。明确更新时使用：

```sh
python3 scripts/install.py --replace
```

更新前自动将旧 skill 备份到 `~/.config/codex/skill-backups/`。配置密钥保存在独立用户目录，安装器不会复制配置。需要指定安装位置时可用 `--destination <目录>`；旧版环境可以显式选择 `~/.codex/skills/feishu-notify`。

官方当前支持 `~/.agents/skills` 和符号链接；如果安装后没有显示，重新打开 Codex。见 [OpenAI 官方 skill 文档](https://learn.chatgpt.com/docs/build-skills)。

## 手工配置：从建群到收到消息

1. 打开并登录飞书桌面 App，确认当前账号及组织正确。
2. 点左上角“＋／New”→“创建群／New Group”。选择普通聊天群，填写“Codex通知”，可只保留自己；点击“创建”。已有合适的群可直接打开。
3. 在群右上角“⋯”→“设置／Settings”→“群机器人／Bots”→“添加机器人／Add Bot”→“自定义机器人／Custom Bot”。
4. 填写名称，如“Codex任务通知”；描述可写“仅在用户要求时发送 Codex 任务结果摘要”。使用默认头像即可，点击“添加”。
5. 在机器人设置中启用“签名校验／Signature Verification”，获取 Webhook 地址及签名密钥。保持已有关键词或 IP 限制时，发送内容及网络出口也须满足它们；不要为了通过测试随意关闭安全设置。
6. 在本机终端运行配置命令，按提示粘贴两项凭据。输入隐藏，不会打印密钥：

   ```sh
   python3 scripts/configure.py write --group-name 'Codex通知'
   python3 scripts/configure.py status
   ```

   已有配置会拒绝覆盖；确实需要重新配置时，在 `write` 后加 `--replace`。`status` 输出 `ready: true` 表示本地字段有效，尚未证明网络可达。

7. 离线预览，再发送一条配置测试消息：

   ```sh
   python3 scripts/send.py --dry-run <<'FEISHU_MESSAGE'
   {"title":"飞书通知配置测试","status":"test","summary":"这是一条配置测试消息。以后在 Codex 中说“做完发飞书”，即可收到本次任务结果摘要。"}
   FEISHU_MESSAGE
   ```

   确认群与消息正确后，去掉 `--dry-run` 再运行一次。返回 `accepted: true` 表示飞书接口接受消息；回到目标群看到同一条消息，才完成到达验证。超时先检查群聊，避免自动重发造成重复。

以上 heredoc 用于 macOS/Linux 的 shell。Windows 用户可以使用 Python（命令可能为 `py -3`）和本机 JSON 文件管道；发送 JSON 不包含密钥，凭据依然由隐藏输入的配置脚本保存。

用于 Codex 的详细 computer use 步骤见 [references/setup.md](references/setup.md)，本机配置字段见 [docs/configuration.md](docs/configuration.md)。

## 自动保存凭据，避免贴进聊天

Codex 在界面点击 Webhook 的复制按钮后，运行：

```sh
python3 scripts/configure.py capture webhook --group-name 'Codex通知'
```

再在界面复制签名密钥，运行：

```sh
python3 scripts/configure.py capture secret
python3 scripts/configure.py enable
python3 scripts/configure.py status
```

脚本只读取本机剪贴板并将该字段保存到配置文件，输出字段名称和状态。逐字段保存期间通知保持禁用；全部校验后才启用。不要在复制和保存之间执行其他复制操作。

macOS 使用系统 `pbpaste`；Windows 使用 PowerShell `Get-Clipboard`；Linux 使用已有的 `wl-paste` 或 `xclip`。没有这些能力时使用 `configure.py write`，不会自动安装额外剪贴板工具。剪贴板可能被系统历史或第三方工具保留；配置后可在用户同意下清空本次密钥，或选择本机隐藏输入。

## 日常使用

安装配置好后，对 Codex 说：

> 帮我整理这份文档，做完发飞书。

> 使用 $feishu-notify，发送当前任务的完成结果。

skill 在最终答复前发送一次摘要，普通聊天和配置讨论不会自动通知。通知请求只对当前任务有效，不自动开全局 Hook，也不创建定时任务。

开发时直接从仓库调用也可以：

```sh
python3 scripts/send.py <<'FEISHU_MESSAGE'
{"title":"文档整理","status":"completed","summary":"已整理目录并补充使用说明。","next_step":"查看更新后的 README。"}
FEISHU_MESSAGE
```

## 密钥保存方式

可以使用 `config.json` 保存密钥。它是**本机私密配置文件**，默认位于：

```text
~/.config/codex/feishu-notify/config.json
```

仓库仅包含 [config.example.json](config.example.json)，没有可用凭据。配置脚本会拒绝向项目目录写入真实配置，并在 macOS/Linux 将文件设为 `0600`。JSON 文件本身是明文；应依靠用户目录权限和设备保护，不应提交 Git、共享云盘或贴到聊天。Windows 上还需要由用户目录的 ACL 保护，`chmod` 不等于 Windows ACL 隔离。

## 已确认的能力与限制

- Python 标准库实现；签名发送、离线检查、配置状态、私密配置写入和安装备份。
- macOS 飞书桌面 App 的建群、添加自定义机器人和签名设置路径需以当前界面为准；实机过程记录见 [docs/walkthrough.md](docs/walkthrough.md)。
- 自动配置依赖当前 Codex 实例具备 computer use 能力，并且能控制用户已登录的飞书客户端。README 是操作指南，不是独立 GUI 自动化程序。
- 仅支持飞书中国版 `open.feishu.cn` 自定义机器人 V2 Webhook；不读取双向桥接配置。
- 机器人只接收通知；回复机器人不会继续 Codex 任务。

## 排查

| 现象 | 处理 |
| --- | --- |
| 配置不存在或未启用 | 运行 `configure.py status`，完成字段保存并运行 `enable` |
| 找不到自定义机器人入口 | 检查是否为聊天群、是否拥有管理权限、组织是否禁用自定义机器人 |
| 错误码 `19021` | 核对签名校验和密钥，检查系统时间；不要输出密钥 |
| 错误码 `19024` | 机器人启用了关键词校验；消息须包含既有关键词 |
| 错误码 `19022` | 网络出口不符合机器人 IP 白名单；检查网络与机器人设置 |
| 网络失败或超时 | 先检查群聊，再检查代理和网络；不要自动重发 |
| 配置显示 ready，但没有手机提醒 | 先确认群消息到达，再检查飞书群静音、手机推送和系统通知权限 |

## 开发验证

```sh
python3 -m unittest discover -s tests -v
```

离线验证不向飞书发送消息，不读取你的真实配置。MIT License。
