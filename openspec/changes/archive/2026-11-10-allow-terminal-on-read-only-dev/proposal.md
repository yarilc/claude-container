# Proposal

## Why

On the lab host (Rocky 9, Podman 5.8, crun 1.27) every interactive launch
fails before the agent starts: `crun: unlink /dev/console: Read-only file
system`. With `--read-only --read-only-tmpfs=false`, Podman 5 mounts `/dev`
read-only, and crun 1.27 must replace `/dev/console` to attach the terminal.
Setup reaches `Sandbox: ready`, but login and every TTY session fail.
Non-interactive launches and the qualification gate are unaffected. The fix
must not require host changes.

## What Changes

- Agent containers stop disabling automatic read-only tmpfs provisioning.
  They mount their own `/dev` tmpfs (`rw,nosuid,noexec`, mode 755, 64 MiB) and
  an explicit `devpts` at `/dev/pts`, which a user `/dev` mount otherwise
  drops.
- Agent containers mask `/dev/shm` with an empty read-only tmpfs, so
  re-enabling automatic provisioning does not add a writable `/dev/shm`.
- The explicit `/tmp`, `/run`, `/var/tmp` and `/run/secrets` mounts are
  unchanged. Automatic provisioning adds no other writable path, because
  each of its targets is already mounted explicitly.
- The change applies to every agent container in every mode, with or without
  a terminal. The provider proxy and the qualification gate containers never
  attach a terminal and keep `--read-only-tmpfs=false`.
- On Podman 5, agent-writable `/dev` is a documented relaxation: it is
  `noexec` and `nosuid`, no device can be created without capabilities, and
  its tmpfs counts toward the memory budget where enforced. On Podman 4.9,
  `/dev` stays read-only.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-isolation`: the ephemeral constrained temporary storage
  requirement no longer requires automatic read-only tmpfs provisioning to
  be disabled. A new terminal-compatible device mounts requirement covers the
  agent `/dev`, `/dev/pts` and `/dev/shm` mounts.

## Impact

- `claude-container.sh`: agent container arguments.
- `tests/test_wrapper.py`: assertions on `--read-only-tmpfs=false` and the
  new `/dev`, `/dev/pts` and `/dev/shm` mounts.
- `README.md`, `AGENTS.md` and `docs/validation.md`: describe the relaxation
  and record lab-host evidence.
- `network/`, `setup/` and the shared tests are unchanged, so nothing has to
  be propagated to the sibling wrappers for this change. Each sibling wrapper
  needs the same adaptation in its own launcher.
