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

The host also needs GNU coreutils, including GNU `timeout` with kill-after
support. The wrapper checks this prerequisite before session operations;
`--container-help` remains usable without it.

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

Every session verifies that its launch engine is Linux and rootless before
image inspection, build, or launch. Local Podman needs no API service when
delegation is disabled. An explicit same-host Unix `CONTAINER_HOST` is also
supported, including when this wrapper runs inside another container; launch
verification then queries that service even without delegating it to Claude.
Named `CONTAINER_CONNECTION` contexts, implicit remote contexts, TCP/SSH,
Podman Machine, and rootful engines are unsupported. All bind sources and build
paths must exist on the same Linux host at their original absolute paths.
Unix transport alone does not prove that a forwarded service is on that host.
Launch-engine and enabled delegation verification each require exactly one
response record, with no terminator or one final LF. Additional blank or nonblank
records, including extra trailing LF characters, stop startup before image
inspection, explicit builds, or launch. Query failures remain failures even if
stdout looks valid; delegated query errors identify the selected endpoint.
The endpoint must contain an absolute socket pathname beyond `/`; `unix://`,
`unix:///`, slash-only paths, and relative Unix paths fail before any engine
query, even when delegation is disabled or a delegation override is supplied.

When delegation is enabled, the selected socket is the first of:

1. Nonempty `CLAUDE_CONTAINER_PODMAN_SOCKET` (absolute path, without `unix://`).
2. The wrapper's explicit Unix `CONTAINER_HOST` (with `unix://` removed).
3. `${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock`.

The socket must be accessible and serve a rootless engine that reports an
absolute host-side socket path. With a remapped socket, the wrapper queries the
client-visible path and binds the reported host-side path into the session.
The launch and delegation services must be on the same host; a delegation
override does not change the launch engine. Choose **one** setup method below.

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
podman_socket="${CLAUDE_CONTAINER_PODMAN_SOCKET:-${CONTAINER_HOST#unix://}}"
podman_socket="${podman_socket:-${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock}"
test -S "$podman_socket" && echo "Socket exists"
podman --remote --url "unix://$podman_socket" info --format '{{.Host.Security.Rootless}} {{.Host.RemoteSocket.Path}}'
```

Continue only if the socket exists and the API command succeeds and prints
`true` followed by an absolute host-side socket path. With
`CLAUDE_CONTAINER_PODMAN=1`, the wrapper enforces this check through
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

Automatic builds and `--container-build` use the directory beside the resolved
wrapper script. `.containerignore` excludes all local content except
`Containerfile` and `.containerignore`, since the recipe currently needs no
local `COPY` or `ADD` inputs. Git metadata, Claude configuration, custom state
directories, environment files, caches, and unrelated files are excluded from
the build context. Add any future intentional local build inputs to that
allowlist together with the recipe change. Runtime workspace mounts are
independent of this build-context filter.

The wrapper can replace `claude` through a shell alias:

```bash
alias claude=/absolute/path/to/claude-container.sh
```

The wrapper handles `--container-build`, `--container-shell`,
`--container-git-worktree`, and `--container-help`. Every other argument is
forwarded unchanged, so normal commands such as `claude --help` and
`claude resume --last` retain their meaning.

Each container reserves a name from the physical current directory and the
next numeric index among all existing instances, for example `my-project-0`
and `my-project-1`. Concurrent name collisions are retried up to 20 times;
existing sessions are never deleted to free a name. INT, TERM, and HUP are
forwarded to the owned container. The wrapper preserves process exit codes
(including 125) and removes only its own container at termination.

Shutdown has one 20-second budget. After forwarding a signal, the wrapper allows
at most 5 seconds for graceful exit, then attempts forced removal with Podman's
stop wait set to zero. Shutdown engine calls have a 2-second soft timeout and
at most 1 further second before forced client termination, capped by the remaining
overall budget. Local create/attach clients are also terminated and reaped within
that budget. Normal application and build durations are unrestricted.

The first terminal signal selects status 143 (TERM), 130 (INT), or 129 (HUP);
later signals do not restart shutdown. Otherwise the application's exit status
is retained, including zero and 125, even if cleanup fails. Failures are reported
on stderr with the known container ID or session ownership label. If the engine
cannot confirm removal, inspect that identity on the host with `podman inspect`
or filter `podman ps --all --filter label=io.claude-container.session=SESSION`,
replacing `SESSION` with the reported session token.
Only remove a confirmed session container. A disconnected engine can finish
creation after bounded recovery ends; a warning does not mean it was removed.

Private per-attempt CID files and a unique session label support recovery when
creation is interrupted before its client returns an ID. A workspace name alone
never authorizes removal, and interrupted creation never starts the application.

A TTY is allocated only when stdin and stdout are terminals. Redirected stdin,
argument order, spaces, and empty arguments are preserved, supporting pipelines
and headless CLI use. Shell mode ignores Claude arguments and YOLO injection.
`--container-help` requires no engine and creates no state.

`CLAUDE_YOLO=1` adds `--dangerously-skip-permissions` for that session. Use it
only when the container and mounts are a
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
disabled, the wrapper skips delegation-endpoint validation and separate queries,
does not mount the host socket, and explicitly removes `CONTAINER_HOST` from
the container environment, including image or engine defaults. The host client
retains any Unix `CONTAINER_HOST` needed to launch the session. When enabled,
it mounts the socket at `/run/podman/podman.sock` and sets
`CONTAINER_HOST=unix:///run/podman/podman.sock` in both Claude and shell modes.
Mandatory launch-engine verification still runs in either mode.
A missing or invalid socket stops an enabled launch with setup instructions.
The wrapper also queries the selected service and accepts only a successful
`true` rootless result and an absolute host-side socket path. An unreachable
service, rootful engine, or unexpected
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

