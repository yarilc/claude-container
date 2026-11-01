# Spec Delta

## Purpose

Define the outer container's filesystem and authority boundaries and require evidence that distinguishes container isolation from native agent approvals and internal sandbox execution.

## ADDED Requirements

### Requirement: Read-only system and caller identity
Sessions SHALL use a read-only container root, `--userns=keep-id`, and the caller's UID/GID. Writable persistent binds SHALL be limited to the selected workspace and state mode, plus the delegated socket when enabled. The host CA exception SHALL remain a read-only single-file mount governed by `host-ca-trust`.

#### Scenario: Ordinary session boundaries
- **WHEN** a session writes to its workspace and attempts to change `/usr`
- **THEN** workspace files belong to the caller and the system write fails
- **AND** a host sentinel outside all selected mounts is inaccessible when socket delegation is disabled

#### Scenario: Worktree expansion
- **WHEN** `--container-git-worktree` selects the immediate physical parent
- **THEN** the entire selected parent is writable as specified by `workspace-mounts`, with no additional inferred Git mounts

### Requirement: Ephemeral constrained temporary storage
Sessions SHALL provide ephemeral `/tmp` and `/run` mounts with `rw,nosuid,nodev,noexec`, retaining limits of 256 MiB and 16 MiB respectively. Temporary contents SHALL disappear after container removal. Internal sandbox compatibility SHALL NOT silently relax these options.

#### Scenario: Temporary file lifecycle
- **WHEN** a session writes a temporary file and a new container starts after its removal
- **THEN** temporary storage accepts writes but the previous file is absent
- **AND** both temporary mounts retain `nosuid,nodev,noexec`

### Requirement: Standard runtime security policy
The wrapper SHALL NOT add privileged execution, extra capabilities, custom seccomp profiles, disabled SELinux labels, or automatic host bind relabeling. Policy failures SHALL remain visible with actionable guidance rather than triggering an automatic security-policy bypass.

#### Scenario: SELinux denial
- **WHEN** host policy denies a workspace, state, or socket bind
- **THEN** startup reports the engine failure without adding relabel options or disabling labels

#### Scenario: Internal sandbox denied by policy
- **WHEN** Claude's internal sandbox cannot execute under the standard container policy
- **THEN** the failure is recorded without automatically broadening container privileges or changing seccomp or tmpfs policy

### Requirement: Independent approvals and delegation
`CLAUDE_YOLO` SHALL control only wrapper injection of `--dangerously-skip-permissions` in Claude mode. It SHALL accept existing boolean forms case-insensitively and reject invalid values before image operations. Socket access SHALL depend only on exact `CLAUDE_CONTAINER_PODMAN=1`, independently of YOLO and state mode. Disabling YOLO SHALL NOT override native CLI arguments or saved permission settings.

#### Scenario: Four combinations in either state mode
- **WHEN** all enabled/disabled combinations of YOLO and Podman delegation are used in shared and isolated modes
- **THEN** only YOLO determines flag injection and only exact Podman opt-in determines delegation mounts and variables

#### Scenario: Native permissions explicitly supplied
- **WHEN** YOLO is disabled but a native permission flag is passed directly to Claude
- **THEN** the wrapper forwards that argument without claiming to enforce native approvals

### Requirement: Evidence-based isolation documentation
Documentation SHALL distinguish approvals, internal sandboxing, filesystem isolation, and socket authority. A validation record SHALL identify environment and versions and label checks as passed, failed, or unavailable. A sandboxed tool operation and its expected output SHALL be verified before claiming internal sandbox compatibility; executable availability or CLI exit status alone SHALL NOT establish it.

#### Scenario: Synthetic runtime checks
- **WHEN** automated boundary checks run
- **THEN** they use synthetic state without real credentials or paid model requests and check external sentinels, ownership, state persistence, and temporary storage

#### Scenario: Sandbox operation unavailable or unsuccessful
- **WHEN** an authenticated sandbox check cannot run or fails to produce the expected result
- **THEN** the validation record reports unavailable or failed rather than passed, even if `bwrap` probes succeed or the CLI exits zero

#### Scenario: User reviews access boundaries
- **WHEN** the user reads the README
- **THEN** it explains shared-state write access, parent/worktree expansion, and socket-enabled host mounts beyond the workspace without promising network-egress isolation
