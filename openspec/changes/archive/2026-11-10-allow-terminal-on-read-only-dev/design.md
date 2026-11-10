# Design

## Context

Agent containers run with `--read-only --read-only-tmpfs=false` and
explicit `noexec` tmpfs mounts on `/tmp`, `/run` and `/var/tmp`, plus the
read-only `/run/secrets` mask. Lab-host probes (Podman 5.8.0, crun 1.27)
showed:

| Arguments | TTY start | `/dev` | `/dev/shm` |
|---|---|---|---|
| `--read-only-tmpfs=false` (current) | fails: unlink `/dev/console` | ro | ro |
| `--read-only` only | ok | rw, exec | rw, noexec |
| `=false` + own `/dev` tmpfs | fails: create fails, no `/dev/pts` | forced ro | ro |
| own `/dev` tmpfs, no `devpts` | fails: open `/dev/ptmx` | rw, noexec | ro mask |
| own `/dev` tmpfs + `devpts` + ro `/dev/shm` | ok | rw, noexec | ro mask |

The last combination also attaches a TTY on the development host
(Podman 4.9.3, crun 1.14.1), where `/dev` stays read-only. In both cases the
explicit `/tmp`, `/run` and `/var/tmp` mounts keep their own options.

## Goals / Non-Goals

**Goals:**
- Interactive launches work on Podman 5 with crun 1.27 without host changes.
- No new executable writable path, and no writable `/dev/shm`.

**Non-Goals:**
- Changing the provider proxy or the qualification gate containers. They
  never attach a terminal and keep `--read-only-tmpfs=false`.
- Making `/dev` read-only on Podman 5. The runtime needs it writable to
  replace `/dev/console`.

## Decisions

- **Re-enable automatic provisioning and override every target.** Podman
  forces `/dev` read-only whenever `--read-only-tmpfs=false` is set, even over
  a user `/dev` mount, so that flag cannot stay. Every other target it would
  provision (`/tmp`, `/run`, `/var/tmp`) is already mounted explicitly, and
  `/dev/shm` gets an explicit read-only mask.
  - Alternative rejected: dropping the flag alone. That leaves `/dev`
    writable and executable, and `/dev/shm` writable.
- **Own `/dev` tmpfs `rw,nosuid,noexec,mode=755,size=65536k`.** This matches
  Podman's default `/dev` size and mode and adds `noexec`.
  - Alternative rejected: adding `nodev`. Device nodes are runtime bind
    mounts with their own flags, so `nodev` buys no confinement here, and it
    was not exercised on the target.
- **Explicit `--mount type=devpts,destination=/dev/pts`.** A user `/dev`
  mount makes Podman drop its own `devpts`. The explicit mount restores it
  with the same mapped `gid`, `mode=620` and `ptmxmode=666`.
- **Apply to every agent container, with or without a TTY.** A single
  layout keeps the wrapper and its tests simple, and the identity does not
  depend on whether stdin is a terminal.
  - Alternative rejected: switching only for TTY launches. That would give
    two layouts to test and document.
- **`/dev/mqueue` is no longer mounted.** It is absent under the current
  flags as well, so nothing that works today is removed.

## Risks / Trade-offs

- [`/dev` is agent-writable on Podman 5] → It is `nosuid,noexec` and capped
  at 64 MiB, which counts toward the memory budget where that budget is
  enforced. Without capabilities no device nodes can be created. The
  workspace and state are already writable. Document the relaxation.
- [A future Podman could force `/dev` read-only even without the flag, or
  stop honoring the user `/dev` mount] → Wrapper tests pin the arguments,
  and the lab host records the observed mounts. A regression shows up as the
  same startup error, never as a silent fallback.
- [The guard does not inspect `/dev`] → The guard only requires `/dev/null`
  to be a character device, which still holds. Restricted-mode enforcement is
  unchanged.

## Migration Plan

The change is wrapper-only. Rerunning `--container-setup` installs the new
release; no image rebuild is required. Rollback is the previous release.
