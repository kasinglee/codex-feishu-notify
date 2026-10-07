# Codex 飞书通知项目

先读 README.md 和 SKILL.md。用户要求安装／配置时继续读 references/setup.md，并执行 scripts/configure.py status；该脚本只显示脱敏状态。使用实际可用的 computer use 工具操作客户端，缺少能力时提供具体手工步骤，不声称已自动完成。

此仓库只实现单向签名 Webhook 通知。将真实配置保存在仓库外的用户配置目录；不读取或改写双向桥接配置。不要显示真实密钥、剪贴板内容或未脱敏的机器人配置截图。公开前检查暂存文件与凭据隔离。

Python 3.10+，标准库。修改脚本后运行 `python3 -m unittest discover -s tests -v`；离线测试不得读取真实用户配置或向飞书发送消息。实际配置测试按用户授权进行，一次发送后检查群聊，网络不确定时不自动重试。