Claude configuration defaults to `~/.claude`, or `CLAUDE_CONFIG_DIR` when
nonempty, mounted read/write at `/claude-home/.claude`. Host
`~/.config/openspec` is also mounted read/write at
`/claude-home/.config/openspec`. The rest of `/claude-home` remains read-only
in this shared mode. Credentials, plugins, history, and settings remain shared
with host Claude; the agent can read and change these mounted files.

### Optional isolated home

Set a nonempty `CLAUDE_CONTAINER_STATE_DIR` to mount a dedicated writable home
at `/claude-home`, without adding the shared Claude/OpenSpec mounts:

```bash
unset CLAUDE_CONFIG_DIR
CLAUDE_CONTAINER_STATE_DIR="$HOME/.local/share/claude-container/home" ./claude-container.sh
```

Inside the container, `HOME=/claude-home` and
`CLAUDE_CONFIG_DIR=/claude-home/.claude` in both modes. In isolated mode,
`.claude`, `.config/openspec`, caches, and other home data persist under the
selected directory. A simultaneous nonempty `CLAUDE_CONFIG_DIR` is rejected;
unset it to select isolation. Unset/empty `CLAUDE_CONTAINER_STATE_DIR` keeps the
shared default. A directory alias is resolved to its physical absolute path.
Existing isolated configuration symlinks escaping the selected home are rejected.

New credential directories are created with user-only permissions. The shared
Claude directory, or isolated home and its `.claude` directory, must belong to
the caller, allow read/write/search, and deny group/other access. Existing
permissions are never changed recursively. If startup rejects a directory,
inspect it and explicitly use `chmod 700` on the named directory, or select
private native Linux storage if the filesystem ignores Unix modes (some WSL
Windows-backed mounts do). Directory checks do not recursively audit old files,
encrypt state, or hide credentials from the agent using them.

The wrapper applies `umask 077` only while creating state directories, preserving
the caller's umask for subsequent host commands. This does not set the container
process umask or guarantee private modes for files created inside a session;
those modes depend on the runtime and the application. Directory privacy checks
and measured runtime file modes are separate guarantees.

To migrate, stop sessions and use a new private dedicated directory. Either
sign in afresh or deliberately copy selected files from the previous Claude
configuration into `<state>/.claude` and selected OpenSpec configuration into
`<state>/.config/openspec`. Preserve private file permissions, protect backups,
and do not overwrite an existing profile or copy the whole host home. The
wrapper never imports, merges, or deletes profiles automatically. To return to
shared state, unset `CLAUDE_CONTAINER_STATE_DIR` and restore any previous
`CLAUDE_CONFIG_DIR`; dedicated state remains on disk.

