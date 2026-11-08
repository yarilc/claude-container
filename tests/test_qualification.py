"""Qualification contracts and credential-free installed-path acceptance."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import io
from contextlib import redirect_stdout
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'network'))
import qualification_records as records
import qualify


class QualificationContracts(unittest.TestCase):
    def identity(self):
        return dict(mode='provider', revision=records.REVISION, runtime='a'*64, proxy='b'*64,
                    policy='c'*64, platform=dict(abi=3), code={'guard':'d'*64},
                    hardening=dict(capabilities=[], no_new_privs=True, pids=128, memory=268435456))

    def report(self):
        identity = self.identity()
        return dict(schema=1, identity=identity, fingerprint=records.digest(records.canonical(identity)),
                    checks={name:'passed' for name in records.expected_checks(True)},
                    measured_at='2026-11-07T17:00:00+00:00', reusable=True)

    def test_report_requires_complete_exact_evidence_and_hardening(self):
        report = self.report()
        records.validate_report(report, self.identity())
        for mutate in (lambda r: r['checks'].pop('ip6'), lambda r:r['checks'].update(ip4='unavailable'),
                       lambda r:r['checks'].update(ip4='skipped'), lambda r:r.update(schema=True),
                       lambda r:r.update(extra='ignored'), lambda r:r.update(fingerprint='0'*64),
                       lambda r:r['identity']['hardening'].update(memory=0),
                       lambda r:r['identity']['hardening'].update(no_new_privs=1),
                       lambda r:r.update(reusable='true')):
            value = copy.deepcopy(report); mutate(value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                records.validate_report(value, self.identity())

    def test_each_enforcement_identity_change_invalidates_evidence(self):
        report = self.report()
        for key in ('mode', 'runtime', 'proxy', 'policy', 'revision', 'platform', 'code', 'hardening'):
            changed = self.identity(); changed[key] = 'changed'
            with self.subTest(key=key), self.assertRaises(ValueError):
                records.validate_report(report, changed)
        for data in (b'{"schema":1,"schema":1}', b'{}\n{}', b'x'*65537):
            with self.assertRaises(ValueError):
                records.decode(data)

    def test_release_measured_requires_exact_protected_acceptance_entry(self):
        identity = self.identity()
        self.assertEqual(records.evidence_status(dict(schema=1, fingerprints=[]), identity), 'locally-qualified')
        value = dict(schema=1, fingerprints=[records.digest(records.canonical(identity))])
        self.assertEqual(records.evidence_status(value, identity), 'release-measured')
        changed = identity | {'runtime':'e'*64}
        self.assertEqual(records.evidence_status(value, changed), 'locally-qualified')
        for invalid in ({}, dict(schema=True, fingerprints=[]), dict(schema=1, fingerprints=['*'])):
            with self.assertRaises(ValueError):
                records.evidence_status(invalid, identity)

    def test_bounded_subprocess_group_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            pidfile = Path(temporary) / 'pid'
            script = """import os,signal,sys,time
child=os.fork()
if child:
 time.sleep(.1); sys.exit(0)
