# Spec Delta

## ADDED Requirements

### Requirement: Independent approvals
`CLAUDE_YOLO` SHALL control only the `--dangerously-skip-permissions` argument that Claude's approval-bypass hook adds in Claude mode. It SHALL accept the shared boolean forms case-insensitively and reject invalid values before image operations. Shell mode SHALL NOT receive the flag.

Shell, YOLO and native permission settings SHALL NOT weaken the outer network boundary, and a session container engine SHALL NOT widen it.

#### Scenario: Four combinations in either state mode
- **WHEN** unrestricted runtime mode is selected with YOLO enabled and disabled, in shared and isolated modes
- **THEN** only YOLO determines flag injection, and no session receives a Podman socket or a delegation variable
- **AND** a leftover exact Podman opt-in stops startup with migration guidance in both modes

#### Scenario: Native permissions explicitly supplied
- **WHEN** YOLO is disabled but a native permission flag is passed directly to Claude
- **THEN** the wrapper forwards that argument without claiming to enforce native approvals
- **AND** disabled YOLO overrides neither native CLI arguments nor saved permission settings

#### Scenario: Approvals cannot change egress
- **WHEN** an offline or provider session uses shell mode, YOLO, or a native permission-bypass setting
- **THEN** its selected network restriction still applies
- **AND** a leftover exact `CLAUDE_CONTAINER_PODMAN=1` stops startup in either state mode, and containers started by the session's engine get no network path that the session lacks

### Requirement: Agent containers drop all capabilities and privilege gains
Every agent container SHALL drop all Linux capabilities and enable container-level no-new-privileges, in all network modes, in Claude and shell mode, and when the session has a container engine. The wrapper SHALL NOT add a capability back to resolve an incompatibility. A tool that needs a capability SHALL be documented as unsupported.

#### Scenario: Unrestricted Claude session starts
- **WHEN** an explicitly unrestricted Claude or shell session starts with shared or isolated state
- **THEN** its container has zero inheritable, permitted, effective, bounding and ambient capabilities and no-new-privileges set
- **AND** Claude, Bash, Git and OpenSpec run with caller-owned persistence

#### Scenario: Engine client works without capabilities
- **WHEN** a session with a container engine runs `podman info` and creates a child container through its `CONTAINER_HOST`
- **THEN** the client succeeds without capabilities in the agent container
- **AND** the documentation states the engine container's own hardening exceptions

#### Scenario: Incompatible tool is documented, not re-privileged
- **WHEN** a tool inside the session fails only because capabilities or privilege gains are unavailable
- **THEN** the wrapper adds no capability and does not disable no-new-privileges
- **AND** the limitation is recorded in the validation record

## MODIFIED Requirements

### Requirement: Read-only system and caller identity
Sessions SHALL use a read-only container root, `--userns=keep-id`, and the caller's UID/GID. Writable persistent binds SHALL be limited to the selected workspace and state mode. No Podman socket SHALL be mounted into a session. The host CA exception SHALL remain a read-only single-file mount governed by `host-ca-trust`.

#### Scenario: Ordinary session boundaries
- **WHEN** a session writes to its workspace and attempts to change `/usr`
- **THEN** workspace files belong to the caller and the system write fails
- **AND** a host sentinel outside all selected mounts is inaccessible, also through containers started by the session's container engine

#### Scenario: Worktree expansion
- **WHEN** `--container-git-worktree` selects the immediate physical parent
- **THEN** the entire selected parent is writable as specified by `workspace-mounts`, with no additional inferred Git mounts

## REMOVED Requirements

### Requirement: Independent approvals and delegation
**Reason**: Its socket-access rule and its combination scenario described host Podman delegation, which `sandbox-ref-31` removes.
**Migration**: The approval rule continues as "Independent approvals". A leftover exact `CLAUDE_CONTAINER_PODMAN=1` stops startup with guidance (`container-launcher`), and container tests use the session container engine (`session-container-engine`).

### Requirement: Every agent container drops capabilities and privilege gains
**Reason**: Its delegated-client scenario described host Podman delegation, which `sandbox-ref-31` removes.
**Migration**: The same rule continues as "Agent containers drop all capabilities and privilege gains", with the session container engine in place of delegation.
