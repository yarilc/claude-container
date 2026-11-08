"""Load trusted defaults, then replace this process with the installed wrapper."""
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SetupError, load, protect_mounts, runtime_environment, trusted


def main():
    release = Path(__file__).resolve().parents[1]
    wrapper = release / 'claude-container.sh'
    args = sys.argv[1:]
    launcher = None
    if len(args) >= 2 and args[0] == '--managed-launcher':
        launcher, args = args[1], args[2:]
    if '--container-help' in args or '--container-setup' in args:
        os.execv('/bin/bash', ['bash', str(wrapper), *args])
    if not launcher:
        raise SetupError('The managed launcher needs an update; rerun --container-setup.')
    actual_launcher = trusted(Path(launcher).absolute())
    if not actual_launcher.is_file():
        raise SetupError('The invoked managed launcher must be a protected file.')
    value = load(release / 'setup.json')
    if release.parent != trusted(value['installation']) / 'releases':
        raise SetupError('Managed release does not belong to its declared installation.')
    trusted(wrapper)
    env = runtime_environment(value, release)
    protect_mounts(value, env, args, launcher=launcher)
    if value['worktree'] and '--container-qualify' not in args:
        args = ['--container-git-worktree', *args]
    os.execve('/bin/bash', ['bash', str(wrapper), *args], env)


if __name__ == '__main__':
    try:
        main()
    except (SetupError, OSError, ValueError):
        print('claude-container: invalid or unsafe managed configuration; rerun --container-setup or use a different workspace.', file=sys.stderr)
        sys.exit(1)
