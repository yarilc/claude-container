# Design

## Context

See `proposal.md` for the motivation. The current state that shapes the approach is below.

- **Unrestricted sessions:** `claude-container.sh` builds one `container_args` array. Unrestricted sessions get no hardening. Restricted sessions get `--cap-drop=all`, `--security-opt=no-new-privileges`, `--network=none` and private PID/IPC from the shared helper `network/session.py agent-args`. The help text and the `container-isolation` spec state that unrestricted sessions keep their existing arguments.
- **Proxy model to reuse:** proxy budgets (`--pids-limit=128 --memory=256m`) are already verified twice:
  - `podman inspect` checks the configured HostConfig;
  - `network/proxy_hardening.py probe` checks the effective cgroup v2 values in a private cgroup namespace (`/proc/self/cgroup == 0::/`).
- **Qualification identity:** `network/qualification_records.py` builds an identity with a fixed `hardening` entry that describes the proxy. The probe in `network/qualification_probe.py` already asserts zero capabilities, no-new-privileges and seccomp mode 2 inside the agent container.
- **Managed launcher:** `setup/launch.py` passes the caller's environment through to the wrapper. `runtime_environment()` fills only the saved settings that are absent from the environment. Preferences (`setup.json`) have an exact field set and `schema_version == 1`.
- **Shared code:** `setup/` and `network/` are shared unchanged with the four sibling wrappers. Variable names must be derived from the profile (`PROFILE.env('MEMORY_LIMIT')`), never written as literals.
- **Workspace path:** the wrapper resolves the workspace (`pwd -P`, then the parent in worktree mode) only after the engine checks. The missing-setup refusal must stay first (existing `container-launcher` requirement).
- **Unpinned image:** the `Containerfile` installs `@anthropic-ai/claude-code` and `@fission-ai/openspec@latest` unpinned on `node:22-bookworm-slim`. The tested versions are CLI 2.1.316 (recorded in `agent/policies/default.json` `tested.cli`) and OpenSpec 1.16.0.
- **Legacy unrestricted installations:** these may run without host Python, so per-launch checks for unrestricted mode must stay in Bash.

## Goals / Non-Goals

**Goals:**
- One agent-hardening baseline shared by every mode, with budgets proven by measurement rather than flags.
- Fail-closed validation of every new variable before engine calls.
- Reproducible image inputs whose CLI version is mechanically tied to the policy evidence.

**Non-Goals:**
- Limiting persistent workspace or state disk usage.
- Hash-pinning transitive npm dependencies or adding a lockfile.
- Changing proxy budgets, delegation authority or network policy.
- Image linting and scanning (B06) and capability renaming (B07).

## Decisions

### D1. Single change, grouped tasks

**Choice:** B01–B05 ship together, as requested.

**Why:** they share the wrapper argument block, the qualification identity, setup smoke and one requalification for operators.

**How:** tasks are grouped per item so each can be verified separately.

### D2. Base hardening in the wrapper for every mode

**Choice:** the wrapper adds `--cap-drop=all`, `--security-opt=no-new-privileges` and the three budget flags to `container_args` for all modes.

**Why:** it keeps the baseline in one visible place.

**Restricted mode:** the shared helper's own flags stay unchanged. Duplicated flags are harmless and keep the helper self-contained for sibling wrappers.

**Rejected:** moving the flags into the helper only. That would leave unrestricted mode, which never calls the helper, unhardened.

**Alignment guard:** the shared `tests/test_alignment.py` rejected any `--pids-limit` in the wrapper to keep proxy lifecycle out of it. The pattern is narrowed to the proxy value `--pids-limit=128`, so the agent budget is allowed while an inlined proxy creation is still detected. The four budget suffixes join the profile's derived environment names, so shared setup code addresses them through `PROFILE.env()`.

### D3. Budget formats and normalization

**Accepted values:**

| Variable | Default | Format |
|---|---|---|
| `CLAUDE_CONTAINER_MEMORY_LIMIT` | `4g` | positive integer with unit `k`, `m` or `g` (case-insensitive), normalized to bytes |
| `CLAUDE_CONTAINER_CPU_LIMIT` | `2` | positive decimal with at most 3 fractional digits, normalized to NanoCpus (`value × 10^9`) |
| `CLAUDE_CONTAINER_PIDS_LIMIT` | `512` | positive integer at most 4194304 |

**Rejected values:**
- `0`, `-1`, `max`, empty-but-set values and unitless memory are rejected, so a budget cannot be disabled.
- A set-but-empty variable is an error. Only an unset variable selects the default.

