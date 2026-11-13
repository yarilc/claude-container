# Repository Guidelines

## Project Structure & Module Organization

This repository contains a small, self-contained Podman wrapper for running
Claude Code:

- `claude-container.sh` is the entry-point script and owns argument parsing,
  volume mounts, user mapping, and Podman socket validation.
- `Containerfile` defines the Claude Code runtime image and its shell/tooling
  baseline, including `nano` with `EDITOR` and `VISUAL` set to it. The image
  disables nano's history log in `/etc/nanorc`, because the home directory is
  read-only.
- `README.md` documents setup, usage, persistence, and security boundaries.
- `openspec/` holds the OpenSpec project: `specs/` for the durable capability
  specs (for example `host-ca-trust`) and `changes/` for in-flight changes.
  Archived changes live in `changes/archive/`.
- `tests/` contains synthetic wrapper checks and opt-in rootless runtime checks.
- `docs/validation.md` records verified environments and unavailable checks.
- `agent/profile.json` is the single source of Claude-specific values used by
  shared code: wrapper and variable names, images, labels, installation/state
  names, native home/command/configuration variables, authentication methods
  and their required provider hosts. `agent/policies/` holds the provider policies.
- `network/` contains preflight/snapshot validation, the profile loader,
  the restricted session helper (`session.py`: `prepare`, `start`,
  `agent-args`, `stop`), the standalone CONNECT proxy image, native IPC
  bootstrap, and agent-side relay. The wrapper calls the helper and never
  re-implements proxy lifecycle, guard arguments or proxy cleanup in-line.
- `setup/` contains host-only interactive preparation, declarative managed
  preferences, the exec-based launcher, a sandbox smoke check and the
  operator toolchain library (`setup/toolchains.py`, mounted read-only at
  `/toolchains`).

## Shared and agent-specific files

