#!/usr/bin/env python3
"""Install only skill source; preserve private configuration outside the skill."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
NAME = 'feishu-notify'


def default_destination():
    current = Path.home() / '.agents/skills' / NAME
    legacy = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'skills' / NAME
    if current.exists():
        return current.resolve()
    if legacy.exists():
        return legacy.resolve()
    return current


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=default_destination())
    parser.add_argument('--replace', action='store_true', help='备份并替换已有 skill')
    args = parser.parse_args()
    destination = args.destination.expanduser().resolve()
    if destination == ROOT or destination.is_relative_to(ROOT) or ROOT.is_relative_to(destination):
        parser.error('安装目录不能包含项目目录，也不能位于项目目录内')
    if destination.exists() and not args.replace:
        parser.error('skill 已存在；明确更新时使用 --replace，旧版将自动备份')
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix='.feishu-notify-install-', dir=destination.parent))
        backup = None
        try:
            for name in ('SKILL.md', 'scripts', 'references', 'agents', 'assets'):
                source = ROOT / name
                if source.is_dir():
                    shutil.copytree(source, staging / name,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'config.json', '*.local.json'))
                elif source.is_file():
                    shutil.copy2(source, staging / name)
            if destination.exists():
                backup = Path.home() / '.config/codex/skill-backups' / (NAME + '-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
                backup.parent.mkdir(parents=True, exist_ok=True)
                destination.rename(backup)
            try:
                staging.rename(destination)
            except OSError:
                if backup:
                    backup.rename(destination)
                raise
        finally:
            if staging.exists():
                shutil.rmtree(staging)
        print(json.dumps({'installed': True, 'destination': str(destination),
                          'backup': str(backup) if backup else None}, ensure_ascii=False))
        return 0
    except OSError:
        print('安装失败：文件操作未完成，请检查目录权限和已有 skill 位置', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
