# Design

## Context

`claude-container.sh` builds `container_args` around line 512. For every
agent and shell container (not the proxy) it passes:

- `--read-only`, with automatic read-only tmpfs provisioning enabled;
- `--tmpfs '/dev:rw,nosuid,noexec,mode=755,size=65536k'`;
- `--mount type=devpts,destination=/dev/pts`;
- `--mount type=tmpfs,destination=/dev/shm,ro=true`;
- `--mount type=tmpfs,destination=/run/secrets,ro=true`.

These were adopted in `sandbox-ref-11` (lab-host fixes) because Podman 5
mounts `/dev` read-only under `--read-only-tmpfs=false`, and crun 1.27
cannot then replace `/dev/console`. That failure came from
`--read-only-tmpfs=false`, which is already removed.

Measured on this host (Podman 4.9.3, image
`localhost/claude-code:setup-11645a29317d4621bf77bc5efc1437af`, with
`--read-only --userns=keep-id --cap-drop=all`):

| Layout | `/dev/pts` options | `pty.openpty()` | `/dev` |
| --- | --- | --- | --- |
| explicit `/dev` tmpfs and `devpts` (current) | `mode=600,ptmxmode=000` | "out of pty devices" | `ro,nosuid,noexec` |
| explicit `/dev`, `devpts` and `--device /dev/ptmx` | `mode=600,ptmxmode=000` | "out of pty devices" (the engine replaces `/dev/ptmx` with a `pts/ptmx` symlink) | `ro,nosuid,noexec` |
| engine `/dev` | `mode=620,ptmxmode=666,gid=…` | `/dev/pts/0` | `ro,nosuid` |

`--mount type=devpts,destination=/dev/pts,ptmxmode=0666` is rejected:
"ptmxmode: invalid mount option".

The terminal itself attached in the current layout, because the engine
allocates the console outside that `devpts`. Only pseudo-terminals opened
inside the session fail. The Claude CLI does not need one for its own
commands, so the defect showed no symptom here. Antigravity's agy does need
one, and the same fix passed its operator tests on all three hosts,
including Rocky Linux 9 on Podman 5 with crun 1.27.

Qualification digests the launcher (`code_files` includes
`profile.wrapper`), so any launcher change requires a new setup.

## Goals / Non-Goals

**Goals:**
- Pseudo-terminals work in every Claude and shell session.
- The terminal still attaches on Podman 5 with crun 1.27.
- `/dev/shm` and `/run/secrets` stay empty read-only masks.
- The reference is ready for Codex, OpenCode and Pi to copy.

**Non-Goals:**
- Shared code. `network/session.py` keeps `--read-only-tmpfs=false` for the
  proxy, which never attaches a terminal. No new reference tag.
- Changing `/tmp`, `/run` or `/var/tmp`.

## Decisions

1. **Leave `/dev` to the engine.** Remove the explicit `/dev` tmpfs and
   `devpts` and keep `--read-only` with automatic provisioning. The engine
   provides `/dev`, its device nodes and a `devpts` with `ptmxmode=666`. This
   is the layout Antigravity adopted and the operator verified.

   Alternatives considered:
   - Pass `ptmxmode` to the explicit `devpts`. Rejected: Podman refuses the
     option.
   - Add `--device /dev/ptmx` to the explicit layout. Rejected: the engine
     still links `/dev/ptmx` to `pts/ptmx`, and allocation fails.
   - Keep the explicit layout and accept no PTYs. Rejected: it breaks
     interactive tools, and the wrappers that copy the reference would
     inherit it.

2. **Keep the masks.** `/dev/shm` stays an empty read-only tmpfs, so
   automatic provisioning adds no writable shared memory. `/run/secrets`
   stays unchanged.

3. **Tests.**
   - `tests/test_wrapper.py`:
     - `assert_agent_dev_layout` requires `--read-only`, no
       `--read-only-tmpfs=false`, no `--tmpfs /dev…` and no `devpts` mount,
       and the `/dev/shm` mask;
     - the temporary tmpfs list (around line 1376) loses its `/dev` entry.

     The proxy assertion is unchanged.
   - `tests/test_runtime.py`: add `test_pseudo_terminals_and_device_masks`,
     adapted from Antigravity. In a shell session it runs `pty.openpty()`,
     checks that the slave is under `/dev/pts/`, and checks that
     `/dev/shm` and `/run/secrets` are empty and refuse writes. It must fail
     on the current layout and pass after the fix.

4. **Documentation.**
   - `README.md` "Authority and security policies": the engine provides
     `/dev` and a `devpts` that allows pseudo-terminals, and an explicit
     `devpts` would get `ptmxmode=000`. On Podman 5, `/dev` is writable but
     needs capabilities to create devices; on Podman 4.9 it is read-only.
   - `AGENTS.md`: the same rule. Do not mount `/dev` or `devpts`
     explicitly, only the `/dev/shm` mask.
   - `docs/validation.md`: a record with the table above, the test results
     and pending operator setups.

## Risks / Trade-offs

- [On Podman 5, `/dev` is writable and executable, which the explicit
  layout prevented] → `nosuid` remains, devices need capabilities that are
  dropped, and `/dev` is ephemeral. Writable, executable paths already
  exist in the workspace and state mounts. Recorded as a policy change.
- [A future engine change to `devpts` defaults] → The runtime PTY test
  detects it.
- [The Rocky Linux 9 host cannot be reproduced here] → The Antigravity
  operator test already confirmed this layout there. The operator reruns
  Claude setup and a session on each host.

## Migration Plan

1. Merge on `main` after validation. The operator pushes it.
2. On each host, run `--container-setup` (the launcher digest changed).
3. Rollback: revert the merge and rerun setup.
4. Follow-up changes in Codex, OpenCode and Pi apply the same launcher,
   test and documentation edits.
