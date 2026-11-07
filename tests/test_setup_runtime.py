"""Opt-in real WSL setup acceptance; no credentials or user-service mutations."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from test_setup import pty_run

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get('CLAUDE_RUNTIME_TESTS') == '1', 'requires real rootless WSL engine')
class SetupRuntime(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='setup-acceptance-', dir=os.environ['CLAUDE_TEST_STATE_ROOT'])
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.home = self.base / 'home'
        self.home.mkdir(mode=0o700)
        self.workspace = self.base / 'workspace with spaces'
        self.workspace.mkdir()
        self.root = self.base / 'installation'
        self.command = self.base / 'bin/claude-container'
        self.env = {'PATH': os.environ['PATH'], 'HOME': str(self.home),
                    'CONTAINER_HOST': os.environ['CONTAINER_HOST']}
        self.tags = set()
        self.addCleanup(self.clean_tags)

    def clean_tags(self):
        for path in self.root.glob('releases/*/setup.json'):
            self.tags.add(json.loads(path.read_text())['image'])
        for tag in self.tags:
            subprocess.run(['podman', 'image', 'rm', tag], capture_output=True, timeout=30)

    def answers(self, mode, ca=False):
        answers = [('Protected native installation directory', str(self.root)), ('Network mode', mode)]
        if mode != 'offline':
            answers += [('Authentication method', 'account')]
        answers += [('State mode', 'isolated'), ('Private isolated state directory', str(self.base / 'state')),
                    ('Delegate the host Podman API', 'no'), ('Enable Claude permission bypass', 'no'),
                    ('Use parent-directory worktree scope', 'no'), ('Trust a host CA bundle', 'yes' if ca else 'no')]
        if ca:
            answers += [('CA bundle file', '/etc/ssl/certs/ca-certificates.crt')]
        answers += [('Managed launch command path', str(self.command)),
                    ('Podman launch endpoint', self.env['CONTAINER_HOST'])]
        if mode == 'provider':
            answers += [('Private native egress runtime directory', str(self.base / 'egress'))]
        answers += [('Refresh prepared images', 'no'), ('Apply this installation', 'yes')]
        return answers

    def setup_run(self, mode, source=ROOT, login_prompt=True, ca=False):
        answers = self.answers(mode, ca=ca)
        if mode != 'offline' and login_prompt:
            answers += [('Run Claude account login now?', 'no')]
        return pty_run(['bash', str(source / 'claude-container.sh'), '--container-setup'],
                       self.env, self.workspace, answers, timeout=180)

    def test_fresh_provider_new_terminal_rerun_offline_and_failed_update(self):
        # Regression: a caller-owned 0755 root from manual installation is
        # protected but not private. Preserve it without chmod or replacement.
        self.root.mkdir(mode=0o755)
        manual = self.root / 'manual-install-marker'
        manual.write_text('preserve existing installation')
        code, output = self.setup_run('provider', ca=True)
        self.assertEqual(code, 0, output)
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o755)
        self.assertEqual(manual.read_text(), 'preserve existing installation')
        self.assertIn('Sandbox: ready', output)
        self.assertIn('Authentication: pending', output)
        release = (self.root / 'current').resolve()
        first = json.loads((release / 'setup.json').read_text())
        self.tags.add(first['image'])
        self.assertEqual(first['network'], 'provider')
        guard = (release / 'network/bin/claude-egress-guard').read_bytes()
        # No exported wrapper/network settings in this fresh launch environment.
        result = subprocess.run([str(self.command), '--version'], cwd=self.workspace,
                                env={'PATH': self.env['PATH'], 'HOME': self.env['HOME']},
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Claude Code', result.stdout)
        self.assertIn('enforced revision=abi3-seccomp-mux-v1', result.stderr)
        self.assertRegex(result.stderr, r'(INFO\[\d+\] Should restart: false|level=info msg="Should restart: false")')
        self.assertNotRegex(result.stderr, r'ERRO\[\d+\] Should restart: false')
        self.assertNotIn('level=error msg="Should restart: false"', result.stderr)
        code, output = self.setup_run('provider')
        self.assertEqual(code, 0, output)
        second = (self.root / 'current').resolve()
        self.assertNotEqual(release, second)
        self.assertEqual((second / 'network/bin/claude-egress-guard').read_bytes(), guard)
        self.assertNotIn('Packaged guard', output)
        self.assertTrue(release.exists())
        code, output = self.setup_run('offline')
        self.assertEqual(code, 0, output)
        self.assertIn('Authentication: not applicable', output)
        active = (self.root / 'current').resolve()
        self.assertEqual((active / 'network/bin/claude-egress-guard').read_bytes(), guard)
        # A reviewed update with an intentionally failing smoke must not activate.
        source = self.base / 'failed-source'
        shutil.copytree(active, source)
        (source / 'setup/smoke.py').write_text('import sys\nsys.exit(42)\n')
        before = set(self.root.joinpath('releases').iterdir())
        code, output = self.setup_run('offline', source=source)
        self.assertNotEqual(code, 0, output)
        self.assertEqual((self.root / 'current').resolve(), active)
        self.assertEqual(set(self.root.joinpath('releases').iterdir()), before)
        self.assertFalse((self.root / '.setup.lock').exists())
        # Capture only setup-owned tags from failure reporting for cleanup.
        for line in output.splitlines():
            if 'Prepared runtime image tag: ' in line:
                self.tags.add(line.split('Prepared runtime image tag: ', 1)[1].strip())

    def test_unrestricted_fresh_setup_and_shell(self):
        code, output = self.setup_run('unrestricted')
        self.assertEqual(code, 0, output)
        release = (self.root / 'current').resolve()
        self.assertFalse((release / 'network/bin').exists())
        result = subprocess.run([str(self.command), '--container-shell'], cwd=self.workspace,
                                env={'PATH': self.env['PATH'], 'HOME': self.env['HOME']},
                                input='printf SETUP_SHELL_OK\n', capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('SETUP_SHELL_OK', result.stdout)
        # Move the managed command through the actual wizard, then verify that
        # no obsolete host entry point is left behind in the former workspace.
        previous_command = self.command
        self.command = self.base / 'relocated-bin/claude-container'
        code, output = self.setup_run('unrestricted')
        self.assertEqual(code, 0, output)
        self.assertFalse(previous_command.exists())
        result = subprocess.run([str(self.command), '--version'], cwd=previous_command.parent,
                                env={'PATH': self.env['PATH'], 'HOME': self.env['HOME']},
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Claude Code', result.stdout)
