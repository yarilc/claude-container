# Claude Code CLI in Podman

`claude-container.sh` runs Claude Code in a rootless Podman container. Access
from the container to the host Podman API is disabled by default. Set
`CLAUDE_CONTAINER_PODMAN=1` to let Claude launch containers for tests and builds
through the host socket without running a nested daemon.

## Enable rootless Podman on the host

Run this setup on the Linux host (or inside your Linux/WSL distribution),
using the same non-root account that will run `claude-container.sh`.
Install Podman and its rootless dependencies using your distribution's
[installation instructions](https://podman.io/docs/installation).
The account needs subordinate UID/GID ranges in `/etc/subuid` and
`/etc/subgid`, the `newuidmap`/`newgidmap` helpers, and a rootless networking
backend supported by the installed Podman version. If these are missing,
complete the administrator steps in the
[rootless setup guide](https://github.com/podman-container-tools/podman/blob/main/docs/tutorials/rootless_tutorial.md)
before continuing.

Check that local rootless Podman works:

```bash
podman info --format '{{.Host.Security.Rootless}}'
podman run --rm docker.io/library/alpine:latest id
```

The first command must print `true`; the second must successfully start a
container. Root inside that container is normal for rootless Podman.

## Optional: enable the host Podman API

This setup is required only when launching with `CLAUDE_CONTAINER_PODMAN=1`.
For ordinary sessions, skip to Usage; host Podman is still required to build
images and launch the outer container, but its API socket is not required.

When access is enabled, the wrapper requires the host API socket at exactly
`/run/user/$(id -u)/podman/podman.sock`. It does not use a custom
`XDG_RUNTIME_DIR` to locate it. Choose **one** of the following methods.

### With a systemd user session

From a normal login session for your account, enable socket activation:

```bash
systemctl --user enable --now podman.socket
systemctl --user status podman.socket --no-pager
```

Systemd creates the socket and its parent directory, and starts the API
service when a client connects. An inactive `podman.service` between requests
is normal. To keep the user service available after logout and start it at
boot, optionally enable lingering:

```bash
sudo loginctl enable-linger "$(id -un)"
```

If `systemctl --user` reports that it cannot connect to the bus, ensure you
are logged in directly as the intended user with a working systemd user
session. On systems without systemd, use the manual procedure below.

### Without systemd: create the directories and start the service

An error such as
`bind: no such file or directory` when creating the socket means that a
parent directory is missing. The socket file itself is created by Podman;
do not create it with `touch`.

In a terminal on the host, prepare the runtime directory. On systems without
a login manager, `/run/user/<uid>` may also be absent; creating it under
`/run` usually requires administrator privileges:

```bash
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
if [ ! -d "$XDG_RUNTIME_DIR" ]; then
    sudo install -d -m 0700 -o "$(id -u)" -g "$(id -g)" "$XDG_RUNTIME_DIR"
fi
ls -ld "$XDG_RUNTIME_DIR"
```

The directory must belong to your account and have mode `0700`
(`drwx------`). If an existing directory has incorrect ownership or
permissions, have the administrator correct it before continuing. Then run
the following as your normal user:

```bash
install -d -m 0700 "$XDG_RUNTIME_DIR/podman"
podman system service --time=0 "unix://$XDG_RUNTIME_DIR/podman/podman.sock"
```

Leave this terminal open and use a second terminal for the checks and wrapper
commands below. The service runs in the foreground; Ctrl+C stops it.
Repeat this setup after reboot because `/run` is temporary. Export the same
`XDG_RUNTIME_DIR` in any other terminal used to run local Podman if your
session does not set it automatically. Run the service and wrapper without
`sudo` so they use your rootless containers and configuration.

### Verify the socket before starting an enabled session

For either method, run these commands as the same user in the terminal where
you will launch the wrapper:

```bash
test -S "/run/user/$(id -u)/podman/podman.sock" && echo "Socket exists"
podman --remote --url "unix:///run/user/$(id -u)/podman/podman.sock" info --format '{{.Host.Security.Rootless}}'
```

Continue only if the socket exists and the API command succeeds and prints
`true`. With `CLAUDE_CONTAINER_PODMAN=1`, the wrapper enforces this check through
that exact socket before image operations or container startup. A socket file
alone does not prove that a service is listening or that its engine is rootless.
If the API command fails, check the systemd status or foreground service output
above and your account's permission to access the socket. If it prints `false`
or another unexpected result, verify that the service was started as the intended
non-root user, without `sudo`, and repeat the rootless service setup above.
See also the official
[Podman API service documentation](https://docs.podman.io/en/latest/markdown/podman-system-service.1.html).

## Usage

After completing the rootless host Podman setup, run from the
repository directory:

```bash
chmod +x claude-container.sh
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

The wrapper handles `--container-build`, `--container-shell`,
`--container-git-worktree`, and `--container-help`. Every other argument is
forwarded unchanged, so normal commands such as `claude --help` and
`claude resume --last` retain their meaning.

Each container is named from the last component of the current directory and
the next highest numeric index among running instances, for example
`my-project-0` and `my-project-1`.

`CLAUDE_YOLO=1` starts Claude with `--dangerously-skip-permissions`, disabling
all Claude permission checks. Use it only when the container and mounts are a
trusted environment.

### Allowing Podman access inside the container

To grant a session access to the host Podman API, complete the optional socket
setup and verification above, then run:

```bash
CLAUDE_CONTAINER_PODMAN=1 ./claude-container.sh
CLAUDE_CONTAINER_PODMAN=1 ./claude-container.sh --container-shell
```

Only the exact value `1` enables access. An unset or empty variable, `0`,
`true`, `yes`, and every other value disable access without an error. When
disabled, the wrapper skips socket validation and service queries, does not mount
the host socket, and does not set `CONTAINER_HOST` inside the container. When enabled, it mounts
the socket at `/run/podman/podman.sock` and sets
`CONTAINER_HOST=unix:///run/podman/podman.sock` in both Claude and shell modes.
A missing or invalid socket stops an enabled launch with setup instructions.
The wrapper also queries the exposed service and accepts only a successful
`true` rootless result. An unreachable service, rootful engine, or unexpected
result stops the launch before any image check, build, or container startup.

Migration: earlier versions always exposed the host Podman socket. Existing
workflows that launch child containers must now set `CLAUDE_CONTAINER_PODMAN=1`.
The Podman client remains installed in the image. This switch controls the
host API access supplied by the wrapper; it does not block independently
configured remote endpoints or sockets exposed through other selected mounts.

### Using Git worktrees

When a worktree's shared Git metadata and sibling worktrees are in its parent
directory, run the wrapper from the worktree root with
`--container-git-worktree`:

```bash
cd /path/to/root/main
claude --container-git-worktree
claude --container-git-worktree --container-shell
```

Here `claude` is the alias shown above. The option mounts `/path/to/root` at
`/path/to/root` read/write, while Claude starts in `/path/to/root/main`.
Because the parent and its contents are writable, sibling worktrees and other
files beneath it are accessible too. Git metadata referenced outside that
parent is not exposed by this option.

The wrapper mounts the immediate parent of the physical directory from which
it is launched; it does not search for a Git or worktree root. For example,
launching from `/path/to/root/main/src` mounts `/path/to/root/main`. Use the
flag from the worktree root when the shared metadata is in the common parent.

### Trusting a host CA

Host CA trust is disabled by default. To trust a CA bundle from the host, for
example a corporate TLS proxy certificate, set:

```bash
CLAUDE_CONTAINER_TRUST_HOST_CA=1 ./claude-container.sh
```

`CLAUDE_CONTAINER_TRUST_HOST_CA` accepts `1`, `true`, or `yes`; `0`, `false`, or
`no` (or an empty value) disable it, and any other value stops the wrapper with
an error.

When enabled, the bundle is mounted read-only at `/claude-home/ca/bundle.pem`,
and `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE`, and
`NODE_EXTRA_CA_CERTS` point at it. `NODE_EXTRA_CA_CERTS` is what makes Claude
Code trust the bundle, because Node.js ignores `SSL_CERT_FILE`. The image's own
certificates are not replaced.

The bundle is chosen with `CLAUDE_CONTAINER_CA_BUNDLE`. When it is unset, the
wrapper uses the first existing file among `/etc/ssl/certs/ca-certificates.crt`
(Debian and Ubuntu) and `/etc/pki/tls/certs/ca-bundle.crt` (Fedora and RHEL).
If `CLAUDE_CONTAINER_CA_BUNDLE` names a missing file, or neither default exists,
the wrapper stops before starting the container.

```bash
CLAUDE_CONTAINER_TRUST_HOST_CA=1 CLAUDE_CONTAINER_CA_BUNDLE=/path/to/ca.pem ./claude-container.sh
```

Migration: earlier versions always mounted the host certificate directory and
set CA variables. Those sessions no longer trust the host CA by default. Set
`CLAUDE_CONTAINER_TRUST_HOST_CA=1` to restore that behavior.

## Mounts, identity, and persistence

The process inside the container uses `--userns=keep-id` and the caller's
UID/GID. Files created in the workspace therefore retain compatible ownership
on the host.

By default, the current workspace is mounted read/write at the same absolute
path inside the container. With `--container-git-worktree`, the wrapper mounts
the immediate parent of the current directory at that same absolute path
instead; the container's working directory remains the original current
directory. Preserving absolute paths is required because bind mounts requested
by child containers are resolved by the host Podman service.

Claude configuration defaults to `~/.claude`, or to `CLAUDE_CONFIG_DIR` when
set. It is mounted read/write at `/claude-home/.claude`, and
`CLAUDE_CONFIG_DIR` is set accordingly inside the container. This preserves
Claude settings, credentials, session history, plugins, and other persistent
state.

The container root filesystem is read-only. The selected workspace mount and
Claude configuration directory are writable persistent mounts. The existing
OpenSpec configuration path is also mounted read/write; `/tmp` and `/run` are
ephemeral tmpfs mounts.

With `CLAUDE_CONTAINER_PODMAN=1`, the Podman socket gives Claude control over
containers and volumes available to the host Podman user. The wrapper does
not use `--privileged`. By default,
it does not mount the user's full home directory. With
`--container-git-worktree`, the selected parent can be the home directory, and
all files beneath that parent are writable through the workspace mount. Use
the option from a directory whose parent you intend to expose.

## Included tools

The image includes Node.js/npm, Claude Code, Python 3, Bubblewrap (`bwrap`), the
Podman client, Git, Bash, local search and editing tools, archive tools, JSON
support, and diagnostics needed to work in a repository and run tests in
containers.

The image includes the `nano` editor, and `EDITOR` and `VISUAL` are set to
`nano`, so commands that open an editor, such as `/memory`, work inside the
container. The host's `EDITOR` and `VISUAL` are not forwarded.
