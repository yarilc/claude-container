# Claude Code CLI in Podman

`claude-container.sh` runs Claude Code in a rootless Podman container. Access
from the container to the host Podman API is disabled by default. Set
`CLAUDE_CONTAINER_NETWORK=unrestricted CLAUDE_CONTAINER_PODMAN=1` to let Claude launch containers for tests and builds
through the host socket without running a nested daemon.

## Enable rootless Podman on the host

Setup is the mandatory first step for new users. Run this from a reviewed
checkout on the Linux/WSL host as the non-root user who will run the sandbox:

```bash
bash ./claude-container.sh --container-setup
```

Setup requires an interactive terminal, installed rootless Podman, host Python 3
and GNU coreutils. It asks how you want to work, explains network/state/authority
choices and prepares a protected native installation plus a managed launch
command. The first-run defaults are provider-restricted networking with Claude
account authentication, shared Claude state and
disabled optional authority. No API key is needed for Claude account use. Setup
does not install Podman or any other host package. The following manual steps
remain available for prerequisite preparation and troubleshooting.

After setup, use the managed launch command it prints from your project
directory. It supplies the saved runtime mode. An ordinary direct invocation
with `CLAUDE_CONTAINER_NETWORK` unset or empty exits with setup guidance before
checking runtime prerequisites, contacting Podman or creating application state.
Setup never starts automatically. Operators can still select a mode explicitly
for manually prepared installations and maintenance; restricted modes retain
all protected-path, guard and qualification checks.

See the [guided setup reference](docs/setup.md) for saved preferences, image
preparation, reruns/rollback and separate sandbox/authentication readiness.

Provider transport isolates a missing stream-close acknowledgement from healthy
tunnels. Closing records remain within the 64-stream budget until acknowledged;
exhaustion refuses new local tunnels while established ones continue. Temporary
control congestion applies bounded backpressure; a sustained shared-write stall
still fails the channel closed. To deploy the N23 update, prepare matching runtime
and immutable proxy images plus protected code, rerun qualification through setup
or the manual workflow, and restart existing sessions. Failed candidates preserve
the previous activation; see the setup reference for matching-image rollback.

When a Unix service is required, setup reuses the selected same-host rootless
endpoint or offers `systemctl --user enable --now podman.socket` with separate
confirmation. This enables a host launch service; application delegation remains
a separate unrestricted-only choice. No `sudo`, lingering or WSL/system-wide
configuration changes are performed. Without a working user manager, setup gives
foreground-service instructions below and stays incomplete until that endpoint
is verified. A socket file by itself is not sufficient. Missing rootless UID/GID
mappings or helpers must be addressed outside setup; `podman info` must succeed
as the intended non-root user.

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

## Enable the launch service or optional Podman delegation

Restricted networking currently requires the tested same-host Unix launch
service, even with delegation disabled. An unrestricted local session needs no
API service unless `CLAUDE_CONTAINER_PODMAN=1` is selected. Host Podman is always
required for image operations and launch. See the network setup below for the
protected installation required by restricted modes.

Every session verifies that its launch engine is Linux and rootless before
image inspection, build, or launch. Unrestricted local Podman needs no API service when
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
Delegated socket responses containing any CR character, including a CRLF
terminator, are rejected before field parsing or use of the reported host path.
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

## Network modes and protected installation

Restricted sessions now use a protected static bootstrap combining Landlock ABI 3
filesystem rules, an additional restrictive seccomp filter and private network,
PID and IPC namespaces. Native Linux and WSL2 x86_64 are eligible with usable
Landlock ABI >= 3 and successful local enforcement qualification. Kernel release
strings are recorded as evidence rather than pinned; no ABI-9 feature is required.
The earlier IP-only candidate was bypassed through workspace Unix
sockets and is superseded. See [bootstrap build/tests](network/README.md) and
[versioned evidence](docs/validation.md). Authenticated profile readiness remains partial. Actual Claude Bash-tool
execution is checked separately with a controlled synthetic Messages API; it
does not establish real provider authentication or model behavior.

**Migration:** versions before `c777b73` used ordinary networking without the
runtime-mode interface. The enforced-network change introduced an unset/empty
`offline` default. Ordinary launches now refuse an unset or empty effective mode
with setup guidance. First-run setup proposes `provider` with account
authentication and saves the selected mode for its managed launcher. Operators
can explicitly choose `offline` for prepared restricted sessions or `unrestricted`
for broad networking. Offline sessions cannot reach the Claude API.
A required image build also needs
exact `CLAUDE_CONTAINER_MAINTENANCE=1`; runtime mode never grants maintenance
authority. An absent image no longer triggers an implicitly authorized build.

For example, explicit operator maintenance uses both controls:

```bash
CLAUDE_CONTAINER_NETWORK=unrestricted CLAUDE_CONTAINER_MAINTENANCE=1 bash ./claude-container.sh --container-build
```

| `CLAUDE_CONTAINER_NETWORK` | Behavior |
| --- | --- |
| unset or empty | Ordinary launch stops with setup guidance |
| `offline` | `--network=none`; own loopback services only |
| `provider` | Same isolation plus an external CONNECT proxy with initial and retried TLS SNI binding |
| `unrestricted` | Explicit ordinary runtime networking; socket delegation is eligible |

Every agent container, in all three modes and including shell mode and Podman
delegation, and every session proxy explicitly drops all Linux capabilities and
enables container-level `no-new-privileges` before startup. Caller UID/GID and
`--userns=keep-id`, standard OCI seccomp, SELinux policy and existing mount
restrictions remain in force. Hardening failures stop startup without a weaker
retry. Agent resource budgets are described in
[Agent hardening, budgets and lifetime](#agent-hardening-budgets-and-lifetime).
Each provider proxy is limited to 128 processes and 256 MiB memory. Startup
verifies Podman configuration and the effective limits inside the actual proxy
cgroup before starting the agent. A limit whose rootless cgroup v2 controller
(`pids` or `memory`) the engine does not delegate is not requested and is
announced; a delegated limit that is ignored or unverifiable stops provider
preparation. Proxy exhaustion leaves outbound access closed.

Restricted eligibility requires rootless Netavark/Podman server >= 4.9 through an
explicit same-host Unix CONTAINER_HOST, host Python 3, standard OCI seccomp and
actual guard enforcement. Stable later server versions have no upper pin.
SELinux/AppArmor may remain enabled; compatibility is not guaranteed and any
policy denial stops startup without relabeling, policy disablement or privileges.
The previously measured WSL 6.6.87.2 / server 4.9.3 environment remains historical
evidence, separate from qualification of another installation.

**Migration:** restricted launches now require a protected matching local report.
Rerun `--container-setup`, or run `--container-qualify` alone from a protected
manually prepared installation with explicit environment settings. Qualification
uses disposable credential-free controls, both state modes and the production
guard/proxy path; it does not send real model requests or grant image maintenance.
Ordinary direct environment-based invocation remains supported after qualification.
Missing, unsafe or stale evidence blocks startup. A successful ABI/version probe
alone is insufficient. Changed kernel/boot, engine/backend/security state, code,
images, policy/profile, CA trust or hardening requires requalification. When an
active LSM policy cannot be identified for safe reuse, the gate repeats each launch.
Every launch still verifies paths, engine, guard and proxy readiness.

`locally-qualified` means this installation passed its required controls. It does
not certify every distribution, LSM policy or authenticated provider flow.
`release-measured` additionally requires an exact matching protected acceptance
entry; the default inventory is empty. See [qualification details](network/README.md#local-installation-qualification).

The guard denies new Unix sockets, VSOCK and other families except IPv4/IPv6,
which remain inside network=none. It allows only fixed-peer connected Unix
stream/seqpacket pairs, pipes and own loopback. Existing pairs may have private
pathname/abstract names but cannot listen, change peer or publish into host binds.
New named Unix services, host SSH agents and named cache/supervisor daemons are
unavailable, including on tmpfs. io_uring, pidfd_getfd and compat/x32 syscall
bypasses are denied. Ordinary file persistence and Git/worktree operations remain
available. A private XDG_RUNTIME_DIR holds ordinary runtime files; HOME and
configuration persistence stay unchanged.

Provider mode uses exactly one bootstrap-verified preconnected data descriptor.
The confined loopback relay multiplexes independently authorized tunnels over it;
more than 64 sequential requests are supported, with at most 64 active streams,
bounded credit/queues and versioned framing. The application exec branch closes
that descriptor. Proxy/channel death fails closed and requires a new session;
there is no reconnect exception, unconfined in-container broker or administration.

Restricted networking requires a protected installation outside every writable
workspace/worktree-parent and application-state mount. Files and all ancestor
directories must belong to the caller or root and deny group/other writes.
An agent-writable launcher cannot enforce its own future invocation. Use native
Linux storage; permission-emulating Windows mounts and world-writable ancestors
such as `/tmp` are unsuitable. For example, install from this checkout:

```bash
installation="$HOME/.local/lib/claude-container"
install -d -m 700 "$installation/agent/policies" "$installation/network/bin" "$installation/setup"
install -m 700 claude-container.sh "$installation/claude-container.sh"
install -m 644 Containerfile .containerignore "$installation/"
install -m 644 setup/diagnostics.py "$installation/setup/"
install -m 644 agent/profile.json "$installation/agent/"
install -m 644 network/control.py network/policy.py network/agent_profile.py network/session.py network/proxy.py \
    network/relay.py network/mux.py network/resolv.conf network/Containerfile network/.containerignore "$installation/network/"
install -m 600 agent/policies/default.json "$installation/agent/policies/default.json"
install -d -m 700 "$HOME/.local/state/claude-egress"
# Prepare the pinned compiler image once, as operator maintenance.
# --pull=never expects its pinned Alpine base to be prepared already; see network/README.md.
podman build --pull=never --tag localhost/claude-guard-toolchain:development \
    --file network/guard-build.Containerfile network
# Build and install the protected static guard plus its digest manifest.
CLAUDE_CONTAINER_MAINTENANCE=1 bash network/build-guard.sh "$installation/network/bin"
```

Keep all ancestors protected; the wrapper validates them without recursively
repairing existing permissions. In a separate workspace, use the installed
wrapper and the launch service configured above:

```bash
export CONTAINER_HOST="unix://$XDG_RUNTIME_DIR/podman/podman.sock"
"$installation/claude-container.sh" --container-shell  # offline
```

An operator must prepare the runtime and proxy images separately. The proxy has
no third-party Python dependencies and its base image is pinned by digest:

```bash
# Explicit operator maintenance; these build/pull operations are outside
# runtime filtering and require their own network controls if desired.
CLAUDE_CONTAINER_MAINTENANCE=1 "$installation/claude-container.sh" --container-build --container-shell
podman build --tag localhost/claude-egress:local \
    --file "$installation/network/Containerfile" "$installation/network"
egress_image=$(podman image inspect --format '{{.Id}}' localhost/claude-egress:local)

CLAUDE_CONTAINER_NETWORK=provider \
CLAUDE_CONTAINER_NETWORK_PROFILE=anthropic-api \
CLAUDE_CONTAINER_NETWORK_POLICY="$installation/agent/policies/default.json" \
CLAUDE_CONTAINER_NETWORK_RUNTIME_DIR="$HOME/.local/state/claude-egress" \
CLAUDE_CONTAINER_EGRESS_IMAGE="$egress_image" \
"$installation/claude-container.sh"
```

The proxy image must be a full immutable image ID or registry digest. A missing
registry digest can be pulled only under exact maintenance authorization; missing
local image IDs require operator preparation. Maintenance authorization is not
forwarded to the agent. Runtime filtering does not constrain host image pulls,
build RUN commands, or other operator maintenance tools. Image preparation needs
outbound HTTPS (443) to the container, Debian, Alpine and npm registries, but not
port 80: the runtime image fetches Debian packages only over verified HTTPS.

Provider mode requires all four policy/profile/runtime/image variables above.
Runtime storage must be caller-owned `0700`, outside writable agent mounts, and
visible at exactly the same absolute path to the host service. The agent receives
only its own read-only transport directory, resolver file, static guard and relay/codec assets. Policy
snapshots, logs, and proxy control remain outside its mounts. Both cases of
HTTP/HTTPS proxy variables are set consistently; inherited/image defaults and
alternate proxies are cleared, with only exact loopback bypass entries. Removing
or changing those variables cannot create an external route.

The schema in `network/policy.py` strictly validates `schema_version: 1`, revision,
source date/URLs, tested CLI/Node/authentication metadata, and named profiles.
Each profile declares authentication (`api`, `account`, or explicit `custom`),
`disable_optional_traffic: true`, and exact host/port destination entries. Hostnames
are ASCII, normalized to lowercase with one final dot removed; wildcard, duplicate,
IP-literal and ambiguous authorities are rejected. Normal destinations use port
443. Explicit local-provider exceptions additionally list exact `addresses` and
may name a reviewed different port. All resolved addresses must match that exact
exception, or all must pass the public-address checks. Mixed public/private answers,
IPv4-mapped/transition IPv6 and metadata/private/special ranges are rejected.
The proxy resolves approved names only and connects to the already validated
numeric address. Other methods, direct DNS, UDP/QUIC and alternate routes are denied.
Special-use exclusions also use the dated
[IANA IPv4](https://www.iana.org/assignments/iana-ipv4-special-registry/) and
[IPv6](https://www.iana.org/assignments/iana-ipv6-special-registry/) inventories,
reviewed 2026-11-06, rather than relying on Python-version classifications alone.

`anthropic-api` permits only `api.anthropic.com:443`. The separate
`anthropic-account` inventory adds only `platform.claude.com:443` (policy revision
`anthropic-2026-11-08-v2`). The inventories were checked against
[official standalone CLI requirements](https://code.claude.com/docs/en/network-config)
on 2026-11-06. A static endpoint inventory of CLI 2.1.316 on 2026-11-08 found
OAuth code exchange and token refresh at `platform.claude.com`, account API calls
at `api.anthropic.com`, and authorization pages opened in the host browser, so
`claude.ai` and `claude.com` were removed from the account profile and are denied.
Operators who need them must define a separately named profile in an operator
policy; the exact base profile cannot be extended. On 2026-11-07 an operator-reported account request using existing
OAuth credentials returned ACCOUNT_PROFILE_OK and exit 0 through the restricted
wrapper. A subsequent fresh isolated login and separate ACCOUNT_LOGIN_OK request
also succeeded with exit 0. An automatic refresh after the recorded token expired
returned ACCOUNT_REFRESH_OK and exit 0, advancing the stored expiry. These are
operator-reported checks of the account HTTPS/SSE flow; real-key API authentication
remains unverified; see [the validation record](docs/validation.md). API-key support is
implemented and covered by synthetic integration tests. A real-key check is
optional and non-blocking when no key is available; this does not claim real-key
authentication was verified. Account access does not require an API key. Host
browser steps are outside container enforcement. SSO and third-party clouds/gateways require separately reviewed
profiles; the default inventory does not grant them. An explicitly supplied host
`ANTHROPIC_API_KEY` is forwarded by name in provider mode; no key is copied into
the image or policy. Existing account state follows the selected persistence mode.

Provider startup sets version-supported controls for nonessential traffic,
updaters, telemetry/error reporting, account MCP connectors, and artifacts.
Documentation lookups and runtime plugin downloads remain blocked unless
explicitly authorized by a feature profile. Changing writable Claude settings
cannot add network destinations. Controls were identified in the installed
2.1.316 binary and current documentation; their presence alone does not establish
authenticated behavioral compatibility. No broad vendor/CDN or storage wildcard
is added to repair a failed feature.

Startup reports mode, profile, revision/digest, and a private session diagnostic
path. Denial records contain only sanitized bounded hostname/port, reason, time,
and session ID; they omit credentials, headers, URLs, prompts and bodies. Each
log is capped at approximately 1 MiB. The last 20 sanitized records are reported
on exit; ephemeral session logs are then removed. Reasons distinguish policy
denial, unsafe addresses, DNS failure, and connection/proxy readiness failures.
Provider authentication errors remain the client's diagnostics inside TLS.
Denials never extend a policy. Proxy death leaves the agent without a direct
route. All owned resources share the existing shutdown budget and primary status.

CONNECT preserves end-to-end TLS and existing opt-in CA trust without decryption.
The trusted proxy holds client bytes until a bounded TLS 1.2/1.3 initial
ClientHello has exactly one normalized SNI matching the approved CONNECT name.
Missing, malformed or different SNI, non-TLS, ECH (including GREASE), inspection
limits and timeout fail closed. After a TLS 1.3 HelloRetryRequest, the retried
ClientHello must name the same host before the proxy forwards it; client bytes
are held until the server's first handshake message shows whether a retry
happened. TLS 1.2 renegotiation is an accepted limitation: its ClientHello is
encrypted and the proxy does not decrypt TLS, so it is not inspected.
This verifies the TLS names the proxy can see, not exclusive
communication with Anthropic applications. Allowed services can receive session
data. Encrypted HTTP Host/authority, domain fronting with matching SNI, shared
services and provider-hosted remote tools remain outside the filter. Git hosting, registries, web browsing, external MCP endpoints,
documentation, connectors and plugin downloads need explicit extra authorization.

### Residual exfiltration to allowed services

Destination and SNI binding cannot tell your credentials from attacker-supplied
ones. A prompt-injected agent can send workspace data to any allowed host using
a foreign API key or account: `api.anthropic.com` under `anthropic-api`, and
`api.anthropic.com` or `platform.claude.com` under `anthropic-account`. Setup
asks you to acknowledge this whenever provider mode is selected. Narrowing the
account inventory reduces the number of such hosts but does not close the
channel; only offline mode removes it. Credential-injecting TLS interception is
evaluated in the [network contract](docs/network-contract.md#credential-injecting-interception-not-implemented)
and is not implemented.

Provider releases require proxy enforcement identity `tls-clienthello-sni-v2`.
Deploy protected wrapper code and the rebuilt immutable proxy image together;
old images fail readiness before Claude starts. ECH/GREASE clients are unsupported
unless configured to use a supported non-ECH handshake; no automatic bypass or
TLS interception occurs. A rollback to an old release removes this guarantee;
use offline mode when a verified compatible release is unavailable.

See [the portable contract and sibling adoption checklist](docs/network-contract.md)
and [measured validation results](docs/validation.md). No sibling wrapper is claimed
implemented or verified here.

## Usage

The following commands select an unrestricted checkout workflow. Run restricted
sessions from a separate workspace using the protected installation above:

```bash
chmod +x claude-container.sh
export CLAUDE_CONTAINER_NETWORK=unrestricted
CLAUDE_CONTAINER_NETWORK=unrestricted CLAUDE_CONTAINER_MAINTENANCE=1 ./claude-container.sh --container-build
./claude-container.sh
./claude-container.sh -p "run the tests"
./claude-container.sh --container-shell
./claude-container.sh --container-help
CLAUDE_YOLO=1 ./claude-container.sh
```

With exact `CLAUDE_CONTAINER_MAINTENANCE=1`, absent-image builds and `--container-build` use the directory beside the resolved
wrapper script. `.containerignore` excludes all local content except
`Containerfile`, `.containerignore`, and the explicit `network/relay.py` and
`network/mux.py` runtime inputs. Git metadata, Claude configuration, custom state
directories, environment files, caches, and unrelated files are excluded from
the build context. Add any future intentional local build inputs to that
allowlist together with the recipe change. Runtime workspace mounts are
independent of this build-context filter.

The wrapper can replace `claude` through a shell alias:

```bash
alias claude=/absolute/path/to/claude-container.sh
```

The wrapper handles `--container-build`, `--container-shell`,
`--container-git-worktree`, `--container-toolchain` (see [Toolchains](#toolchains))
and `--container-help`. Every other argument is
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
CLAUDE_CONTAINER_NETWORK=unrestricted CLAUDE_CONTAINER_PODMAN=1 ./claude-container.sh
CLAUDE_CONTAINER_NETWORK=unrestricted CLAUDE_CONTAINER_PODMAN=1 ./claude-container.sh --container-shell
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
workflows that launch child containers must now select explicit unrestricted
networking as well as exact `CLAUDE_CONTAINER_PODMAN=1`. Restricted modes reject
that combination because the host API can create unfiltered child containers.
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
A parent that is a refused sensitive directory, such as your home, stops the
launch.

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

The same bundle also verifies the runtime image build's Debian package
downloads, which use HTTPS only. With host CA trust enabled, `--container-build`,
a missing-image build and setup preparation pass it as the build secret
`build-ca`: it is mounted only for the package installation step and is not stored
in the image. Setup gives it to the guard toolchain build as well, for its Alpine
package downloads. Without host CA trust, the build trusts only the root certificates
of the pinned base image. On a network that intercepts TLS (a corporate proxy that
re-signs certificates), enable host CA trust with a bundle that contains the
interception CA, or the build fails with a certificate verification error.

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

Every agent container, provider proxy and qualification gate container gets an empty read-only tmpfs at
`/run/secrets`. On RHEL and Rocky hosts Podman's `mounts.conf` would otherwise
mount the host subscription secrets there, writable; with the mask Podman skips
that mount, the agent sees no host subscription material, and the restricted
bootstrap accepts the layout. No host configuration change is needed.

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
`/tmp`, `/run`, and `/var/tmp` are explicit ephemeral tmpfs mounts with
`nosuid,nodev,noexec` and limits of 256 MiB, 16 MiB, and 256 MiB respectively.
Podman's automatic read-only tmpfs provisioning stays enabled: with
`--read-only-tmpfs=false`, Podman 5 would mount `/dev` read-only, and newer
crun releases cannot attach a terminal there. The engine provides `/dev` and
a `devpts` at `/dev/pts` that allows pseudo-terminals, which interactive
tools such as `script`, `expect` or `tmux` need. An explicit `devpts` mount
would get `ptmxmode=000`, and no pseudo-terminal could be opened. `/dev/shm`
is an empty read-only tmpfs. On Podman 5, `/dev` is the engine's writable
tmpfs, but no device can be created without capabilities. On Podman 4.9,
`/dev` stays read-only. `/tmp` and `/var/tmp` have
sticky mode `1777`. Their contents disappear when the container is removed.
`/var/tmp` is now explicitly bounded and prevents direct execution, so tools
must not depend on executable temporary files there. No writable `/var/log`
mount is added. The optional host CA remains a single read-only file.
No full host home, SSH agent, desktop bus, or keyring is added automatically.
A selected workspace or worktree parent can itself contain those host files.
The wrapper therefore refuses sensitive workspace roots; see
[Agent hardening, budgets and lifetime](#agent-hardening-budgets-and-lifetime).

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
settings. The independent outer network boundary is controlled by
`CLAUDE_CONTAINER_NETWORK`; shell/YOLO/native settings cannot disable it.
The four socket/YOLO combinations above apply in unrestricted mode. Restricted
modes reject enabled delegation.

### Agent hardening, budgets and lifetime

Every agent container runs with `--cap-drop=all` and
`--security-opt=no-new-privileges` in every mode. Tools that need a capability
are unsupported; the wrapper never adds one back. The delegated Podman client
works without capabilities, but the socket still grants host engine authority.

Every agent container also receives memory, CPU and process budgets, for each
budget whose cgroup v2 controller the rootless engine delegates:

| Variable | Default | Accepted values |
| --- | --- | --- |
| `CLAUDE_CONTAINER_MEMORY_LIMIT` | `4g` | positive integer with unit `k`, `m` or `g` |
| `CLAUDE_CONTAINER_CPU_LIMIT` | `2` | positive number of CPUs with at most 3 decimals |
| `CLAUDE_CONTAINER_PIDS_LIMIT` | `512` | positive integer up to 4194304 |
| `CLAUDE_CONTAINER_RUN_TIMEOUT` | `0` (disabled) | whole seconds of container lifetime |

`--container-setup` asks for these values and saves them; the managed launcher
supplies them unless a variable is exported. Change them by rerunning setup.
An exported value that differs from the saved one is used, but a restricted
launch then stops until you requalify with `--container-qualify`. Budgets
cannot be disabled: empty, `0`, `-1` and `max` are rejected before any engine
operation. Each launch checks the created container's configured limits before
the application starts; setup smoke and restricted qualification measure the
effective cgroup v2 `memory.max`, `pids.max` and `cpu.max`. Budgets and tmpfs
sizes do not limit workspace or state storage growth.

The sandbox adapts to the controllers the engine reports
(`podman info --format '{{.Host.CgroupControllers}}'`) instead of requiring host
changes. A budget whose controller (`memory`, `cpu` or `pids`) is not delegated
is not requested; every launch and the setup plan print a notice such as
`agent CPU budget not enforced: cgroup controller cpu is not delegated to the
rootless engine`, and continue without asking. The check is still strict: a
delegated budget must be applied exactly, an unenforced one must be absent, and
the enforced set is part of the restricted qualification identity, so a later
delegation change requires requalification. Provider proxy budgets follow the
same rule. Risk: without memory or process budgets, a compromised or runaway
agent can exhaust host memory or processes for your user; without a CPU budget
it can saturate every CPU. Delegating the controllers (for example a systemd
`Delegate=cpu cpuset io memory pids` drop-in for `user@.service`) restores full
enforcement, but the sandbox never requires it.

With a lifetime limit, the engine stops the agent container after that many
seconds. The wrapper reports `session lifetime limit reached` and keeps the
engine client's exit status (255 on the measured Podman 4.9.3 server); owned proxies are cleaned up within the usual
shutdown budget.

The writable workspace mount (the parent with `--container-git-worktree`) must
not be `/`, your home directory, `/home`, `/root`, `/etc`, `/usr`, `/var`, `/bin`,
`/sbin`, `/lib`, `/lib64`, `/boot`, `/opt`, `/srv`, `/mnt`, `/media`, `/proc`,
`/sys`, `/dev`, `/run`, `/tmp` or a WSL drive root such as `/mnt/c`. Physical
paths are compared, so symlinks do not bypass the check. Launch from a project
subdirectory instead. Exact `CLAUDE_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1` permits a
refused directory with a warning and relaxes nothing else.

### Standard security policies

Standard seccomp and SELinux policy remain in force. The wrapper adds no
privileged mode, capabilities, custom security profiles, disabled labels, or
automatic bind relabeling (the former OpenSpec `:z` option is removed). If host
policy denies a bind, startup stops and reports the engine error; compatibility
with that policy remains unguaranteed. An internal sandbox failure does not relax these policies or tmpfs
options. `bwrap --version`, namespace probes, or a zero CLI exit status alone do
not prove a sandboxed tool operation succeeded. See [validation](docs/validation.md)
for tested environments, results, and outstanding checks.

## Included tools

The image includes Node.js/npm, Claude Code, Python 3, Bubblewrap (`bwrap`), the
Podman client, Git, Bash, local search and editing tools, archive tools, JSON
support, and diagnostics needed to work in a repository and run tests in
containers.

Image inputs are pinned: the `Containerfile` installs exact Claude Code and
OpenSpec versions on a base image referenced by digest, and sets
`DISABLE_AUTOUPDATER=1`. The pinned CLI version must equal the policy's
`tested.cli`; `tests/test_image_pins.py` enforces both rules. Update them only
through the [maintenance procedure](docs/validation.md#updating-pinned-image-inputs).

The image includes the `nano` editor, and `EDITOR` and `VISUAL` are set to
`nano`, so commands that open an editor, such as `/memory`, work inside the
container. The host's `EDITOR` and `VISUAL` are not forwarded.

## Toolchains

Sessions can use extra toolchains, such as Java, Go or Python, without Podman
access, an unrestricted network or a rebuilt image. The operator keeps a
toolchain library on the host. Every session sees it read-only, with `nosuid`
and `nodev`, at `/toolchains`. The library is shared by the Claude, Codex,
OpenCode, Pi and Antigravity wrappers. A toolchain adds no network, IPC or
privilege capability: it runs under the same restrictions as the rest of the
session.

- **Location:** `${XDG_DATA_HOME:-~/.local/share}/sandbox-toolchains`, or
  `CLAUDE_CONTAINER_TOOLCHAINS_DIR`. The launcher creates it private (`0700`)
  when it is missing. It must stay outside the workspace, the state
  directories and the installation. A home directory exposed as the workspace
  with `CLAUDE_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1` contains the default
  library, so that launch stops. Move the library with
  `CLAUDE_CONTAINER_TOOLCHAINS_DIR`, or omit it.
- **Disable:** `CLAUDE_CONTAINER_TOOLCHAINS=0` starts a session without the
  mount.
- **Live updates:** a toolchain added or removed on the host appears in
  running sessions without a restart.

### Managing the library

The operator runs these commands on the host; `--container-toolchain` must be
the first argument:

```bash
claude --container-toolchain add java21.json   # install or replace from a recipe
claude --container-toolchain list              # name, version, default, size, verified base
claude --container-toolchain remove java21
claude --container-toolchain verify [java21]   # rerun the checks on the current runtime image
```

- **Sources:** a toolchain is a relocatable directory tree, taken either from
  a path inside an OCI image referenced by `@sha256:` digest, or from a local
  archive with its SHA-256. The command never downloads archives.
- **Pulls:** pulling a missing image requires exact
  `CLAUDE_CONTAINER_MAINTENANCE=1`. Like image builds, the pull happens on the
  host, outside runtime filtering.
- **Extraction:** it rejects absolute paths, `..`, device nodes and links
  that leave the toolchain, and clears setuid and setgid bits.
- **Atomic changes:** changes take a library lock and replace directories
  atomically.
- **Check:** before accepting a toolchain, `add` runs the recipe's `check`
  command in the runtime image, without network and with the session's
  identity and hardening. A toolchain that needs a newer C library than the
  image's glibc fails here. The manifest records the base image from the
  installed `Containerfile`. If that base changes, the toolchain stays visible
  but loses its default environment until `verify` succeeds, and the launcher
  prints one warning naming it.

### Recipes

A recipe is a JSON file that the operator keeps and reviews:

| Key | Meaning |
| --- | --- |
| `schema`, `name`, `version` | `1`; `[a-z0-9][a-z0-9._-]*`; free version text |
| `source` | `{"image": "<ref>@sha256:<digest>", "path": "/abs/path"}` or `{"archive": "/abs/file.tar.xz", "sha256": "<hex>", "strip_components": 1}` |
| `path` | directories relative to the toolchain, added to `PATH` (default `["bin"]`) |
| `env` | variables: `{"toolchain": "<relative path>"}` or `{"value": "<literal>"}` |
| `requires` | other toolchains whose environment is loaded first |
| `notes` | short instructions shown to the agent in `toolchains.md` |
| `check` | command run in the runtime image before the toolchain is accepted |
| `default` | `true` adds the toolchain to new sessions' environment |

- **Protected variables:** recipes cannot set `PATH`, `HOME`, loader, proxy,
  CA, wrapper or credential variables, or any `XDG_` variable (a wrapper may
  place its state with them).
- **Default toolchains:** in new sessions, their `PATH` entries come **after**
  the image's. They never replace the runtime's own `node` or `python3`, which
  Claude Code and the image tools use.
- **Conflicts:** two default toolchains cannot share a command or a variable.
  Install a second version with `"default": false` and use it through its
  `env.sh`.
- **Writable locations:** `/claude-home` is read-only in shared-state mode, and
  `/tmp` is writable but `noexec`. Point caches to `/tmp` with literal values,
  and use `notes` to tell the agent when a tool must run files from a
  workspace directory.
- **Dependency downloads** (Maven, npm, pip, Cargo, Go modules) need network
  access that provider and offline modes do not grant. Provide dependencies in
  the workspace, or use an unrestricted session.

The examples below were verified with the versions, digests and checksums
shown. See [the validation record](docs/validation.md#toolchain-library-2026-11-13).

The recipes are in [`docs/toolchains/`](docs/toolchains/), and download
sources are listed in `docs/toolchains/sources.json`:

| Recipe | Version | Source | Default | Notes |
| --- | --- | --- | --- | --- |
| `java21.json` | Temurin 21.0.13 | image `eclipse-temurin@sha256:0a3f3298…`, `/opt/java/openjdk` | yes | `JAVA_HOME` |
| `maven3.9.json` | 3.9.16 | image `maven@sha256:99e61abc…`, `/usr/share/maven` | yes | requires `java21`; local repository in `/tmp/m2`; harmless jansi warning |
| `go.json` | 1.27.4 | image `golang@sha256:4fa7c968…`, `/usr/local/go` | yes | `GOTOOLCHAIN=local`; caches in `/tmp`; `go test` needs `GOTMPDIR` in the workspace |
| `node24.json` | 24.22.3 | archive `node-v24.22.3-linux-x64.tar.xz` | no | the image's Node.js 22 stays first |
| `python3.13.json` | 3.13.18 | archive python-build-standalone `20261110` `install_only` | no | the image's `python3` stays first; virtual environments in the workspace |
| `rust.json` | 1.100.0 | image built from `rust-musl.Containerfile` | yes | target `x86_64-unknown-linux-musl` linked by `rust-lld`; crates with build scripts or procedural macros fail |

Notes on using the recipes:
- **Archive recipes:** download the file, check it against the recipe's
  SHA-256, and set `archive` to its absolute path.
- **Rust:** the runtime image has no C linker, so the recipe uses the musl
  target, whose startup files ship with Rust, and links with `rust-lld`. Build
  the image, then put its local digest in the recipe:

  ```bash
  podman build --tag localhost/sandbox-rust-musl:local \
      --file docs/toolchains/rust-musl.Containerfile docs/toolchains
  podman image inspect --format '{{.Digest}}' localhost/sandbox-rust-musl:local
  ```

`SANDBOX_TOOLCHAIN_EXAMPLES=1 bash tests/run-runtime.sh --network -k
documented_toolchain` downloads, pulls and builds all six, then checks them in
an offline session.

### Telling the agent

The wrapper never edits memory files or installs skills. The library contains
a generated `/toolchains/toolchains.md` with the usage rules and every
installed toolchain, plus a machine-readable `/toolchains/index.json`. Add one
line to the project's or your global `CLAUDE.md`:

```markdown
Read /toolchains/toolchains.md before using or looking for build tools.
```

The agent then runs a toolchain in one command with
`. /toolchains/<name>/env.sh && <command>`. This form also works for
toolchains added after the session started.

SELinux and AppArmor enforcement were not tested with the library mount. On
hosts that enforce them, profile the tools you add.

## Shared sandbox components and the agent profile

`network/` and `setup/` are shared with the sibling Codex, Antigravity, OpenCode
and Pi wrappers and are copied between them unchanged. They contain no
Claude-specific names. Every agent-specific value is declared in
`agent/profile.json`:
- the wrapper name and the `CLAUDE_CONTAINER_*` variable prefix;
- the `localhost/claude-*` images and `io.claude-container.*` labels;
- installation and state names;
- `/claude-home`, `CLAUDE_CONFIG_DIR`, `CLAUDE_YOLO` and `ANTHROPIC_API_KEY`;
- login assistance and the required hosts for each authentication method.

Provider policies are in `agent/policies/`. Inside containers the sandbox uses
neutral paths: `/opt/sandbox-egress`, `/run/sandbox-egress`,
`/tmp/sandbox-runtime` and the `sandbox-egress-guard` binary.

Each sibling pins its copy to an annotated `sandbox-ref-N` tag of this
repository. A shared change gets a new tag and reaches the siblings through
`tools/propagate.py`, as described in [docs/propagation.md](docs/propagation.md).

The profile and policy are protected installation inputs and part of the
qualification identity. After upgrading from a release that used
`network/policies/` or `claude-egress-guard`, rerun `--container-setup` (or
rebuild the guard, proxy and runtime images and rerun `--container-qualify`)
and restart running sessions. Restricted launches refuse the stale
qualification until then. Operator commands, variables and saved setup
preferences are unchanged. Only test-harness controls changed:
- `CLAUDE_TEST_TMPDIR` is now `SANDBOX_TEST_TMPDIR`;
- `CLAUDE_TEST_STATE_ROOT` is now `SANDBOX_TEST_STATE_ROOT`;
- `CLAUDE_RUNTIME_TESTS` is now `SANDBOX_RUNTIME_TESTS`;
- `CLAUDE_GUARD_TOOLCHAIN` is now `SANDBOX_GUARD_TOOLCHAIN`.

## Verification

```bash
bash -n claude-container.sh
python3 -m unittest discover -s tests -p test_wrapper.py -v
SANDBOX_RUNTIME_TESTS=1 python3 -m unittest discover -s tests -p test_runtime.py -v
bash tests/run-runtime.sh
git diff --check
```

Wrapper tests use synthetic HOME/state and a fake Podman, without host
credentials or a real engine. They need executable temporary storage with Unix
permissions; set `SANDBOX_TEST_TMPDIR` to a suitable native Linux directory when
`/tmp` is `noexec`. Runtime tests are opt-in and require a built image and a
rootless engine. The runner uses a disposable native Linux volume for state,
preserves host absolute paths, and removes only its own test resources; it can
also run the wrapper tests via `bash tests/run-runtime.sh --wrapper` when host
Python is unavailable. No automated test uses real credentials or paid model
requests. Image absence triggers a build; inspection errors stop startup rather
than causing an accidental rebuild. Explicit builds retain normal caching.
