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

## Build, Test, and Development Commands

Run these commands from the repository root:

```bash
./claude-container.sh --container-build  # Build or refresh the local image
./claude-container.sh                    # Start Claude in the current workspace
./claude-container.sh --container-shell  # Open a shell in the runtime image
bash -n claude-container.sh              # Validate Bash syntax
git diff --check                         # Detect whitespace errors
```

Host Podman is always required and its launch engine must verify as Linux and
rootless. Local use requires no API socket with delegation off; explicit same-host
Unix `CONTAINER_HOST` use verifies that launch service regardless of delegation.
Reject named connections and TCP/SSH contexts. Delegation requires the exact value
`CLAUDE_CONTAINER_PODMAN=1`. Select its endpoint by explicit
`CLAUDE_CONTAINER_PODMAN_SOCKET`, Unix `CONTAINER_HOST`, then
`${XDG_RUNTIME_DIR:-/run/user/<uid>}/podman/podman.sock`. Verify that exact endpoint
before image operations, requiring rootless `true` and an absolute reported host
socket path; bind the latter when the wrapper sees a remapped socket.

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
on changed shell scripts, and `git diff --check`. Wrapper tests use synthetic
HOME/configuration and fake Podman on executable native temporary storage;
`CLAUDE_TEST_TMPDIR` overrides the temporary directory. No real credentials or
remote Git repositories belong in tests.

With a built image and rootless engine, run `CLAUDE_RUNTIME_TESTS=1 python3 -m
unittest discover -s tests -p test_runtime.py -v` or `bash tests/run-runtime.sh`.
The latter uses disposable native state and same-host Unix service access;
`--wrapper` runs wrapper tests there if host Python is unavailable. Verify both
state modes, privacy failures, escaped symlinks, exact disabled socket values,
endpoint precedence/remapping, shell/build/worktree composition, all four
YOLO/socket combinations, engine errors, argument/stdin forwarding, name races,
exit codes, signals, and owned cleanup. Disabled delegation skips separate
endpoint checks, not mandatory launch-engine verification. Record runtime and
internal sandbox checks as passed, failed, or unavailable with versions.

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

Expose the host Podman API socket only with `CLAUDE_CONTAINER_PODMAN=1`.
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
host binds or add privileges to make an internal sandbox work.