signal.signal(signal.SIGTERM,signal.SIG_IGN)
open(sys.argv[1],'w').write(str(os.getpid()))
os.close(0); os.close(1); os.close(2)
time.sleep(60)
"""
            gate = qualify.Gate(os.environ)
            gate.run([sys.executable, '-c', script, str(pidfile)], timeout=3)
            pid = int(pidfile.read_text())
            deadline = time.monotonic()+2
            while time.monotonic()<deadline:
                stat = Path(f'/proc/{pid}/stat')
                if not stat.exists() or stat.read_text().split()[2]=='Z':
                    break
                time.sleep(.02)
            else:
                os.kill(pid, signal.SIGKILL)
                self.fail('owned descendant survived group cleanup')
            started = time.monotonic()
            with self.assertRaises(subprocess.TimeoutExpired):
                gate.run([sys.executable, '-c',
                    'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)'],
                    timeout=.2)
            self.assertLess(time.monotonic() - started, 5)
            self.assertIsNone(gate.process)

    def test_unknown_policy_requalifies_and_changed_inputs_cannot_publish(self):
        identity=self.identity()
        for changed in (False, True):
            gate=unittest.mock.Mock()
            snapshots=[(identity,False),(identity | {'runtime':'changed'} if changed else identity,False)]
            with tempfile.TemporaryDirectory() as temporary, patch.object(qualify,'ROOT',Path(temporary)), \
                    patch.object(qualify,'trusted_path',side_effect=lambda path,*a,**k:Path(path)), \
                    patch.object(qualify,'Gate',return_value=gate), patch.object(qualify.records,'CODE',()), \
                    patch.object(qualify.records,'fingerprint',side_effect=snapshots), \
                    patch.object(qualify.records,'read',return_value={'reusable':False}), \
                    patch.object(qualify.records,'publish') as publish, \
                    patch.object(qualify.records,'status',return_value='locally-qualified'), \
                    patch.object(sys,'argv',['qualify.py','check']), \
                    patch.dict(os.environ,{'CONTAINER_HOST':'unix:///some/socket','CLAUDE_CONTAINER_NETWORK':'offline'},clear=True):
                if changed:
                    with self.assertRaisesRegex(qualify.GateError,'changed'):
                        qualify.main()
                    publish.assert_not_called()
                else:
                    with redirect_stdout(io.StringIO()) as output:
                        qualify.main()
                    self.assertEqual(output.getvalue(),'')
                    publish.assert_called_once()
                gate.qualify.assert_called_once_with(identity)
                self.assertTrue(gate.cleanup.called)

    def test_failed_control_cannot_publish_a_success_report(self):
        gate=unittest.mock.Mock()
        gate.qualify.side_effect=qualify.GateError('positive control unavailable')
        with tempfile.TemporaryDirectory() as temporary, patch.object(qualify,'ROOT',Path(temporary)), \
                patch.object(qualify,'trusted_path',side_effect=lambda path,*a,**k:Path(path)), \
                patch.object(qualify,'Gate',return_value=gate), patch.object(qualify.records,'CODE',()), \
                patch.object(qualify.records,'fingerprint',return_value=(self.identity(),True)), \
                patch.object(qualify.records,'publish') as publish, \
                patch.object(sys,'argv',['qualify.py','qualify']), \
                patch.dict(os.environ,{'CONTAINER_HOST':'unix:///some/socket','CLAUDE_CONTAINER_NETWORK':'offline'},clear=True):
            with self.assertRaisesRegex(qualify.GateError,'unavailable'):
                qualify.main()
            publish.assert_not_called()
            self.assertTrue(gate.cleanup.called)
            gate.qualify.side_effect = None
            gate.cleanup.side_effect = [None, qualify.GateError('cleanup unavailable')]
            with self.assertRaisesRegex(qualify.GateError, 'cleanup unavailable'):
                qualify.main()
            publish.assert_not_called()


@unittest.skipUnless(os.environ.get('CLAUDE_RUNTIME_TESTS') == '1', 'requires disposable native rootless harness')
class QualificationRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guard = tempfile.TemporaryDirectory(prefix='qualification-guard-', dir=os.environ['CLAUDE_TEST_STATE_ROOT'])
        cls.addClassCleanup(cls.guard.cleanup)
        result = subprocess.run(['bash', str(ROOT/'network/build-guard.sh'), cls.guard.name],
            env=os.environ | {'CLAUDE_CONTAINER_MAINTENANCE':'1'}, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError(result.stderr)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='qualification-', dir=os.environ['CLAUDE_TEST_STATE_ROOT'])
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name)
        self.install = self.base/'installed'; self.install.mkdir(mode=0o700)
        (self.install/'network').mkdir(mode=0o700)
        shutil.copyfile(ROOT/'claude-container.sh', self.install/'claude-container.sh')
        for source in (ROOT/'network').glob('*.py'):
            shutil.copyfile(source, self.install/'network'/source.name)
        shutil.copyfile(ROOT/'network/resolv.conf', self.install/'network/resolv.conf')
        shutil.copytree(self.guard.name, self.install/'network/bin')
        self.project=self.base/'project'; self.project.mkdir()
        self.home=self.base/'home'; self.home.mkdir(mode=0o700)
        self.runtime=self.base/'egress'; self.runtime.mkdir(mode=0o700)
        self.env=dict(PATH=os.environ['PATH'], HOME=str(self.home),
            CONTAINER_HOST=os.environ['CONTAINER_HOST'], CLAUDE_CONTAINER_NETWORK='offline',
            CLAUDE_CONTAINER_STATE_DIR=str(self.base/'state'),
            CLAUDE_CONTAINER_NETWORK_RUNTIME_DIR=str(self.runtime),
            CLAUDE_CONTAINER_IMAGE=os.environ.get('CLAUDE_CONTAINER_IMAGE','localhost/claude-code:latest'))

    def command(self, *args, input=None, timeout=325):
        return subprocess.run(['bash', str(self.install/'claude-container.sh'), *args],
            cwd=self.project, env=self.env, input=input, capture_output=True, text=True, timeout=timeout)

    def test_installed_offline_qualification_missing_stale_and_unsafe_reports(self):
        result=self.command('--container-shell', input='touch agent-started\n')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('qualification',result.stderr)
        self.assertFalse((self.project/'agent-started').exists())
        result=self.command('--container-qualify')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('CLAUDE_QUALIFICATION_OK',result.stdout)
        paths=list((self.install/'qualification').glob('*.json'))
        self.assertEqual(len(paths),1)
        report=json.loads(paths[0].read_text())
        self.assertEqual(report['identity']['hardening']['memory'],268435456)
        result=self.command('--container-shell',input='printf qualified-startup-ok\n')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('qualified-startup-ok',result.stdout)
        helper=self.install/'network/platform_check.py'
        helper.chmod(0o666)
        result=self.command('--container-shell',input='touch agent-started\n')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('network policy preflight failed',result.stderr)
        helper.chmod(0o644)
        paths[0].chmod(0o644)
        self.assertNotEqual(self.command('--container-shell',input='touch agent-started\n').returncode,0)
        paths[0].chmod(0o600)
        code=self.install/'network/qualification_probe.py'
        code.write_text(code.read_text()+'\n# changed enforcement fixture\n')
        self.assertNotEqual(self.command('--container-shell',input='touch agent-started\n').returncode,0)
        self.assertFalse((self.project/'agent-started').exists())

    def test_installed_provider_qualification_and_fixed_probe_cannot_run_application(self):
        image=subprocess.check_output(['podman','image','inspect','--format','{{.Id}}',
            'localhost/claude-egress:tls-binding-candidate'],text=True).strip()
        policy=self.install/'policy.json'; shutil.copyfile(ROOT/'network/policies/default.json',policy)
        self.env.update(CLAUDE_CONTAINER_NETWORK='provider',CLAUDE_CONTAINER_NETWORK_PROFILE='anthropic-account',
            CLAUDE_CONTAINER_NETWORK_POLICY=str(policy),CLAUDE_CONTAINER_EGRESS_IMAGE=image)
        result=self.command('--container-qualify')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        report=json.loads(next((self.install/'qualification').glob('*.json')).read_text())
        self.assertEqual(report['checks']['tls-mismatch-zero-bytes'],'passed')
        self.assertEqual(report['checks']['proxy-loss'],'passed')
        for args in (('--container-qualify','--container-shell'), ('--container-qualify-probe','touch','agent-started')):
            self.assertNotEqual(self.command(*args).returncode,0)
        result=self.command('--container-qualify-probe')
        self.assertNotEqual(result.returncode,0)
        self.assertFalse((self.project/'agent-started').exists())
        data=dict(schema=1,token='a'*32,workspace=str(self.project),addresses=['127.0.0.1','::1'],provider=True,tls=False)
        path=self.install/'bad-input.json'
        path.write_text(json.dumps(data | {'command':'touch agent-started'}))
        self.env['CLAUDE_CONTAINER_QUALIFICATION_INPUT']=str(path)
        self.assertNotEqual(self.command('--container-qualify-probe').returncode,0)
        path=self.project/'writable-input.json'; path.write_text(json.dumps(data))
        self.env['CLAUDE_CONTAINER_QUALIFICATION_INPUT']=str(path)
        self.assertNotEqual(self.command('--container-qualify-probe').returncode,0)
        self.assertFalse((self.project/'agent-started').exists())

    def test_ordinary_report_check_interruption_preserves_shutdown_budget(self):
        engine=shutil.which('podman')
        directory=self.base/'shim'; directory.mkdir()
        marker=self.base/'check-started'; counter=self.base/'host-query'
        script=directory/'podman'
        script.write_text("""#!/usr/bin/env python3
