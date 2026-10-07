#!/usr/bin/env python3
"""Configure signed Feishu notifications without echoing credentials."""
import argparse
import getpass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from common import (ConfigError, DEFAULT_CONFIG, normalize_config,
                    normalize_webhook, private_write, read_raw, safe_status, valid_secret)


def clipboard_text():
    if sys.platform == 'darwin':
        command = ['pbpaste']
    elif os.name == 'nt':
        command = ['powershell', '-NoProfile', '-Command', 'Get-Clipboard -Raw']
    elif shutil.which('wl-paste'):
        command = ['wl-paste', '--no-newline']
    elif shutil.which('xclip'):
        command = ['xclip', '-selection', 'clipboard', '-o']
    else:
        raise ConfigError('此环境无法读取剪贴板；请使用 write 的本机交互输入模式')
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                encoding='utf-8', timeout=5, check=True)
    except (OSError, UnicodeError, subprocess.SubprocessError):
        raise ConfigError('读取剪贴板失败；未输出剪贴板内容') from None
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('status', help='仅显示配置状态，不显示密钥')
    write = commands.add_parser('write', help='写入完整配置')
    write.add_argument('--stdin', action='store_true', help='从 stdin 读取私密 JSON')
    write.add_argument('--group-name', default='Codex通知')
    write.add_argument('--replace', action='store_true', help='明确替换已有配置')
    capture = commands.add_parser('capture', help='从剪贴板保存一个字段，保持通知禁用')
    capture.add_argument('field', choices=['webhook', 'secret'])
    capture.add_argument('--group-name')
    capture.add_argument('--replace', action='store_true', help='明确替换已有已启用配置')
    commands.add_parser('enable', help='校验全部字段并启用')
    commands.add_parser('disable', help='停用通知，保留私密配置')
    args = parser.parse_args()
    try:
        if args.command == 'status':
            result = safe_status(args.config)
        elif args.command == 'write':
            if args.config.exists() and not args.replace:
                raise ConfigError('配置已存在；先运行 status，明确替换时使用 --replace')
            if args.stdin:
                try:
                    data = json.loads(sys.stdin.read(20001))
                except (ValueError, UnicodeError):
                    raise ConfigError('配置输入必须是有效 JSON') from None
            else:
                if not sys.stdin.isatty():
                    raise ConfigError('交互模式需要本机终端；自动化请使用 capture 或 write --stdin')
                data = {'enabled': True, 'group_name': args.group_name,
                        'webhook_url': getpass.getpass('Webhook（隐藏输入）：'),
                        'signing_secret': getpass.getpass('签名密钥（隐藏输入）：')}
            config = normalize_config(data, require_enabled=False)
            config['enabled'] = True
            private_write(args.config, config)
            result = safe_status(args.config)
        elif args.command == 'capture':
            data = read_raw(args.config) if args.config.exists() else {'enabled': False}
            if data.get('enabled') is True and not args.replace:
                raise ConfigError('已有已启用配置；重新配置前需明确使用 --replace')
            value = clipboard_text()
            if args.field == 'webhook':
                data['webhook_url'] = normalize_webhook(value)
                data.pop('FSKEY', None)
                data.pop('signing_secret', None)
                data.pop('FSSIGN', None)
            else:
                if not valid_secret(value) or any(char.isspace() for char in value):
                    raise ConfigError('剪贴板不是有效签名密钥，请重新复制正确字段')
                data['signing_secret'] = value
                data.pop('FSSIGN', None)
            data['enabled'] = False
            if args.group_name:
                data['group_name'] = args.group_name
            data.setdefault('group_name', 'Codex通知')
            private_write(args.config, data)
            result = {'saved_field': args.field, 'enabled': False,
                      'config_path': str(args.config), 'credentials_redacted': True}
        else:
            data = read_raw(args.config)
            if args.command == 'enable':
                data = normalize_config(data, require_enabled=False)
                data['enabled'] = True
            else:
                data['enabled'] = False
            private_write(args.config, data)
            result = safe_status(args.config)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except ConfigError as exc:
        print('配置失败：' + str(exc), file=sys.stderr)
    except (OSError, UnicodeError):
        print('配置失败：无法写入本机配置文件；密钥未输出', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
