## ADDED Requirements

### Requirement: Every agent container drops capabilities and privilege gains
Every agent container SHALL drop all Linux capabilities and enable container-level no-new-privileges, in all network modes, in Claude and shell mode, and with Podman delegation. The wrapper SHALL NOT add a capability back to resolve an incompatibility. A tool that needs a capability SHALL be documented as unsupported.

#### Scenario: Unrestricted Claude session starts
- **WHEN** an explicitly unrestricted Claude or shell session starts with shared or isolated state
- **THEN** its container has zero inheritable, permitted, effective, bounding and ambient capabilities and no-new-privileges set
- **AND** Claude, Bash, Git and OpenSpec run with caller-owned persistence

#### Scenario: Delegated Podman client works without capabilities
- **WHEN** an unrestricted session with exact `CLAUDE_CONTAINER_PODMAN=1` runs `podman info` and creates a child container through the mounted socket
- **THEN** the client succeeds without capabilities in the agent container
- **AND** the documentation states that the socket still grants host engine authority beyond these limits

#### Scenario: Incompatible tool is documented, not re-privileged
- **WHEN** a tool inside the session fails only because capabilities or privilege gains are unavailable
- **THEN** the wrapper adds no capability and does not disable no-new-privileges
- **AND** the limitation is recorded in the validation record

### Requirement: Agent containers have explicit resource budgets
Every agent container SHALL be created with a memory limit, a CPU limit and a process limit. The defaults are 4 GiB memory, 2 CPUs and 512 processes. `CLAUDE_CONTAINER_MEMORY_LIMIT`, `CLAUDE_CONTAINER_CPU_LIMIT` and `CLAUDE_CONTAINER_PIDS_LIMIT` SHALL override them. No value SHALL disable a budget.

#### Scenario: Default budgets
- **WHEN** a session starts with none of the budget variables set
- **THEN** the container is created with 4 GiB memory, 2 CPUs and 512 processes

#### Scenario: Operator overrides budgets
- **WHEN** the operator sets `CLAUDE_CONTAINER_MEMORY_LIMIT=8g`, `CLAUDE_CONTAINER_CPU_LIMIT=1.5` and `CLAUDE_CONTAINER_PIDS_LIMIT=1024`
- **THEN** the container is created with exactly those limits

#### Scenario: Invalid or unbounded budget value
- **WHEN** a budget variable is empty-but-set with whitespace, zero, negative, `-1`, `max`, non-numeric, or has an unsupported unit
- **THEN** the wrapper exits with status 1 and names the variable before any engine query, state creation or image operation

### Requirement: Resource budgets are verified, not assumed
Before starting the application, each launch SHALL inspect the created agent container and require its configured memory, CPU and process limits to equal the selected budgets. Setup smoke and restricted qualification SHALL verify the effective cgroup v2 limits inside the agent container. A mismatch or missing limit SHALL stop startup or setup with an actionable diagnostic, without a retry using weaker limits.

#### Scenario: Engine ignores a budget
- **WHEN** the created container reports no limit or a different limit for memory, CPU or processes
- **THEN** the wrapper removes only its own container and exits non-zero before the application starts
- **AND** the diagnostic names rootless cgroup v2 controller delegation

#### Scenario: Effective limits are measured
- **WHEN** setup smoke or the restricted qualification probe runs inside the agent container
- **THEN** it reads the container's cgroup v2 `memory.max`, `pids.max` and `cpu.max` and requires them to match the selected budgets

#### Scenario: Budgets do not bound persistent storage
- **WHEN** the operator reads the README or wrapper help
- **THEN** it states that the budgets and tmpfs sizes do not limit workspace or state storage growth

## MODIFIED Requirements

### Requirement: Restricted containers have no capabilities or privilege gains
Offline/provider agent containers and session egress proxy containers SHALL drop all Linux capabilities and enable container-level no-new-privileges. Required hardening SHALL preserve caller identity, standard OCI seccomp, active host security policy and existing mount restrictions. Failure to apply it SHALL stop startup without a weaker retry.

#### Scenario: Restricted agent starts in either state mode
- **WHEN** an offline or provider Claude/shell session starts with shared or isolated state
- **THEN** its container drops all capabilities and enables no-new-privileges before the bootstrap executes
- **AND** caller-owned persistence, guard enforcement, relay startup and allowed local IPC continue to work

#### Scenario: Provider proxy starts without capabilities
- **WHEN** the session proxy starts
- **THEN** it has no capabilities and cannot gain privileges across execution
- **AND** its caller-owned transport socket, protected configuration, readiness identity and bounded diagnostic writes remain usable

#### Scenario: Engine or host policy rejects hardening
- **WHEN** required hardening cannot be applied or prevents a required startup operation
- **THEN** startup fails with an actionable diagnostic and removes only owned resources
- **AND** it adds no capabilities, disables no security policy and never retries unrestricted

#### Scenario: Unrestricted behavior is preserved
- **WHEN** the operator explicitly selects unrestricted networking
- **THEN** the agent container receives the same capability, no-new-privileges and resource-budget settings as restricted sessions
- **AND** no egress proxy, guard or network restriction is added to that session
