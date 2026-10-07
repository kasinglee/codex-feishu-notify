#!/usr/bin/env python3
"""Send one explicitly requested summary to a signed Feishu group webhook."""
import argparse
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from pathlib import Path
import socket
import sys
import time
import urllib.error
import urllib.request

from common import ConfigError, DEFAULT_CONFIG, normalize_config, read_raw

STATUSES = {'completed': '已完成', 'incomplete': '未完成',
            'failed': '执行失败', 'test': '配置测试'}


def message(data):
    if not isinstance(data, dict) or data.get('status', 'completed') not in STATUSES:
        raise ConfigError('消息状态无效')
    for field in ('title', 'summary'):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise ConfigError('需要任务名称和摘要')
    if not isinstance(data.get('next_step', ''), str):
        raise ConfigError('下一步必须是文本')
    stamp = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
    lines = [f'🔔 Codex通知｜{STATUSES[data.get("status", "completed")]}', '',
             '任务：' + data['title'].strip()[:160], '时间：' + stamp + '（北京时间）',
             '', data['summary'].strip()[:3500]]
    if data.get('next_step', '').strip():
        lines.extend(['', '下一步：' + data['next_step'].strip()[:500]])
    return '\n'.join(lines)


def signature(timestamp, secret):
    key = f'{timestamp}\n{secret}'.encode('utf-8')
    return base64.b64encode(hmac.new(key, b'', hashlib.sha256).digest()).decode('ascii')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def send(config, text, no_proxy=False):
    stamp = str(int(time.time()))
    payload = {'msg_type': 'text', 'content': {'text': text}, 'timestamp': stamp,
               'sign': signature(stamp, config['signing_secret'])}
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    if len(body) > 19000:
        raise ConfigError('消息过长')
    request = urllib.request.Request(config['webhook_url'], data=body,
        headers={'Content-Type': 'application/json; charset=utf-8'}, method='POST')
    handlers = [NoRedirect()]
    if no_proxy:
        handlers.append(urllib.request.ProxyHandler({}))
    with urllib.request.build_opener(*handlers).open(request, timeout=15) as response:
        if response.status != 200:
            raise ConfigError('飞书 HTTP 响应异常')
        try:
            result = json.load(response)
        except (ValueError, UnicodeError):
            raise ConfigError('响应不是有效 JSON，送达状态未知；请先检查群聊') from None
    code = result.get('code', result.get('StatusCode')) if isinstance(result, dict) else None
    if type(code) is not int or code != 0:
        safe_code = str(code) if type(code) is int else 'unknown'
        raise ConfigError('飞书拒绝消息，错误码：' + safe_code)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    parser.add_argument('--dry-run', action='store_true', help='离线检查，不发送')
    parser.add_argument('--no-proxy', action='store_true', help='本次请求直接连接飞书')
    args = parser.parse_args()
    try:
        raw = sys.stdin.read(20001)
        if len(raw) > 20000:
            raise ConfigError('输入过长')
        try:
            text = message(json.loads(raw))
        except (ValueError, TypeError) as exc:
            if isinstance(exc, ConfigError):
                raise
            raise ConfigError('输入必须是有效消息 JSON') from None
        config = normalize_config(read_raw(args.config))
        if args.dry_run:
            result = {'dry_run': True, 'group': config['group_name'], 'signed': True,
                      'transport': 'feishu-webhook', 'text': text}
        else:
            send(config, text, args.no_proxy)
            result = {'accepted': True, 'group': config['group_name'],
                      'transport': 'feishu-webhook'}
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except ConfigError as exc:
        print('通知失败：' + str(exc), file=sys.stderr)
    except urllib.error.HTTPError as exc:
        print('通知失败，HTTP 状态：' + str(exc.code), file=sys.stderr)
    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError):
        print('网络失败或超时，送达状态可能未知；未自动重发，请先检查群聊。', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