**Where validation lives:**
- Bash validates in the wrapper.
- `network/agent_budgets.py` (protected, installed with the network code) normalizes for qualification.
- A table-driven unit test feeds the same accept and reject cases to both, so they cannot drift.

**Setup:** setup imports the same `network/agent_budgets.py` to validate answers and saved preferences.

**Rejected:** a single Python validator. Unrestricted installations may lack host Python.

### D4. Per-launch configured check, measured effective check

**Every launch:** after `podman create` and before `podman start`, the wrapper runs `podman inspect --format '{{.HostConfig.Memory}} {{.HostConfig.NanoCpus}} {{.HostConfig.PidsLimit}}'`. It compares the result to the normalized budgets. On a mismatch it removes only its owned container and exits non-zero. The check is bounded by `timeout` and needs no host Python.

**Effective values:** these are read inside the agent container, which needs a running process:
- **Setup smoke (every mode):**
  - requires `/proc/self/cgroup == 0::/`;
  - reads `memory.max`, `pids.max` and `cpu.max` (`<quota> <period>`, with quota/period equal to the CPU value);
  - requires zero capability sets and `NoNewPrivs: 1`.

  Setup passes the expected normalized values as smoke arguments.
- **Restricted qualification probe:** performs the same reads, comparing them with the identity values.
- **Runtime tests:** cover the defaults and overrides in each mode.

**Rejected:** a per-launch `exec` probe before the application starts. It would require a second process in the agent container before the guard or entrypoint runs, which would change the restricted bootstrap contract.

### D5. Qualification identity

`hardening` gains an `agent` entry: `{capabilities: [], no_new_privs: true, memory: <bytes>, nano_cpus: <int>, pids: <int>, timeout: <seconds or 0>}`.

**Where the values come from:** the effective environment, which for managed launches is filled from the saved preferences (D9).
- `qualify.py check` (per launch) computes the entry from that environment.
- The setup gate and `--container-qualify` compute it the same way, and their probe verifies the effective values.

So setup qualifies exactly the saved values, and only an explicit export that differs from them triggers requalification.

**Effect:** existing reports no longer match and need requalification, which is the intended migration. The proxy entry is unchanged.

**Timeout binding:** the timeout is bound as the todo requires. It does not affect enforcement, but it keeps the qualified launch configuration exact.

### D6. Session lifetime

**Setting:** `CLAUDE_CONTAINER_RUN_TIMEOUT=N` (N ≥ 1) adds `--timeout N` to `podman create`. `0`, unset or empty adds nothing.

**Exit handling:**
- The wrapper records `SECONDS` immediately before `podman start`.
- If the client exits non-zero and the elapsed time is at least N, it prints `session lifetime limit reached (N s)`.
- The exit status is never rewritten.
- Proxy cleanup runs through the existing EXIT trap and 20-second shutdown budget.

**Engine support:** `--timeout` support is checked on the measured Podman versions (task 4.x). If an unrestricted engine lacks it, `podman create` fails with its own diagnostic. No silent fallback is used.

**Rejected:** a host-side `timeout` wrapper around `podman start`. It would kill the client, not the container, and would overlap the signal-forwarding logic.

### D7. Workspace guard placement and set

**Placement:** the guard runs after the missing-setup refusal and environment validation, and before `command -v podman`. Workspace and parent selection move earlier for this.

**Comparison:** the guard compares the physical `workspace_mount` against:
- `/` and the physical `$HOME`;
- the fixed system list in the spec, including `/tmp`;
- `^/mnt/[A-Za-z]$`.

An unresolvable `HOME` fails closed with a message.

**Override:** only `CLAUDE_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1` permits a refused path, with a stderr warning.

**Setup and qualification:** the qualification gate already uses private temporary workspaces. Setup smoke and login used the directory setup was started from, which could be the refused home. They now run in a private temporary workspace under `${XDG_CACHE_HOME:-~/.cache}`; a private `/tmp` is not used because bind sources must exist at the same path for the engine.

**Rejected:** refusing ancestors of the home in general. It is too broad on systems with unusual homes. `/` and `/home` cover the common cases.

### D8. Image pins

**Recipe:**
- `ARG CLAUDE_CODE_VERSION=2.1.316` and `ARG OPENSPEC_VERSION=1.16.0`;
- `FROM docker.io/library/node:22-bookworm-slim@sha256:<digest>`, with the digest captured under maintenance during implementation;
- `npm install -g --omit=dev "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" "@fission-ai/openspec@${OPENSPEC_VERSION}"`;
- `ENV DISABLE_AUTOUPDATER=1` in the image, so no mode can install a newer CLI into writable state.

