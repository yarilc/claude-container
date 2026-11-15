# Proposal

## Why

The cross-wrapper review of 2026-11-14 found that the shared code is identical
in every wrapper, but some session boundaries depend on code that each
launcher writes its own way:

- **H1 (toolchain variables):** `setup/toolchains.py` protects only each
  profile's prefix, configuration, approval and credential variables. It does
  not protect the variables the agent itself reads, such as
  `OPENCODE_PERMISSION`, `PI_OFFLINE`, `AGY_CLI_DISABLE_AUTO_UPDATE`,
  `CLAUDE_CODE_*` or `ANTHROPIC_BASE_URL`. Claude, Pi and Antigravity are safe
  today only because of the order of their `--env` options. OpenCode was not,
  and gets an immediate launcher fix in its own change
  (`protect-session-env-from-toolchains`).
- **M4 (working directory):** `toolchains.check()` starts the runtime image
  without `--workdir /`. On the Rocky lab host with a domain UID, Podman
  fails when it creates a missing `WORKDIR` under `--userns=keep-id`.
  `sandbox-ref-12` fixed this for qualification only. Claude's own
  `Containerfile` is also the only one that does not create `/workspace` in a
  build step.
- **M3 (state inside the workspace):** OpenCode, Pi and Antigravity refuse an
  isolated state directory that overlaps the workspace. Claude and Codex do
  not, so `CLAUDE_CONTAINER_STATE_DIR=$PWD` would put credentials inside the
  repository. Managed launches check writable mounts in shared code, which
  does not check this either.
- **M2 (signals):** Claude is the only wrapper that attaches with the default
  `--sig-proxy`, so a signal can reach the container twice, through the client
  and through the wrapper's own shutdown.
- **L2 (alignment tests):** `test_consistency_check_detects_a_mismatch` can
  never fail, and `test_wrapper_uses_every_profile_variable` accepts names
  that appear only in the usage text.

## What Changes

Shared code, published as `sandbox-ref-18`:

- **Agent-owned variables in the profile:** `agent/profile.json` gains an
  optional `native.protected_env` list of variable names and prefixes (ending
  in `_`). The profile loader validates it. `setup/toolchains.py` treats these
  names as profile variables: `add` rejects them, and `launch-env` leaves
  them out with one warning naming the toolchain.
- **Toolchain check in `/`:** `toolchains.check()` passes `--workdir /`.
- **No state inside the workspace:** the shared writable-mount check rejects
  an isolated state directory that is, contains or lies inside the workspace,
  so every managed launch enforces it.
- **Alignment tests:** the mismatch test runs the real consistency check on
  modified text and expects it to fail. The profile-variable test checks the
  launcher's code and its help text separately (see design.md).

Claude only:

- `agent/profile.json` declares Claude's own variables: the `CLAUDE_CODE_`
  and `ANTHROPIC_` prefixes, `DISABLE_TELEMETRY`, `DISABLE_AUTOUPDATER`,
  `DISABLE_ERROR_REPORTING` and `ENABLE_CLAUDEAI_MCP_SERVERS`.
- The launcher refuses an isolated state directory that overlaps the
  workspace, on direct launches too.
- The `Containerfile` creates `/workspace` in the package step. A
  `test_image_pins.py` check, ported from Codex, rejects a `WORKDIR` that no
  build step creates.
- `podman start` uses `--sig-proxy=false`, like the other four wrappers.

Out of scope, for later changes:

- Each adopter's adoption of `sandbox-ref-18` with its own `protected_env`
  values, and the ports of the overlap check (Codex) and of the lifecycle
  recovery and ownership check (Codex, Pi, Antigravity; OpenCode for the
  collision check).
- Credential forwarding (M1), including Claude's forwarding of
  `ANTHROPIC_API_KEY` to the account profile.
- `propagate.py` checklist (M6), Pi CI (M5) and the documentation fixes
  (L1, L3).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `toolchain-library`: profile variables include the agent's own variables
  and prefixes declared in the profile. The toolchain check starts in `/`.
- `persistent-state`: an isolated state directory must not overlap the
  workspace.
- `runtime-image`: every `WORKDIR` is created by a build step.
- `container-launcher`: the attached client does not proxy signals; the
  wrapper alone forwards them.

## Impact

- Shared: `network/agent_profile.py`, `setup/toolchains.py`,
  `setup/common.py`, `tests/test_agent_profile.py`,
  `tests/test_toolchains.py`, `tests/test_setup.py`,
  `tests/test_alignment.py`. Qualified code changes, so every restricted
  installation reruns `--container-setup` after adoption.
- Claude: `agent/profile.json`, `claude-container.sh`, `Containerfile`,
  `tests/test_wrapper.py`, `tests/test_image_pins.py`, `README.md`,
  `docs/network-contract.md`, `docs/validation.md`, the parity table.
- New annotated tag `sandbox-ref-18`.
