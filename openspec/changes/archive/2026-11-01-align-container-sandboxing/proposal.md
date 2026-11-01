# Proposal

## Why

The newer sibling project `antigravity-container` verifies the launch engine, protects persistent state, handles remapped Unix sockets, and tests filesystem boundaries more thoroughly. Claude Container should adopt those behaviors while retaining the user's existing `~/.claude` workflow and its stricter Podman opt-in.

## What Changes

- Require a verified Linux rootless launch engine and explicitly support local Podman and same-host Unix service access.
- Preserve `~/.claude` (or `CLAUDE_CONFIG_DIR`) and shared host OpenSpec configuration by default; add optional isolated application home through `CLAUDE_CONTAINER_STATE_DIR`, with no automatic credential import.
- **BREAKING**: Reject credential directories with the wrong owner or group/other access; document explicit permission repair and native Linux storage for filesystems that cannot enforce privacy.
- Support selected and remapped delegation sockets through `CLAUDE_CONTAINER_PODMAN_SOCKET`, Unix `CONTAINER_HOST`, and `XDG_RUNTIME_DIR`, while preserving exact `CLAUDE_CONTAINER_PODMAN=1` semantics.
- **BREAKING**: Reject unsupported remote contexts and remove automatic SELinux relabeling of shared host configuration; retain standard runtime security policies.
- Make TTY allocation conditional, reserve container names atomically, forward signals, preserve exit codes, and distinguish image absence from inspection failures.
- Add synthetic wrapper tests, opt-in runtime boundary tests, and a versioned validation record distinguishing CLI approvals, internal sandboxing, and container isolation.
- Preserve workspace/worktree selection, host CA opt-in, tmpfs `noexec`, and independence of YOLO and socket access.

## Capabilities

### New Capabilities

- `container-launcher`: Verified launch engine, transparent terminal-aware invocation, image error handling, and owned container lifecycle.
- `persistent-state`: Compatible shared state, optional isolated home, private credential directories, and explicit migration.
- `container-isolation`: Read-only system, temporary storage, independent authority controls, and verifiable isolation claims.

### Modified Capabilities

- `container-podman-access`: Select and verify the delegation endpoint, bind its host-side socket path, distinguish launch-engine checks from delegation checks, and document authority beyond the workspace.

## Impact

Implementation will primarily change `claude-container.sh`, `README.md`, and `AGENTS.md`, add `tests/` and `docs/validation.md`, and may adjust `Containerfile` only if runtime acceptance requires directory preparation. No new authentication backend, privileged mode, custom seccomp policy, network filtering, automatic migration, or production dependency is planned. Python's standard library can support the tests, with a Podman runner when host Python is unavailable. Existing `workspace-mounts`, `host-ca-trust`, and `runtime-image` requirements remain applicable and require regression coverage.
