# Claude Code CLI in Podman

`claude-container.sh` runs Claude Code in a rootless Podman container. The
container uses the host Podman socket, allowing Claude to launch containers for
tests and builds without running a nested daemon.

## Usage

```bash
chmod +x claude-container.sh
podman system service --time=0 unix:///run/user/$(id -u)/podman/podman.sock &
./claude-container.sh --container-build
./claude-container.sh
./claude-container.sh -p "run the tests"
./claude-container.sh --container-shell
./claude-container.sh --container-help
CLAUDE_YOLO=1 ./claude-container.sh
```

The wrapper can replace `claude` through a shell alias:

```bash
alias claude=/absolute/path/to/claude-container.sh
```

Only `--container-build`, `--container-shell`, and `--container-help` are
handled by the wrapper. Every other argument is forwarded unchanged, so normal
commands such as `claude --help` and `claude resume --last` retain their
meaning.

Each container is named from the last component of the current directory and
the next highest numeric index among running instances, for example
`my-project-0` and `my-project-1`.

`CLAUDE_YOLO=1` starts Claude with `--dangerously-skip-permissions`, disabling
all Claude permission checks. Use it only when the container and mounts are a
trusted environment.

## Mounts, identity, and persistence

The process inside the container uses `--userns=keep-id` and the caller's
UID/GID. Files created in the workspace therefore retain compatible ownership
on the host.

The current workspace is mounted at the same absolute path inside the
container. This is required because bind mounts requested by child containers
are resolved by the host Podman service.

Claude configuration defaults to `~/.claude`, or to `CLAUDE_CONFIG_DIR` when
set. It is mounted read/write at `/claude-home/.claude`, and
`CLAUDE_CONFIG_DIR` is set accordingly inside the container. This preserves
Claude settings, credentials, session history, plugins, and other persistent
state.

The container root filesystem is read-only. The workspace and Claude
configuration directory are the only persistent writable mounts; `/tmp` and
`/run` are ephemeral tmpfs mounts.

The Podman socket gives Claude control over containers and volumes available
to the host Podman user. The wrapper does not use `--privileged` and does not
mount the user's full home directory.

## Included tools

The image includes Node.js/npm, Claude Code, the Podman client, Git, Bash,
local search and editing tools, archive tools, JSON support, and diagnostics
needed to work in a repository and run tests in containers.
