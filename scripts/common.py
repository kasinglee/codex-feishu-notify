"""Private local configuration shared by setup and delivery. Standard library only."""
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit

DEFAULT_CONFIG = Path.home() / '.config/codex/feishu-notify/config.json'
PROJECT_ROOT = Path(__file__).resolve().parents[1]
HOOK_BASE = 'https://open.feishu.cn/open-apis/bot/v2/hook/'


class ConfigError(ValueError):
    """Only put safe, fixed diagnostic text in this exception."""


def valid_secret(value):
    return (isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{8,512}', value) is not None
            and not value.startswith('YOUR_'))


def normalize_webhook(value):
    if not isinstance(value, str):
        raise ConfigError('Webhook 缺失')
    try:
        parts = urlsplit(value.strip())
    except ValueError:
        raise ConfigError('Webhook 格式无效') from None
    prefix = '/open-apis/bot/v2/hook/'
    token = parts.path[len(prefix):] if parts.path.startswith(prefix) else ''
    if (parts.scheme != 'https' or parts.netloc != 'open.feishu.cn'
            or parts.query or parts.fragment or not re.fullmatch(r'[A-Za-z0-9_-]{1,200}', token)
            or token.startswith('YOUR_')):
        raise ConfigError('需要飞书中国版 V2 自定义机器人 Webhook；不接受其他域名、参数或占位值')
    return HOOK_BASE + token


def read_raw(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
    except FileNotFoundError:
        raise ConfigError('配置不存在，请先运行 configure.py status 并完成配置') from None
    except (OSError, ValueError, UnicodeError):
        raise ConfigError('无法读取配置或 JSON 格式无效') from None
    if not isinstance(data, dict):
        raise ConfigError('配置必须是 JSON 对象')
    return data


def normalize_config(data, require_enabled=True):
    if not isinstance(data, dict):
        raise ConfigError('配置必须是 JSON 对象')
    if require_enabled and data.get('enabled') is not True:
        raise ConfigError('通知未启用；请完成配置后运行 configure.py enable')
    webhook = data.get('webhook_url')
    if webhook is None and isinstance(data.get('FSKEY'), str):
        webhook = HOOK_BASE + data['FSKEY']
    webhook = normalize_webhook(webhook)
    secret = data.get('signing_secret', data.get('FSSIGN'))
    if not valid_secret(secret):
        raise ConfigError('签名密钥缺失或无效；请在机器人中启用签名校验并保存密钥')
    group = data.get('group_name', 'Codex通知')
    if not isinstance(group, str) or not group.strip() or len(group) > 160:
        raise ConfigError('群名称必须为 1–160 字符')
    return {'enabled': data.get('enabled') is True, 'group_name': group.strip(),
            'webhook_url': webhook, 'signing_secret': secret}


def private_write(path, data):
    path = Path(path).expanduser().absolute()
    if path.is_symlink():
        raise ConfigError('请使用真实配置文件路径，不向符号链接写入密钥')
    if path.resolve().is_relative_to(PROJECT_ROOT):
        raise ConfigError('真实配置必须保存在项目目录外；建议使用默认用户配置目录')
    parent = path.parent
    if not parent.exists():
        parent.mkdir(parents=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(prefix='.config-', dir=parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            os.fchmod(stream.fileno(), 0o600) if hasattr(os, 'fchmod') else None
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        path.chmod(0o600)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def safe_status(path):
    result = {'config_path': str(Path(path).expanduser()), 'exists': Path(path).exists()}
    if not result['exists']:
        return {**result, 'ready': False}
    try:
        raw = read_raw(path)
        result['enabled'] = raw.get('enabled') is True
        group = raw.get('group_name')
        result['group_name'] = group if isinstance(group, str) else None
        normalize_config(raw)
        result['ready'] = True
    except ConfigError as exc:
        result.update(ready=False, reason=str(exc))
    if os.name != 'nt':
        result['file_mode'] = oct(Path(path).stat().st_mode & 0o777)
        result['private_permissions'] = (Path(path).stat().st_mode & 0o077) == 0
    return result
