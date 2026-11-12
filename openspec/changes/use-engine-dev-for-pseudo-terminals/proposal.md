# Proposal

## Why

The agent device layout from `sandbox-ref-11` mounts its own `/dev` tmpfs
and an explicit `--mount type=devpts,destination=/dev/pts`. That `devpts`
takes the kernel defaults `mode=600,ptmxmode=000`, so no process in a
session can open a pseudo-terminal: `pty.openpty()` fails with "out of pty
devices". Antigravity found the defect because agy runs tool commands in a
PTY. The fix there, which passed the operator's tests on this host, the
Rocky Linux 9 lab host and the newer WSL host, leaves `/dev` to the engine.

This reproduces in the Claude image on this host, on Podman 4.9.3:

- with the explicit layout, `/dev/pts` is `mode=600,ptmxmode=000` and the
  allocation fails;
- with the engine's `/dev`, `/dev/pts` is `mode=620,ptmxmode=666` and
  `/dev/pts/0` opens.

Interactive shell tools such as `script`, `expect` or `tmux`, and any tool
the agent runs in a PTY, need this. The reference launcher should be
corrected before Codex, OpenCode and Pi copy the fix.

## What Changes

- **Launcher (`claude-container.sh`):**
  - remove the explicit `--tmpfs '/dev:rw,nosuid,noexec,mode=755,size=65536k'`
    and `--mount type=devpts,destination=/dev/pts`;
  - keep `--read-only`, automatic read-only tmpfs provisioning (no
    `--read-only-tmpfs=false`), the empty read-only `/dev/shm` and the
    `/run/secrets` mask;
  - the engine then provides `/dev` and its `devpts`.
- **Tests:**
  - the wrapper assertions require no explicit `/dev` or `devpts` mount,
    and still require the `/dev/shm` and `/run/secrets` masks;
  - a new runtime test opens a pseudo-terminal inside a session and checks
    that `/dev/shm` and `/run/secrets` are empty and read-only.
- **Documentation:** `README.md`, `AGENTS.md` and a validation record in
  `docs/validation.md`.
- **BREAKING (policy):** on Podman 5 `/dev` is the engine's writable tmpfs
  without `noexec`. On Podman 4.9 it stays read-only. The requirement
  "Terminal-compatible device mounts", with its scenario "Executables
  cannot run from /dev", is removed and replaced. OpenSpec cannot drop a
  single scenario from a modified requirement.
- **Unchanged:**
  - the proxy container keeps `--read-only-tmpfs=false`;
  - `/tmp`, `/run` and `/var/tmp`;
  - shared code under `network/` and `setup/`. No new reference tag is
    needed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-isolation`:
  - removes "Terminal-compatible device mounts";
  - adds "Engine-provided device mounts allow pseudo-terminals";
  - the explicit temporary mounts no longer include `/dev` and `/dev/pts`.

## Impact

- `claude-container.sh`, `tests/test_wrapper.py`, `tests/test_runtime.py`.
- `README.md`, `AGENTS.md`, `docs/validation.md`.
- **BREAKING (installation):** the qualification identity binds the
  launcher digest (`code_files` includes the wrapper), so restricted
  installations rerun `--container-setup`. The runtime image is unchanged,
  so no image rebuild is needed.
- Follow-up changes apply the same fix in Codex, OpenCode and Pi.
