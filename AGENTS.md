# Repository Guidelines

## Project Structure & Module Organization

This repository contains a small, self-contained Podman wrapper for running
Claude Code:

- `claude-container.sh` is the entry-point script and owns argument parsing,
  volume mounts, user mapping, and Podman socket validation.
- `Containerfile` defines the Claude Code runtime image and its shell/tooling
  baseline.
- `README.md` documents setup, usage, persistence, and security boundaries.
- There are currently no separate source, test, or asset directories.

## Build, Test, and Development Commands

Run these commands from the repository root:

```bash
./claude-container.sh --container-build  # Build or refresh the local image
./claude-container.sh                    # Start Claude in the current workspace
./claude-container.sh --container-shell  # Open a shell in the runtime image
bash -n claude-container.sh              # Validate Bash syntax
git diff --check                         # Detect whitespace errors
```

The runtime requires a rootless Podman socket, for example:
`podman system service --time=0 unix:///run/user/$(id -u)/podman/podman.sock`.

## Coding Style & Naming Conventions

Use Bash with `set -Eeuo pipefail`, quote variables, and prefer explicit
arrays for commands with user-controlled arguments. Keep functions small and
fail with actionable messages. Use four-space indentation within Bash blocks,
lower-case `snake_case` for local variables, and upper-case names for
environment/configuration variables. Keep image and file names descriptive and
lowercase (`Containerfile`, `claude-container.sh`). Write documentation, code
comments, help text, and user-facing messages in English.

## Testing Guidelines

There is no test framework yet. Every script change must pass `bash -n` and
`git diff --check`; when Podman is available, verify `--container-help`, Claude
argument forwarding, image build, Claude startup, persistence of
`~/.claude`, and a child `podman run`. Avoid embedding credentials or relying
on a remote Git repository in tests.

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
