# Proposal

## Why

Session termination can currently hang indefinitely on an application or Podman control call, and interruption during creation can lose the container ID needed for safe cleanup. Engine verification also accepts extra trailing blank records because Bash strips them before validation; both gaps are documented in the updated `todo.md`.

## What Changes

- Bound shutdown after TERM, INT, or HUP: forward the signal, wait briefly for graceful exit, then attempt forced removal of the owned container and terminate stalled local clients.
- Preserve recoverable container ownership during interrupted creation without deleting by a potentially reused workspace name.
- Bound shutdown control calls and client reaping; report cleanup errors while preserving application or signal exit status, including application exit 125.
- Preserve verification-output boundaries and command failure status. Accept one response record with an optional single LF terminator, and reject additional blank or nonblank records before image operations.
- Extend synthetic fault injection and rootless runtime checks; document shutdown limits, cleanup failure recovery, and stricter response validation in help, README, and validation records.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-launcher`: Recoverable ownership during creation, bounded shutdown and diagnostics, and strict single-record launch-engine verification.
- `container-podman-access`: Strict single-record delegated-socket verification without changing opt-in, endpoint selection, or reported host-path handling.

## Impact

Implementation targets `claude-container.sh`, `tests/test_wrapper.py`, `tests/test_runtime.py`, `README.md`, and `docs/validation.md`. GNU `timeout` from host coreutils becomes an explicit checked prerequisite for bounded control calls; help remains usable without it. Runtime image packages, build context, credentials, state layout, CA integration, temporary mounts, rootless requirements, and security policy are unchanged. No new public configuration option is planned.

## Non-goals

Do not limit normal application or build duration, retry malformed verification responses, change authentication or mounts, broaden privileges, or promise remote removal when the engine cannot be reached. Existing external-reference implementations are context, not substitutes for this project's acceptance tests. Main-spec synchronization, archive, and commit are separate later actions.
