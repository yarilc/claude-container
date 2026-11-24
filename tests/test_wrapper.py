"""Claude-specific launcher checks: the real entry script with Claude's agent part.

The launcher behavior is tested once, for every wrapper, by the shared
tests/test_launcher.py against fixture agent parts. These cases cover what only
Claude's own profile and agent part show: the shipped provider inventories, the
approval bypass hook and its help, the provider-only optional-traffic settings
and the API key that follows the selected policy profile.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / 'claude-container.sh'
FAKE = (ROOT / 'tests/fake_podman.py').read_text()
sys.path.insert(0, str(ROOT / 'tests'))
from test_launcher import build_inputs_hash, synthetic_install  # noqa: E402

PROVIDER_ONLY = ('CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1', 'DISABLE_AUTOUPDATER=1', 'DISABLE_TELEMETRY=1',
                 'DISABLE_ERROR_REPORTING=1', 'ENABLE_CLAUDEAI_MCP_SERVERS=false', 'CLAUDE_CODE_DISABLE_ARTIFACT=1')
BYPASS = '--dangerously-skip-permissions'


class AccountInventoryTests(unittest.TestCase):
    """Claude-specific exact provider inventories (N21)."""
    def setUp(self):
        sys.path.insert(0, str(ROOT / 'network'))
        import agent_profile
        import policy
        self.policy = policy
        self.rules = agent_profile.load(ROOT / agent_profile.PROFILE).policy_rules()
        self.value = json.loads((ROOT / agent_profile.POLICY).read_text())

    def hosts(self, name):
        return {(d['host'], d['port']) for d in self.value['profiles'][name]['destinations']}

    def test_shipped_inventories_are_exact(self):
        self.policy.validate(json.loads(json.dumps(self.value)), self.rules)
        self.assertEqual(self.hosts('anthropic-api'), {('api.anthropic.com', 443)})
        self.assertEqual(self.hosts('anthropic-account'), {('api.anthropic.com', 443), ('platform.claude.com', 443)})
        self.assertEqual(self.value['revision'], 'anthropic-2026-11-08-v2')

    def test_removed_account_hosts_require_a_separate_profile(self):
        for host in ('claude.ai', 'claude.com'):
            with self.subTest(host=host):
                value = json.loads(json.dumps(self.value))
                value['profiles']['anthropic-account']['destinations'].append({'host': host, 'port': 443})
                with self.assertRaisesRegex(self.policy.PolicyError, 'exact base profile'):
                    self.policy.validate(value, self.rules)
        value = json.loads(json.dumps(self.value))
        value['profiles']['account-with-web'] = {
            'authentication': 'account', 'disable_optional_traffic': True,
            'destinations': [*value['profiles']['anthropic-account']['destinations'],
                             {'host': 'claude.ai', 'port': 443}, {'host': 'claude.com', 'port': 443}]}
        self.policy.validate(value, self.rules)


class WrapperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='claude-wrapper-', dir=os.environ.get('SANDBOX_TEST_TMPDIR'))
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        podman = self.bin / 'podman'
        podman.write_text(FAKE)
        podman.chmod(0o755)
        self.project = self.base / 'parent with spaces' / 'my project'
        self.project.mkdir(parents=True)
        self.log = self.base / 'calls.jsonl'
        self.state = self.base / 'state'
        self.env = {'PATH': str(self.bin) + ':' + os.environ['PATH'], 'HOME': str(self.base / 'host-home'),
                    'CLAUDE_CONTAINER_NETWORK': 'unrestricted', 'CLAUDE_CONTAINER_MAINTENANCE': '1',
                    'FAKE_LABEL_HASH': build_inputs_hash(ROOT), 'FAKE_LOG': str(self.log)}

    def run_wrapper(self, *args, wrapper=WRAPPER, **env):
        return subprocess.run([str(wrapper), *args], cwd=self.project, env=self.env | env, input='input payload',
                              text=True, capture_output=True, timeout=30)

    def calls(self):
        return [json.loads(s) for s in self.log.read_text().splitlines()] if self.log.exists() else []

    def agent_create(self):
        return next(c for c in self.calls() if c[0] == 'create' and not any('.egress=' in a for a in c))

    @staticmethod
    def environment(create):
        return [create[i + 1] for i, arg in enumerate(create) if arg == '--env']

    def test_help_documents_the_approval_bypass(self):
        result = subprocess.run(['/bin/bash', str(WRAPPER), '--container-help'], cwd=self.project,
                                env={'PATH': '/usr/bin:/bin', 'HOME': self.env['HOME']},
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('CLAUDE_YOLO', result.stdout)
        self.assertIn(BYPASS, result.stdout)
        self.assertIn('anthropic-api: api.anthropic.com', result.stdout)
        self.assertIn('anthropic-account: api.anthropic.com, platform.claude.com', result.stdout)
        self.assertLess(result.stdout.index('CLAUDE_CONTAINER_NETWORK'), result.stdout.index('CLAUDE_YOLO'))
        self.assertIn('Host Podman delegation was removed: CLAUDE_CONTAINER_PODMAN=1 stops startup.', result.stdout)
        self.assertEqual(self.calls(), [])

    def test_four_independent_permission_combinations(self):
        # State mode and permission bypass; host Podman delegation was removed.
        for isolated in (False, True):
            for yolo in ('0', '1'):
                with self.subTest(isolated=isolated, yolo=yolo):
                    self.log.unlink(missing_ok=True)
                    result = self.run_wrapper('-p', 'test', CLAUDE_YOLO=yolo,
                                              CLAUDE_CONTAINER_STATE_DIR=str(self.state) if isolated else '')
                    self.assertEqual(result.returncode, 0, result.stderr)
                    create = self.agent_create()
                    self.assertEqual(BYPASS in create, yolo == '1')
                    self.assertFalse(any('podman.sock' in a for a in create))
                    self.assertEqual(create[-2:], ['-p', 'test'])
                    self.assertNotIn('--privileged', create)
                    self.assertFalse(any('label=disable' in a for a in create))

    def test_bypass_precedes_claude_arguments_and_never_reaches_the_shell(self):
        result = self.run_wrapper('-p', 'hello world', '', CLAUDE_YOLO='yes')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.agent_create()[-4:], [BYPASS, '-p', 'hello world', ''])
        self.log.unlink()
        result = self.run_wrapper('--container-shell', '-c', 'echo ok', CLAUDE_YOLO='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        create = self.agent_create()
        self.assertNotIn(BYPASS, create)
        self.assertIn('/bin/bash', create)
        self.assertEqual(create[-2:], ['-c', 'echo ok'])

    def test_invalid_bypass_value_stops_before_the_engine(self):
        result = self.run_wrapper('-p', 'test', CLAUDE_YOLO='maybe')
        self.assertEqual(result.returncode, 1)
        self.assertIn('CLAUDE_YOLO', result.stderr)
        self.assertFalse(any(c[0] in ('build', 'create') for c in self.calls()))

    def test_unrestricted_sessions_get_no_provider_settings_or_api_key(self):
        result = self.run_wrapper('-p', 'test', ANTHROPIC_API_KEY='host-key')
        self.assertEqual(result.returncode, 0, result.stderr)
        environment = self.environment(self.agent_create())
        self.assertNotIn('ANTHROPIC_API_KEY', environment)
        for setting in PROVIDER_ONLY:
            self.assertNotIn(setting, environment)
        self.log.unlink()
        result = self.run_wrapper('-p', 'test', ANTHROPIC_API_KEY='host-key',
                                  CLAUDE_CONTAINER_ENV_VARS='ANTHROPIC_API_KEY')
        self.assertEqual(result.returncode, 0, result.stderr)
        environment = self.environment(self.agent_create())
        self.assertIn('ANTHROPIC_API_KEY', environment)
        self.assertNotIn('host-key', ' '.join(self.agent_create()))


class ProviderTests(WrapperTests):
    """Provider sessions through a synthetic installation (argument instrumentation only)."""
    def setUp(self):
        super().setUp()
        self.wrapper = synthetic_install(self.base, ROOT, WRAPPER.name)
        self.policy = self.wrapper.parent / 'agent/policies/default.json'
        self.policy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'agent/policies/default.json', self.policy)
        self.runtime = self.base / 'runtime'
        self.runtime.mkdir(mode=0o700)

    def run_provider(self, profile, **env):
        return self.run_wrapper('-p', 'test', wrapper=self.wrapper, CLAUDE_CONTAINER_NETWORK='provider',
                                CLAUDE_CONTAINER_NETWORK_PROFILE=profile,
                                CLAUDE_CONTAINER_NETWORK_POLICY=str(self.policy),
                                CLAUDE_CONTAINER_NETWORK_RUNTIME_DIR=str(self.runtime),
                                CLAUDE_CONTAINER_EGRESS_IMAGE='sha256:' + 'e' * 64,
                                ANTHROPIC_API_KEY='host-key', FAKE_NETWORK='1', FAKE_INFO='true linux true',
                                CONTAINER_HOST='unix:///run/service.sock', **env)

    def test_api_profile_receives_the_key_and_the_provider_settings(self):
        result = self.run_provider('anthropic-api')
        self.assertEqual(result.returncode, 0, result.stderr)
        create = self.agent_create()
        environment = self.environment(create)
        self.assertIn('ANTHROPIC_API_KEY', environment)
        self.assertNotIn('host-key', ' '.join(create))
        for setting in PROVIDER_ONLY:
            self.assertIn(setting, environment)

    def test_account_profile_never_receives_the_api_key(self):
        result = self.run_provider('anthropic-account', CLAUDE_CONTAINER_ENV_VARS='ANTHROPIC_API_KEY')
        self.assertEqual(result.returncode, 0, result.stderr)
        environment = self.environment(self.agent_create())
        self.assertNotIn('ANTHROPIC_API_KEY', environment)
        self.assertIn('ANTHROPIC_API_KEY', result.stderr)
        for setting in PROVIDER_ONLY:
            self.assertIn(setting, environment)

    # The unrestricted cases of the parent class run once, there.
    test_help_documents_the_approval_bypass = None
    test_four_independent_permission_combinations = None
    test_bypass_precedes_claude_arguments_and_never_reaches_the_shell = None
    test_invalid_bypass_value_stops_before_the_engine = None
    test_unrestricted_sessions_get_no_provider_settings_or_api_key = None


if __name__ == '__main__':
    unittest.main()