### Authority and security policies

The root filesystem is read-only; selected workspace/state mounts are writable.
Automatic read-only tmpfs provisioning is disabled. `/tmp`, `/run`, and
`/var/tmp` are explicit ephemeral tmpfs mounts with `nosuid,nodev,noexec` and
limits of 256 MiB, 16 MiB, and 256 MiB respectively. `/tmp` and `/var/tmp` have
sticky mode `1777`. Their contents disappear when the container is removed.
`/var/tmp` is now explicitly bounded and prevents direct execution, so tools
must not depend on executable temporary files there. No writable `/var/log`
mount is added. The optional host CA remains a single read-only file.
No full host home, SSH agent, desktop bus, or keyring is added automatically.
A selected workspace or worktree parent can itself contain those host files;
a parent of `$HOME` or `/` exposes that entire directory read/write.

**With `CLAUDE_CONTAINER_PODMAN=1`, Claude can control the service user's
containers and volumes and request new host bind mounts beyond the workspace.**
The socket removes the project-only filesystem boundary. To pin the old endpoint
explicitly, use `CLAUDE_CONTAINER_PODMAN_SOCKET=/run/user/$(id -u)/podman/podman.sock`
alongside `CLAUDE_CONTAINER_PODMAN=1`; runtime-directory or Unix launch endpoint
settings otherwise affect selection.

YOLO, Claude's internal sandbox, and outer container isolation are separate.
YOLO and socket delegation are independent, in either state mode:

| `CLAUDE_YOLO` | `CLAUDE_CONTAINER_PODMAN` | Wrapper additions |
| --- | --- | --- |
| disabled | disabled | No bypass flag or socket |
| enabled | disabled | Bypass flag only |
| disabled | `1` | Socket only |
| enabled | `1` | Bypass flag and socket |

YOLO accepts `1/true/yes` and `0/false/no` case-insensitively; empty means disabled
and invalid values fail before image operations. Socket access keeps its exact
`1` rule. Disabling YOLO does not neutralize native flags or saved permission
settings. The wrapper does not filter network egress.

Standard seccomp and SELinux policy remain in force. The wrapper adds no
privileged mode, capabilities, custom security profiles, disabled labels, or
automatic bind relabeling (the former OpenSpec `:z` option is removed). If host
policy denies a bind, the engine error is reported; configure host policy
explicitly. An internal sandbox failure does not relax these policies or tmpfs
options. `bwrap --version`, namespace probes, or a zero CLI exit status alone do
not prove a sandboxed tool operation succeeded. See [validation](docs/validation.md)
for tested environments, results, and outstanding checks.

## Included tools

The image includes Node.js/npm, Claude Code, Python 3, Bubblewrap (`bwrap`), the
Podman client, Git, Bash, local search and editing tools, archive tools, JSON
support, and diagnostics needed to work in a repository and run tests in
containers.

The image includes the `nano` editor, and `EDITOR` and `VISUAL` are set to
`nano`, so commands that open an editor, such as `/memory`, work inside the
container. The host's `EDITOR` and `VISUAL` are not forwarded.

## Verification

```bash
bash -n claude-container.sh
python3 -m unittest discover -s tests -p test_wrapper.py -v
CLAUDE_RUNTIME_TESTS=1 python3 -m unittest discover -s tests -p test_runtime.py -v
bash tests/run-runtime.sh
git diff --check
```

Wrapper tests use synthetic HOME/state and a fake Podman, without host
credentials or a real engine. They need executable temporary storage with Unix
permissions; set `CLAUDE_TEST_TMPDIR` to a suitable native Linux directory when
`/tmp` is `noexec`. Runtime tests are opt-in and require a built image and a
rootless engine. The runner uses a disposable native Linux volume for state,
preserves host absolute paths, and removes only its own test resources; it can
also run the wrapper tests via `bash tests/run-runtime.sh --wrapper` when host
Python is unavailable. No automated test uses real credentials or paid model
requests. Image absence triggers a build; inspection errors stop startup rather
than causing an accidental rebuild. Explicit builds retain normal caching.
