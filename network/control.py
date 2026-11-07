"""Host-side restricted-network preflight and immutable snapshot creation."""
import argparse
import hashlib
import stat
import json
import os
from pathlib import Path
import re
import sys

# Isolated Python ignores PYTHONPATH and the script directory. Only import
# helpers from the installation selected by this script's physical location.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from policy import PolicyError, canonical, load, overlaps, revision, selected, trusted_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=('preflight', 'snapshot'))
    parser.add_argument('--installation', required=True)
    parser.add_argument('--writable', action='append', default=[])
    parser.add_argument('--mount-target', action='append', default=[])
    parser.add_argument('--policy')
    parser.add_argument('--profile')
    parser.add_argument('--proxy-image')
    parser.add_argument('--runtime')
    parser.add_argument('--session')
    args = parser.parse_args()
    for writable in args.writable:
        resolved = Path(writable).resolve()
        if any(resolved == Path(root) or Path(root) in resolved.parents for root in ('/proc', '/sys', '/dev')):
            raise PolicyError('host process, namespace and device trees cannot be restricted workspace/state binds')
    installation = trusted_path(args.installation, args.writable, directory=True)
    for name in ('claude-container.sh', 'network/control.py', 'network/policy.py', 'network/relay.py', 'network/mux.py', 'network/resolv.conf'):
        trusted_path(installation / name, args.writable)
    for target in args.mount_target:
        target = Path(target)
        if not target.is_absolute() or '..' in target.parts:
            raise PolicyError('invalid effective mount target')
        if any(overlaps(target, Path(root)) for root in ('/tmp', '/run', '/var/tmp')):
            raise PolicyError('host bind overlaps a reserved private IPC hierarchy')
    guard = trusted_path(installation / 'network/bin/claude-egress-guard', args.writable)
    manifest = trusted_path(installation / 'network/bin/claude-egress-guard.sha256', args.writable)
    identity = hashlib.sha256(guard.read_bytes()).hexdigest()
    if manifest.read_text() != identity + '  claude-egress-guard\n':
        raise PolicyError('native bootstrap digest mismatch')
    if not guard.stat().st_mode & stat.S_IXUSR or guard.read_bytes()[:6] != b'\x7fELF\x02\x01':
        raise PolicyError('native bootstrap must be an executable static x86_64 ELF')
    # ELF64 little-endian native x86_64, no interpreter or dynamic segment.
    import struct
    data = guard.read_bytes()
    if len(data) < 64 or struct.unpack_from('<H', data, 18)[0] != 62:
        raise PolicyError('native bootstrap architecture mismatch')
    offset = struct.unpack_from('<Q', data, 32)[0]
    size, count = struct.unpack_from('<HH', data, 54)
    if size != 56 or offset + size * count > len(data):
        raise PolicyError('native bootstrap ELF layout invalid')
    if any(struct.unpack_from('<I', data, offset + i * size)[0] in (2, 3) for i in range(count)):
        raise PolicyError('native bootstrap must not have dynamic loading or an interpreter')
    guard_identity = {'sha256': identity, 'revision': 'abi3-seccomp-mux-v1',
                      'required_abi': 3, 'filter': 'native-x86_64-v1', 'protocol': 1}
    if not args.policy:
        return
    policy_path = trusted_path(args.policy, args.writable)
    value = load(policy_path)
    selected(value, args.profile)
    if not re.fullmatch(r'(?:(?:sha256:)?[a-f0-9]{64}|[A-Za-z0-9./:_-]+@sha256:[a-f0-9]{64})', args.proxy_image or ''):
        raise PolicyError('CLAUDE_CONTAINER_EGRESS_IMAGE must be an immutable image ID or digest')
    runtime = trusted_path(args.runtime or '', args.writable, directory=True)
    info = runtime.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise PolicyError('network runtime directory must be caller owned and mode 0700')
    if args.operation == 'snapshot':
        session = Path(args.session).resolve(strict=True)
        if session.parent != runtime or session.stat().st_uid != os.getuid() or session.stat().st_mode & 0o077:
            raise PolicyError('invalid private network session directory')
        for name in ('config', 'transport', 'logs'):
            (session / name).mkdir(mode=0o700)
        with (session / 'config/policy.json').open('xb') as output:
            output.write(canonical(value))
        (session / 'config/policy.json').chmod(0o400)
        (session / 'config/manifest.json').write_text(json.dumps(guard_identity | {
            'policy': revision(value), 'profile': args.profile, 'session': session.name}, sort_keys=True) + '\n')
        (session / 'config/manifest.json').chmod(0o400)
        # No external DNS from the agent. Own hosts entries remain usable.
        (session / 'resolv.conf').write_text('nameserver 127.0.0.1\noptions attempts:1 timeout:1\n')
        (session / 'resolv.conf').chmod(0o400)
        print(revision(value))


if __name__ == '__main__':
    try:
        main()
    except (PolicyError, OSError, ValueError) as error:
        # Paths can be operator supplied; never echo policy/request contents.
        print('claude-container: network policy preflight failed: ' +
              (str(error) if isinstance(error, PolicyError) else 'input inaccessible or invalid'), file=sys.stderr)
        sys.exit(1)