`network/`, `setup/` and the shared tests listed in `tests/test_alignment.py`
are copied unchanged between the Claude, Codex, Antigravity, OpenCode and Pi
wrappers. Never add an agent identifier (any of the profile's `identifiers`) to
them. Read agent-specific values from the profile, or pass them from host code
to in-container helpers. In-container paths are neutral: `/opt/sandbox-egress`,
`/run/sandbox-egress`, `/tmp/sandbox-runtime` and `sandbox-egress-guard`.

These files are per agent:
- `agent/`, `claude-container.sh`, `Containerfile` and `.containerignore`;
- the end-to-end tests: `test_wrapper.py`, `test_runtime.py`,
  `test_network_runtime.py` with `network_tls_fixture.py`,
  `test_setup_runtime.py`, `run-runtime.sh` and `image-smoke.sh`.

When a shared component needs a new agent-specific value, extend the profile
schema in `network/agent_profile.py` here first. Then tag the result and
propagate the shared files to the sibling wrappers with `tools/propagate.py`
(dry run first, then `--apply`), following `docs/propagation.md`; never edit a
shared file in a sibling. `tests/test_alignment.py` enforces the literal scan
and wrapper/profile consistency, and `tests/test_propagate.py` covers the tool.
- `docs/setup.md` documents guided installation, maintenance consent and rollback.
- `docs/network-contract.md` defines the shared mode and rollout contract;
  sibling wrappers remain independently unassessed.

## Build, Test, and Development Commands

Run these commands from the repository root:

```bash
CLAUDE_CONTAINER_NETWORK=unrestricted CLAUDE_CONTAINER_MAINTENANCE=1 ./claude-container.sh --container-build
CLAUDE_CONTAINER_NETWORK=unrestricted ./claude-container.sh
CLAUDE_CONTAINER_NETWORK=unrestricted ./claude-container.sh --container-shell
bash -n claude-container.sh              # Validate Bash syntax
git diff --check                         # Detect whitespace errors
```

Configured launches require host Podman and its launch engine must verify as
Linux and rootless. Unrestricted local use requires no API socket with delegation off; explicit same-host
Unix `CONTAINER_HOST` use verifies that launch service regardless of delegation.
Reject named connections and TCP/SSH contexts. Delegation requires the exact value
`CLAUDE_CONTAINER_PODMAN=1`. Select its endpoint by explicit
`CLAUDE_CONTAINER_PODMAN_SOCKET`, Unix `CONTAINER_HOST`, then
`${XDG_RUNTIME_DIR:-/run/user/<uid>}/podman/podman.sock`. Verify that exact endpoint
before image operations, requiring rootless `true` and an absolute reported host
socket path; bind the latter when the wrapper sees a remapped socket.

Setup is the mandatory first step for new users. Ordinary launches require a
nonempty `CLAUDE_CONTAINER_NETWORK`, explicitly set by the operator or supplied
by the validated managed launcher. Unset/empty modes must stop with setup
guidance before runtime checks, engine queries or state creation; explicit empty
overrides must not restore saved defaults. Help, setup and standalone fixed
qualification retain their dedicated checks. Qualification alone keeps its
offline default and never admits a supplied application command. Maintenance
consent does not select a runtime mode. Offline cannot reach the Claude API.
Restricted sessions must use the static ABI-3
Landlock/additive-seccomp bootstrap before any application code. Keep fail-closed
per-session checks; never restore the superseded IP-only path.
Restricted modes require a verified
same-host Unix launch service with rootless Netavark/Podman >= 4.9, host Python 3,
and protected installed code outside all agent-writable mounts. Provider mode
requires a protected versioned policy/profile, private native host-path runtime
directory and immutable proxy image ID/digest. Never silently broaden support or
fall back to unrestricted networking. Exact maintenance opt-in is separate from
runtime policy and does not constrain host image pulls or build RUN traffic.
Native Linux and WSL2 x86_64 require usable Landlock ABI >= 3 and current protected
local enforcement qualification; exact kernel/server pins and upper bounds are
not admission rules. Preserve active SELinux/AppArmor without guaranteeing their
compatibility. Never disable policy or accept an unavailable required control.
Keep shared platform rules in protected code and validate qualification reports
against current boot, engine/backend/security, code/images, policy/profile, CA
and hardening. Unobservable active LSM identity requires requalification each
launch. Distinguish locally-qualified installations from exact release-measured
evidence; no exhaustive distribution matrix is required or implied.

## Coding Style & Naming Conventions

Use Bash with `set -Eeuo pipefail`, quote variables, and prefer explicit
arrays for commands with user-controlled arguments. Keep functions small and
fail with actionable messages. Use four-space indentation within Bash blocks,
lower-case `snake_case` for local variables, and upper-case names for
environment/configuration variables. Keep image and file names descriptive and
lowercase (`Containerfile`, `claude-container.sh`). Write documentation, code
comments, help text, and user-facing messages in English.

## Testing Guidelines

Run `python3 -m unittest discover -s tests -p test_wrapper.py -v`, `bash -n`
on changed shell scripts, and `git diff --check`. Run `test_image_pins.py`
after any `Containerfile` or `tested.cli` change; image inputs stay pinned and
change only through the maintenance procedure in `docs/validation.md`. Every
agent container drops capabilities and receives memory/CPU/process budgets in
all modes; never add a capability, and never drop a budget the engine can enforce
to make a tool work. A budget whose cgroup v2 controller the rootless engine does
not delegate (`Host.CgroupControllers`) is omitted, announced and bound into the
qualification identity; never require host changes to delegate it. Wrapper tests use synthetic
HOME/configuration and fake Podman on executable native temporary storage;
`SANDBOX_TEST_TMPDIR` overrides the temporary directory. No real credentials or
remote Git repositories belong in tests.

With a built image and rootless engine, run `SANDBOX_RUNTIME_TESTS=1 python3 -m
unittest discover -s tests -p test_runtime.py -v` or `bash tests/run-runtime.sh`.
The latter uses disposable native state and same-host Unix service access;
`--wrapper` runs wrapper tests there if host Python is unavailable. Verify both
state modes, privacy failures, escaped symlinks, exact disabled socket values,
endpoint precedence/remapping, shell/build/worktree composition, all four
YOLO/socket combinations, engine errors, argument/stdin forwarding, name races,
exit codes, signals, and owned cleanup. Disabled delegation skips separate
endpoint checks, not mandatory launch-engine verification. Record runtime and
internal sandbox checks as passed, failed, or unavailable with versions.

Run `bash tests/run-runtime.sh --network-feasibility`, `--network-policy`, and
`--network` for the isolated topology, trusted policy/proxy tests, and production
wrapper acceptance. Use disposable native storage with protected ancestors for
policy path tests; do not weaken path checks for `/tmp`, `/codex-home`, or `/mnt/d`
permissions. Existing runtime regressions explicitly select unrestricted mode
and maintenance authorization. Authenticated API/account tests are separate from
automated synthetic state and require explicit credential/model-call approval.

`bash tests/run-runtime.sh --guard` builds/tests the static native bootstrap using
a prepared immutable toolchain image; see `network/README.md`. Link-time syscall
mocks are component instrumentation only and must never enter a shipped guard.
The recorded initial measured target is WSL 6.6.87.2 x86_64 with usable ABI 3;
other eligible installations must pass their own local gate. The guard adds a
restrictive in-process seccomp filter while preserving the standard OCI profile
and SELinux policy. Existing connected pairs may have private inert names, but
cannot listen, retarget or publish in host binds. Production guard checks and
mocked component checks are separate. Record the WSL IP/IPC/proxy gate separately
from authenticated compatibility; no kernel upgrade is required.
Run `bash tests/run-runtime.sh --qualification` for protected installed-path,
report, cancellation and concurrent gate acceptance. Ship fixed qualification
fixtures with protected releases, without syscall mocks or application-command
exceptions. Preserve per-launch enforcement even with a matching report.

Run `python3 -m unittest discover -s tests -p test_setup.py -v` or
`bash tests/run-runtime.sh --setup` for synthetic setup/PTY checks. The opt-in
`bash tests/run-runtime.sh --setup-runtime` uses disposable native installation
and state with the existing same-host service and prepared images. It must not
enable real user services, read real credentials or send model requests. Record
real systemd activation/login as unavailable unless explicitly exercised.
Keep help independent of setup preferences, strict declarative JSON outside all
writable mounts, exact maintenance consent and last-working-release rollback.

Changes to host CA handling must also verify both modes: with
`CLAUDE_CONTAINER_TRUST_HOST_CA` unset, no CA mount or CA variables are
present; with it set to `1`, the bundle is mounted read-only at
`/claude-home/ca/bundle.pem` and the four CA variables point at it.

Without Podman, stub `podman` on `PATH` and run a copy of the script to check
the assembled arguments and the validation errors. `/tmp` may be mounted
`noexec`, so put stubs in a non-`noexec` directory and remove them afterwards.

## Commit & Pull Request Guidelines

The repository history is minimal, so use concise imperative commit subjects,
for example `Add Podman socket validation`. Keep each commit focused. Pull
requests should explain behavior changes, list verification commands, call out
security or mount changes, and update `README.md` when usage changes.

## Security & Configuration

Treat `~/.claude` and the Podman socket as sensitive. Do not copy credentials
into the image, broaden mounts unnecessarily, or add `--privileged`. Preserve
the host workspace's absolute path so containers launched by the host Podman
service can resolve child bind mounts correctly. Claude configuration is
intentionally writable because it contains its credentials and session state.

Expose the host Podman API socket only with `CLAUDE_CONTAINER_PODMAN=1` and
explicit `CLAUDE_CONTAINER_NETWORK=unrestricted`. Reject exact socket opt-in
in offline/provider modes before image/resource operations.
This grants control over containers, volumes, and additional host bind mounts
available to the service user, beyond the selected workspace.

Host CA trust is opt-in. Mount only the selected CA bundle file, read-only, at
`/claude-home/ca/bundle.pem`. Never mount the host certificate directory
(`/etc/ssl/certs/`), and never make it writable from the container.

Keep `~/.claude`/`CLAUDE_CONFIG_DIR` and shared host OpenSpec configuration as
the default. Nonempty `CLAUDE_CONTAINER_STATE_DIR` selects an isolated writable
home and conflicts with nonempty host `CLAUDE_CONFIG_DIR`. Create private state,
validate ownership/access/modes, and reject isolated configuration paths escaping
that home. Do not recursively repair permissions or import credentials. Keep
`noexec` tmpfs and standard seccomp/SELinux policy; do not automatically relabel
host binds or add privileges to make an internal sandbox work. Agent
containers keep automatic read-only tmpfs provisioning only so a terminal can
attach. The engine provides `/dev` and its `devpts`; do not mount either
explicitly, because an explicit `devpts` gets `ptmxmode=000` and no
pseudo-terminal can be opened. Override `/dev/shm` with an empty read-only
tmpfs, and add no other writable provisioned path.

Provider tunnels require trusted-proxy initial TLS 1.2/1.3 ClientHello inspection
and exact normalized SNI/CONNECT binding before forwarding client bytes. After a
TLS 1.3 HelloRetryRequest the retried ClientHello is bound the same way; client
bytes stay held until the upstream's first handshake message is classified.
TLS 1.2 renegotiation is encrypted and remains an accepted, documented limitation.
Reject missing/malformed/mismatched SNI, non-TLS, ECH including GREASE, limits and absolute
timeouts without unchecked fallback. Require `tls-clienthello-sni-v2` (defined once in
`network/revisions.py`) in protected
manifest/readiness identities; old images must fail before agent execution.
Preserve end-to-end certificate validation. This does not prove exclusive
Anthropic application access: encrypted HTTP Host, shared services and provider
forwarding remain opaque, and allowed services can receive data. Run parser and
proxy suites (`test_tls_client_hello.py`, `test_tls_proxy.py`), then controlled
shared-address TLS acceptance through the production guard, relay and proxy.
Record zero-byte rejection, positive controls, both profile inventories and
actual target/environment evidence separately from historical/authenticated
results. Include parser inputs in protected setup releases and image builds.
