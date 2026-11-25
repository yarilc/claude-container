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

### Requirement: Process budget falls back to the process rlimit
When the verified engine does not delegate the `pids` controller and the engine host counts the process rlimit per container, the agent container's first process SHALL set its soft and hard process rlimit to the selected process budget before the container's program runs. The engine SHALL apply no process rlimit for the budget: one applied at creation counts every container of the user. Otherwise the process budget SHALL stay unenforced. Memory and CPU SHALL have no fallback.

#### Scenario: Process controller missing on a per-container host
- **WHEN** a session starts with the default budgets on an engine delegating `cpu` and `memory` but not `pids`, on a host that counts the process rlimit per container
- **THEN** the container's first process sets a soft and hard process rlimit of 512 before the application, or the guard in restricted modes, runs
- **AND** the container is created without a cgroup process limit and without a process rlimit requested from the engine
- **AND** the memory and CPU limits are applied as before

#### Scenario: Process controller delegated
- **WHEN** the engine delegates the `pids` controller
- **THEN** the process budget is enforced only by the cgroup process limit
- **AND** the wrapper sets no process rlimit

#### Scenario: Per-container counting not established
- **WHEN** the engine does not delegate `pids` and the host is not known to count the process rlimit per container
- **THEN** the wrapper requests neither a cgroup process limit nor a process rlimit for the container
- **AND** the session continues with a notice that names the unenforced process budget and why the fallback was not applied

#### Scenario: Memory controller missing
- **WHEN** the engine does not delegate the `memory` controller
- **THEN** the memory budget stays unenforced and no substitute memory limit is set

#### Scenario: The session cannot raise its process rlimit
- **WHEN** a process in a session on the fallback tries to raise its soft or hard process rlimit above the selected budget
- **THEN** the attempt fails, because the session has no capabilities and no-new-privileges is set

#### Scenario: Concurrent sessions have independent limits
- **WHEN** two sessions on the fallback run at the same time and the first holds processes up to its limit
- **THEN** the second session can still create processes up to its own limit

#### Scenario: Other containers do not consume the session's budget
- **WHEN** other containers of the same user, such as proxies, engines or their nested containers, together hold more processes than the session's budget
- **THEN** the session starts, and can create processes up to its own budget

#### Scenario: The limit cannot be set
- **WHEN** the container's first process cannot set the process rlimit to the selected budget
- **THEN** the container stops before the application or the guard runs, and the launch exits non-zero

### Requirement: Process rlimit fallback is verified
When the process budget uses the rlimit fallback, each launch SHALL require the created agent container to start with the step that sets the selected budget, and to carry no process rlimit requested by the wrapper. Setup smoke and restricted qualification SHALL measure the effective limit inside the agent container. A mismatch SHALL stop startup or setup with an actionable diagnostic, without a retry using weaker limits.

#### Scenario: Engine drops the process rlimit
- **WHEN** the created container does not start with the step that sets the selected budget, for example because the engine dropped or replaced its entry command, or the step sets another value, or the container carries a process rlimit requested by the wrapper
- **THEN** the wrapper removes only its own container and exits non-zero before the application starts
- **AND** the diagnostic names the process rlimit fallback

#### Scenario: Effective rlimit is measured
- **WHEN** setup smoke or the restricted qualification probe runs inside an agent container on the fallback
- **THEN** it reads the effective soft and hard process rlimit and requires both to equal the selected budget
- **AND** it requires the cgroup process interface to be absent or unlimited

## REMOVED Requirements

### Requirement: Independent approvals and delegation
**Reason**: Its socket-access rule and its combination scenario described host Podman delegation, which `sandbox-ref-34` removes.
**Migration**: The approval rule continues as "Independent approvals". A leftover exact `CLAUDE_CONTAINER_PODMAN=1` stops startup with guidance (`container-launcher`), and container tests use the session container engine (`session-container-engine`).

### Requirement: Every agent container drops capabilities and privilege gains
**Reason**: Its delegated-client scenario described host Podman delegation, which `sandbox-ref-34` removes.
**Migration**: The same rule continues as "Agent containers drop all capabilities and privilege gains", with the session container engine in place of delegation.
