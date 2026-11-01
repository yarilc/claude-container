# Proposal

## Why

The wrapper leaves five documented runtime and build behaviors dependent on permissive endpoint parsing, inherited defaults, or an unnecessarily broad process scope. Making these choices explicit closes the gaps in `todo.md` while retaining the existing rootless, state, and delegation boundaries.

## What Changes

- Reject Unix launch endpoints without a socket pathname, including `CONTAINER_HOST=unix:///`, before querying Podman.
- Explicitly remove container `CONTAINER_HOST` when delegation is disabled, including values supplied by image or engine defaults.
- Disable automatic read-only tmpfs provisioning and explicitly mount `/tmp`, `/run`, and `/var/tmp` with constrained, ephemeral storage; retain the existing `/tmp` and `/run` limits.
- Restrict the private creation umask to state-directory creation, preserving the caller's umask for subsequent host commands.
- Add a restrictive `.containerignore` that excludes repository metadata, local credentials/state, caches, and unrelated content from builds.
- Add regression and opt-in runtime checks and update affected help, README, and validation records.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-launcher`: Reject pathless Unix launch endpoints before engine queries and require a minimal, filtered build context for automatic and explicit builds.
- `container-podman-access`: Require container `CONTAINER_HOST` to be absent when delegation is disabled, even if defaults define it.
- `container-isolation`: Require explicit temporary mounts, including `/var/tmp`, with automatic read-only tmpfs disabled.
- `persistent-state`: Limit private directory-creation umask changes to state operations without claiming that host umask determines container file modes.

## Impact

Implementation will affect `claude-container.sh`, a new `.containerignore`, `tests/test_wrapper.py`, `tests/test_runtime.py`, build-context acceptance coverage, `README.md`, and `docs/validation.md`. No new runtime dependency or user option is planned. Runtime tool provisioning in `Containerfile`, existing host CA handling, workspace selection, exact delegation opt-in, and standard security policies remain unchanged. `/var/tmp` gains an explicit size limit and `noexec`; endpoint and environment handling become stricter.

## Non-goals

Do not change Claude's internal sandbox, add privilege or policy bypasses, set a new container umask, migrate credentials, synchronize main specifications, or resolve unrelated archived acceptance tasks. Reference implementations named in the backlog are not prerequisites or evidence of Claude runtime compatibility.
