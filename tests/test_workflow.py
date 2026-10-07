"""Offline contract checks: never load the user's real credentials or send messages."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import common
import configure
import send

FIXTURE = {'enabled': True, 'group_name': 'Offline test group',
           'webhook_url': common.HOOK_BASE + 'offline-test-token',
           'signing_secret': 'offline-test-secret'}
MESSAGE = {'title': 'Offline contract check', 'status': 'test', 'summary': 'No live delivery.'}


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'private' / 'config.json'

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, script, *args, data=None):
        return subprocess.run([sys.executable, str(ROOT / 'scripts' / script), *map(str, args)],
                              input=json.dumps(data) if data is not None else None,
                              text=True, capture_output=True, timeout=10)

    def test_private_write_redacted_status_and_dry_run(self):
        result = self.cli('configure.py', '--config', self.path, 'write', '--stdin', data=FIXTURE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['ready'])
        self.assertNotIn(FIXTURE['signing_secret'], result.stdout)
        self.assertNotIn(FIXTURE['webhook_url'], result.stdout)
        if os.name != 'nt':
            self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(self.path.parent.stat().st_mode & 0o777, 0o700)
        dry = self.cli('send.py', '--config', self.path, '--dry-run', data=MESSAGE)
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertTrue(json.loads(dry.stdout)['dry_run'])
        self.assertNotIn(FIXTURE['signing_secret'], dry.stdout)
        disabled = self.cli('configure.py', '--config', self.path, 'disable')
        self.assertEqual(disabled.returncode, 0)
        denied = self.cli('send.py', '--config', self.path, '--dry-run', data=MESSAGE)
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn('未启用', denied.stderr)

    def test_existing_config_not_overwritten_implicitly(self):
        common.private_write(self.path, FIXTURE)
        before = self.path.read_bytes()
        other = {**FIXTURE, 'group_name': 'Different group'}
        result = self.cli('configure.py', '--config', self.path, 'write', '--stdin', data=other)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.path.read_bytes(), before)

    def test_capture_requires_complete_new_credentials(self):
        args = ['configure.py', '--config', str(self.path), 'capture', 'webhook', '--group-name', 'Test']
        output = io.StringIO()
        with patch.object(sys, 'argv', args), patch.object(configure, 'clipboard_text', return_value=FIXTURE['webhook_url']), contextlib.redirect_stdout(output):
            self.assertEqual(configure.main(), 0)
        self.assertFalse(common.read_raw(self.path)['enabled'])
        premature = self.cli('configure.py', '--config', self.path, 'enable')
        self.assertNotEqual(premature.returncode, 0)
        args = ['configure.py', '--config', str(self.path), 'capture', 'secret']
        with patch.object(sys, 'argv', args), patch.object(configure, 'clipboard_text', return_value=FIXTURE['signing_secret']), contextlib.redirect_stdout(output):
            self.assertEqual(configure.main(), 0)
        self.assertNotIn(FIXTURE['signing_secret'], output.getvalue())
        self.assertEqual(self.cli('configure.py', '--config', self.path, 'enable').returncode, 0)
        # Replacing a destination clears the old signing credential and disables sending.
        args = ['configure.py', '--config', str(self.path), 'capture', 'webhook', '--replace']
        with patch.object(sys, 'argv', args), patch.object(configure, 'clipboard_text', return_value=FIXTURE['webhook_url']), contextlib.redirect_stdout(output):
            self.assertEqual(configure.main(), 0)
        self.assertNotIn('signing_secret', common.read_raw(self.path))
        self.assertFalse(common.read_raw(self.path)['enabled'])

    def test_legacy_configuration_is_compatible(self):
        legacy = {'enabled': True, 'FSKEY': 'offline-test-token', 'FSSIGN': 'offline-test-secret'}
        self.assertEqual(common.normalize_config(legacy)['webhook_url'], FIXTURE['webhook_url'])

    def test_invalid_destinations_and_placeholder_rejected_without_echo(self):
        urls = ['http://open.feishu.cn/open-apis/bot/v2/hook/private-value',
                'https://evil.invalid/open-apis/bot/v2/hook/private-value',
                common.HOOK_BASE + 'private-value?key=private-value',
                common.HOOK_BASE + 'YOUR_WEBHOOK_TOKEN']
        for url in urls:
            with self.subTest(url=url):
                result = self.cli('configure.py', '--config', self.path, 'write', '--stdin',
                                  data={**FIXTURE, 'webhook_url': url})
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('private-value', result.stdout + result.stderr)
                self.assertFalse(self.path.exists())
        self.assertFalse(common.valid_secret(FIXTURE['webhook_url']))

    def test_repository_and_symlink_config_writes_refused(self):
        with self.assertRaises(common.ConfigError):
            common.private_write(ROOT / 'config.json', FIXTURE)
        if os.name != 'nt':
            target = Path(self.temp.name) / 'target.json'
            target.write_text('original', encoding='utf-8')
            linked = Path(self.temp.name) / 'linked.json'
            linked.symlink_to(target)
            with self.assertRaises(common.ConfigError):
                common.private_write(linked, FIXTURE)
            self.assertEqual(target.read_text(), 'original')

    def test_live_contract_signed_request_and_no_retry(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b'{"code":0}'
        with patch.object(send.time, 'time', return_value=1700000000), patch.object(send.urllib.request, 'build_opener') as factory:
            opener = factory.return_value
            opener.open.return_value = Response()
            send.send(FIXTURE, 'hello')
            request = opener.open.call_args.args[0]
            payload = json.loads(request.data)
            self.assertEqual(payload['timestamp'], '1700000000')
            self.assertEqual(payload['msg_type'], 'text')
            self.assertEqual(payload['sign'], send.signature('1700000000', FIXTURE['signing_secret']))
            self.assertTrue(any(isinstance(handler, send.NoRedirect) for handler in factory.call_args.args))
            opener.open.reset_mock()
            opener.open.side_effect = TimeoutError('sensitive-value-must-not-be-printed')
            with self.assertRaises(TimeoutError):
                send.send(FIXTURE, 'hello')
            self.assertEqual(opener.open.call_count, 1)
        self.assertIsNone(send.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://evil.invalid'))

    def test_network_error_cli_does_not_echo_or_retry(self):
        common.private_write(self.path, FIXTURE)
        output = io.StringIO()
        with patch.object(sys, 'argv', ['send.py', '--config', str(self.path)]), patch.object(sys, 'stdin', io.StringIO(json.dumps(MESSAGE))), patch.object(send, 'send', side_effect=urllib.error.URLError(FIXTURE['webhook_url'])) as delivery, contextlib.redirect_stderr(output):
            self.assertEqual(send.main(), 1)
        self.assertEqual(delivery.call_count, 1)
        self.assertNotIn(FIXTURE['webhook_url'], output.getvalue())
        self.assertIn('未自动重发', output.getvalue())

    def test_installer_keeps_config_out_and_backs_up_old_skill(self):
        home = Path(self.temp.name) / 'fake-home'
        destination = home / '.agents/skills/feishu-notify'
        env = {**os.environ, 'HOME': str(home), 'USERPROFILE': str(home)}
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/install.py'), '--destination', str(destination)],
                                text=True, capture_output=True, env=env, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((destination / 'SKILL.md').exists())
        self.assertFalse((destination / 'config.example.json').exists())
        self.assertFalse((destination / 'config.json').exists())
        (destination / 'custom-old-file').write_text('old skill')
        replaced = subprocess.run([sys.executable, str(ROOT / 'scripts/install.py'), '--destination', str(destination), '--replace'],
                                  text=True, capture_output=True, env=env, timeout=10)
        self.assertEqual(replaced.returncode, 0, replaced.stderr)
        backup = Path(json.loads(replaced.stdout)['backup'])
        self.assertEqual((backup / 'custom-old-file').read_text(), 'old skill')
        self.assertFalse((destination / 'custom-old-file').exists())


if __name__ == '__main__':
    unittest.main()