import os,pathlib,signal,sys,time
args=sys.argv[1:]
if args and args[0]=='info' and args[-1]=='{{json .Host}}':
 p=pathlib.Path(os.environ['QUALIFY_COUNTER'])
 if p.exists():
  signal.signal(signal.SIGTERM,signal.SIG_IGN)
  pathlib.Path(os.environ['QUALIFY_MARKER']).write_text(str(os.getpid()))
  time.sleep(300)
 p.touch()
os.execv(os.environ['QUALIFY_ENGINE'],[os.environ['QUALIFY_ENGINE'],*args])
""")
        script.chmod(0o700)
        env=self.env | dict(PATH=str(directory)+':'+self.env['PATH'], QUALIFY_ENGINE=engine,
                           QUALIFY_MARKER=str(marker),QUALIFY_COUNTER=str(counter))
        process=subprocess.Popen(['bash',str(self.install/'claude-container.sh'),'--container-shell'],
            env=env,cwd=self.project,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            deadline=time.monotonic()+20
            while not marker.exists() and process.poll() is None and time.monotonic()<deadline:
                time.sleep(.02)
            self.assertTrue(marker.exists(),'ordinary check did not reach metadata inspection')
            started=time.monotonic(); process.terminate()
            stdout,stderr=process.communicate('touch agent-started\n',timeout=23)
            self.assertEqual(process.returncode,143,stdout+stderr)
            self.assertLess(time.monotonic()-started,21)
            self.assertFalse((self.project/'agent-started').exists())
            pid=int(marker.read_text())
            stat=Path(f'/proc/{pid}/stat')
            self.assertTrue(not stat.exists() or stat.read_text().split()[2]=='Z')
        finally:
            if process.poll() is None:
                process.kill(); process.communicate()

    def test_cancelled_gate_has_no_report_and_cleans_only_its_resources(self):
        process=subprocess.Popen(['bash',str(self.install/'claude-container.sh'),'--container-qualify'],
            cwd=self.project,env=self.env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            deadline=time.monotonic()+30
            configs=[]
            while not configs and process.poll() is None and time.monotonic()<deadline:
                configs=list(self.base.glob('.claude-qualification-*/shared/input.json'))
                time.sleep(.02)
            self.assertTrue(configs, 'gate did not reach owned fixture setup')
            token=json.loads(configs[0].read_text())['token']
            process.terminate()
            stdout,stderr=process.communicate(timeout=40)
            self.assertNotEqual(process.returncode,0,stdout+stderr)
            self.assertEqual(list((self.install/'qualification').glob('*.json')),[])
            result=subprocess.check_output(['podman','ps','--all','--filter',
                'label=io.claude-container.qualification='+token,'--format','{{.ID}}'],text=True).strip()
            self.assertEqual(result,'')
            self.assertEqual(list(self.base.glob('.claude-qualification-*')),[])
        finally:
            if process.poll() is None:
                process.kill(); process.communicate()

    def test_cancelled_tls_gate_is_bounded_and_cleans_owned_resources(self):
        image=subprocess.check_output(['podman','image','inspect','--format','{{.Id}}',
            'localhost/claude-egress:tls-binding-candidate'],text=True).strip()
        policy=self.install/'policy.json'; shutil.copyfile(ROOT/'network/policies/default.json',policy)
        self.env.update(CLAUDE_CONTAINER_NETWORK='provider',CLAUDE_CONTAINER_NETWORK_PROFILE='anthropic-account',
            CLAUDE_CONTAINER_NETWORK_POLICY=str(policy),CLAUDE_CONTAINER_EGRESS_IMAGE=image)
        # Instrument only this disposable installed fixture to hold the TLS
        # subprocess open after actual matching/mismatching handshake checks.
        probe=self.install/'network/qualification_probe.py'
        source=probe.read_text()
        source=source.replace("    print('qualification-proxy-loss-ready', flush=True)",
            "    Path('/workspace/cancel-tls-ready').touch()\n    __import__('time').sleep(60)\n"
            "    print('qualification-proxy-loss-ready', flush=True)")
        probe.write_text(source)
        process=subprocess.Popen(['bash',str(self.install/'claude-container.sh'),'--container-qualify'],
            cwd=self.project,env=self.env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            deadline=time.monotonic()+100; markers=[]
            while not markers and process.poll() is None and time.monotonic()<deadline:
                markers=list(self.base.glob('.claude-qualification-*/tls/project/cancel-tls-ready'))
                time.sleep(.02)
            self.assertTrue(markers,'gate did not reach controlled TLS stage')
            config=markers[0].parents[1]/'input.json'
            token=json.loads(config.read_text())['token']
            started=time.monotonic(); process.terminate()
            stdout,stderr=process.communicate(timeout=18)
            self.assertNotEqual(process.returncode,0,stdout+stderr)
            self.assertLess(time.monotonic()-started,15)
            self.assertEqual(list((self.install/'qualification').glob('*.json')),[])
            owned=subprocess.check_output(['podman','ps','--all','--filter',
                'label=io.claude-container.qualification='+token,'--format','{{.ID}}'],text=True).strip()
            self.assertEqual(owned,'')
            self.assertEqual(list(self.base.glob('.claude-qualification-*')),[])
        finally:
            if process.poll() is None:
                process.kill(); process.communicate()

    def test_concurrent_gates_publish_complete_atomic_reports(self):
        children=[subprocess.Popen(['bash',str(self.install/'claude-container.sh'),'--container-qualify'],
            cwd=self.project,env=self.env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            for _ in range(2)]
        try:
            for child in children:
                stdout,stderr=child.communicate(timeout=325)
                self.assertEqual(child.returncode,0,stdout+stderr)
            reports=list((self.install/'qualification').glob('*.json'))
            self.assertEqual(len(reports),1)
            value=json.loads(reports[0].read_text())
            records.validate_report(value,value['identity'])
            self.assertEqual(list(self.base.glob('.claude-qualification-*')),[])
        finally:
            for child in children:
                if child.poll() is None:
                    child.terminate(); child.communicate(timeout=40)

    def test_record_publication_is_atomic_and_refuses_unsafe_paths(self):
        identity=QualificationContracts().identity()
        records.publish(self.install,identity,True,[])
        path=next((self.install/'qualification').glob('*.json'))
        old=path.read_bytes()
        with patch.object(records.os,'replace',side_effect=OSError('synthetic publication failure')):
            with self.assertRaises(OSError):
                records.publish(self.install,identity,True,[])
        self.assertEqual(path.read_bytes(),old)
        self.assertEqual(list(path.parent.glob('.qualification-*')),[])
        saved=path.parent/'saved'; path.rename(saved); path.symlink_to(saved.name)
        with self.assertRaises(ValueError):
            records.read(self.install,identity,[])
        path.unlink(); saved.rename(path); path.chmod(0o644)
        with self.assertRaises(ValueError):
            records.publish(self.install,identity,True,[])
        self.assertEqual(path.stat().st_mode & 0o777,0o644)