**Unit test (new `tests/test_image_pins.py`):**
- parses the recipe;
- rejects unpinned specifiers, `@latest` or a tag without a digest;
- requires `CLAUDE_CODE_VERSION` to equal the leading version in the policy's `tested.cli`.

**Where versions live:** the `Containerfile` is the single source. The wrapper never passes `--build-arg`, so the defaults are authoritative.

**Rejected:** a separate `.version` file as in Pi. It adds a second source without benefit, because the build already reads the `Containerfile`.

### D9. Setup-managed budgets and preference schema 2

**Questions:** after the worktree question and before the CA question, setup asks:
- `Agent memory limit` (default `4g`);
- `Agent CPU limit` (default `2`);
- `Agent process limit` (default `512`);
- `Session lifetime in seconds, 0 disables` (default `0`).

Each answer is validated with `agent_budgets.py` and asked again on error. The setup plan prints all four.

**Preferences:**
- `setup.json` gains `memory_limit`, `cpu_limit`, `pids_limit` and `run_timeout` as canonical strings, and `schema_version` becomes 2.
- `load()` accepts exactly the v1 field set and upgrades it in memory with the defaults. Anything else outside v2 is rejected.
- `save()` writes v2 only.
- Old releases keep their own v1 files, so rollback is unaffected.

**Launch and smoke:**
- `runtime_environment()` adds the four variables to `selected`, so explicit exports keep precedence, including for `overrides=False` cleanup.
- Smoke receives the normalized saved values as arguments.

**Rejected:**
- Keeping budgets environment-only: smoke and qualification would not match the values actually used.
- Storing them outside `setup.json`: a second preference file would need its own trust checks.

## Risks / Trade-offs

- **[CPU controller not delegated to the rootless user]** The engine may reject or ignore `--cpus`. → Setup smoke and the per-launch inspection fail closed with a message about cgroup v2 controller delegation. The WSL target is measured first (task 2.x). If `cpu` is unavailable there, stop and report before weakening anything.
- **[4 GiB / 512-process defaults too small for heavy builds]** → The limits are configurable and documented. Raising them requires requalification only in restricted mode.
- **[Dropping capabilities breaks a tool in unrestricted mode]** Candidates: package managers that `chown`, and Claude's internal sandboxing. → Measure Claude, Bash, Git, OpenSpec, the delegated Podman client and the Bubblewrap probe before and after. Document failures and do not re-add capabilities. Podman's default capability set already excludes `CAP_SYS_ADMIN`, so namespace-based tools are not expected to change.
- **[Transitive npm dependencies remain unpinned]** → Accepted. The resulting image is immutable and bound by ID in qualification, and rebuilds happen only under maintenance.
- **[Lifetime notice heuristic]** A non-zero exit at or after N seconds that was not caused by the timeout is reported as reached. → The status is unchanged, and the wording says "limit reached", not a cause.
- **[An exported budget variable overrides the saved value]** This invalidates qualification in restricted mode. → The requalification message names the hardening settings. The docs recommend changing budgets by rerunning setup.
- **[Preference schema bump]** → v1 is accepted only through the exact-field upgrade. Unknown fields and versions still fail. Tests cover v1 upgrade, v2 round-trip and rejection.

## Migration Plan

1. Implement and pass the credential-free suites in the sandbox where possible. Host runs are authoritative.
2. Rebuild the image under `CLAUDE_CONTAINER_MAINTENANCE=1`, then confirm the CLI and OpenSpec versions and the base digest.
3. Operators rerun `--container-setup`. It proposes the default budgets for v1 preferences. The new protected release (schema 2 preferences), smoke and qualification activate atomically, and a failed smoke keeps the previous release.
4. **Rollback:** reactivate the previous release through setup, or check out the previous commit and rerun setup. Old reports remain bound to the old identity.

## Open Questions

- The exact base image digest, captured during implementation from the currently tested `node:22-bookworm-slim`.
- Resolved during implementation: base digest `sha256:4b150b48b4116e2a22f2c39cc27025fbf4f153e2078fd3b14d159fdb5c7279da` (the locally prepared `node:22-bookworm-slim`, created 2026-10-28). A timeout-stopped container makes both `podman run` and `podman start --attach` return 255 on client 4.3.1/server 4.9.3, with container `ExitCode` -1.
