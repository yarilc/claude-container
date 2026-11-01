# Tasks

## 1. Implement and document conditional Podman access

- [x] 1.1 Add exact-value `CLAUDE_CONTAINER_PODMAN=1` handling in `claude-container.sh`, gate socket resolution/validation, and append the socket mount and `CONTAINER_HOST` together only when enabled. Verify `bash -n claude-container.sh` passes and inspect captured launch arguments for enabled and disabled sessions.
- [x] 1.2 Verify the access matrix using host Podman or an isolated temporary `podman` stub on an executable PATH: unset, empty, `0`, `true`, `yes`, `01`, and an unexpected value omit both socket mount and `CONTAINER_HOST`; exact `1` includes both with a valid socket; missing/non-socket paths fail only when enabled and report an actionable error. Use a script copy and temporary socket fixtures if needed, avoid changing a live host socket, record results, and remove fixtures afterwards.
- [x] 1.3 Update wrapper help, README setup/usage/security/migration guidance, and AGENTS.md runtime/testing instructions. Verify `--container-help` names the variable and exact enabling value, the README shows the opt-in command and distinguishes optional API setup from mandatory host Podman, and no documentation still claims every session requires the API socket.

## 2. Verify launch integration and existing behavior

- [x] 2.1 Exercise Claude argument forwarding, `--container-shell`, and `--container-build --container-git-worktree` in both access modes using real Podman or captured stub arguments. Verify only enabled launches receive API access while entrypoints, build calls, absolute workspace mounts, and working directory retain their existing behavior; confirm missing host Podman still fails regardless of the opt-in.
- [x] 2.2 When a working Podman runtime is available, verify image build, Claude startup, configuration persistence, and an enabled child `podman run` with a local fixture image. Inspect a disabled shell session to confirm the wrapper-provided socket and `CONTAINER_HOST` are absent and host API use fails. If runtime execution is unavailable, record that limit and the stub verification results without claiming a live smoke test passed.
- [x] 2.3 Run `bash -n claude-container.sh`, `git diff --check`, and `openspec validate opt-in-container-podman --strict`; verify all pass and review the final diff for unintended mount or privilege changes.

## Verification results

- `podman build --tag localhost/claude-code:podman-opt-in-check --file Containerfile .` completed successfully. Live launch checks used the existing `localhost/claude-code:latest` image; the image definition was unchanged by this change.
- Temporary stub checks passed for unset, empty, `0`, `true`, `yes`, `01`, unexpected values, and exact `1`, including missing and non-socket fixtures. No live host socket was changed.
- Captured arguments verified Claude forwarding, shell entrypoint, explicit build, parent workspace mounts with spaces, working directory, host Podman prerequisite errors, and CA trust composition in both access modes.
- Live checks used the unchanged wrapper through a temporary runner container with the host socket exposed at its expected absolute path, and isolated configuration under the workspace. Claude CLI startup (`--version`) passed with access enabled and disabled. An enabled session ran the locally available Alpine image with `--pull=never`; a disabled shell had no socket or `CONTAINER_HOST` and could not connect to the host API. Configuration writes persisted across sessions. No credentials were used.
- Temporary test scripts, socket fixtures, and configuration directories were removed after verification.
- `bash -n claude-container.sh`, `git diff --check`, and `openspec validate opt-in-container-podman --strict` passed. Final diff review found no added privileges or unrelated mount changes.
