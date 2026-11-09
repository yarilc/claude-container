# Proposal

## Why

`pi-container` and `opencode-container` enforce controls this wrapper lacks:
- privilege dropping in every mode;
- bounded host resources (finding F2);
- refusal of sensitive workspace roots (finding F4);
- an optional session lifetime;
- pinned agent versions.

Wave 0 makes `claude-container` the reference sandbox, so it must match or exceed them before the cross-wrapper tag `sandbox-ref-2`. This change covers todo items B01–B05.

## What Changes

- **B01: drop privileges in every mode.** Unrestricted, shell and delegated sessions also use `--cap-drop=all` and `--security-opt=no-new-privileges`. Restricted sessions already do (N18). **BREAKING** for unrestricted sessions that relied on default container capabilities: any incompatibility is documented, and no capability is added back.
- **B02: explicit resource budgets.** Every agent container gets `--memory`, `--cpus` and `--pids-limit`:
  - set by `CLAUDE_CONTAINER_MEMORY_LIMIT` (default `4g`), `CLAUDE_CONTAINER_CPU_LIMIT` (default `2`) and `CLAUDE_CONTAINER_PIDS_LIMIT` (default `512`);
  - values are validated before any engine call;
  - every launch checks the configured budgets on the created container;
  - setup smoke, qualification and runtime tests check the effective cgroup v2 limits.

  **BREAKING**: sessions that used more than the defaults must raise the limits.
- **B03: refuse sensitive workspace roots.** The wrapper refuses to mount these as the writable workspace, including through `--container-git-worktree`:
  - `/`;
  - the caller's home;
  - system directories;
  - WSL drive roots such as `/mnt/c`.

  The check compares physical paths and runs before image or engine operations. `CLAUDE_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1`, an exact opt-in, overrides it with a visible warning.
- **B04: optional session lifetime.** `CLAUDE_CONTAINER_RUN_TIMEOUT` (seconds, disabled by default) sets the native Podman container `--timeout`.
  - It is independent of the 20-second shutdown budget.
  - Exit status reporting is preserved.
  - A reached limit is reported on stderr.
- **B05: pinned image inputs.**
  - The `Containerfile` installs exact `@anthropic-ai/claude-code` and `@fission-ai/openspec` versions recorded in the repository.
  - The base image is pinned by digest.
  - A unit check keeps the pinned CLI version equal to the version recorded in the network policy's `tested.cli`.
  - Updates follow a documented maintenance procedure under `CLAUDE_CONTAINER_MAINTENANCE=1`, recorded in `docs/validation.md`.
- **Setup-managed budgets:**
  - `--container-setup` asks for memory, CPU, processes and session lifetime, with defaults `4g`/`2`/`512`/`0`;
  - the answers are saved as versioned preferences, and older preferences migrate with the defaults;
  - the managed launcher supplies them unless a variable is explicitly exported.
- **Qualification:** restricted qualification identities and setup smoke use the saved budgets and lifetime. Changing them requires requalification.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-isolation`:
  - drop capabilities and enable no-new-privileges in every mode, replacing the "unrestricted behavior is preserved" exemption;
  - add agent resource budgets.
- `workspace-mounts`: refuse sensitive physical workspace roots with an exact override.
- `container-launcher`:
  - optional session lifetime limit with status preservation;
  - qualification identity binds the budgets and lifetime;
  - help and environment documentation.
- `container-setup`: budget and lifetime questions, saved preferences supplied by the managed launcher, migration of preferences without budgets.
- `runtime-image`: pinned agent CLI, OpenSpec and base image, with the maintenance update procedure.

## Impact

- **`claude-container.sh`:**
  - environment validation;
  - workspace guard;
  - container arguments;
  - post-create budget inspection;
  - lifetime notice;
  - help text.
- **`network/qualification_records.py`, `network/qualification_probe.py`:**
  - the identity's `hardening` gains the agent budgets and lifetime;
  - the probe verifies the effective agent cgroup limits.
- **`setup/setup.py`, `setup/common.py`, `setup/smoke.py`:**
  - new questionnaire entries and setup plan lines;
  - preference schema version 2 with v1 migration;
  - managed environment entries;
  - smoke verifies zero capabilities, no-new-privileges and the saved effective budgets in every mode.
- **Shared code:** `network/` and `setup/` are shared with the sibling wrappers, so variable names come from the agent profile's environment prefix and the shared tests stay identifier-free.
- **`Containerfile`:** pinned versions and base digest.
- **Docs:**
  - README;
  - `docs/setup.md`, `docs/network-contract.md`, `docs/validation.md`;
  - `AGENTS.md` if it lists environment controls.
- **Tests:**
  - `tests/test_wrapper.py`, `tests/test_setup.py`, `tests/test_qualification.py`;
  - `tests/test_runtime.py`, `tests/test_network_runtime.py`;
  - a new pin-consistency check.
- **Existing installations:** must rerun `--container-setup` to deploy the protected wrapper and requalify.
- **Out of scope:**
  - image linting and scanning (B06);
  - capability renaming (B07).
