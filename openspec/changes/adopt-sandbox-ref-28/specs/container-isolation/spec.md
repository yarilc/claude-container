# Spec Delta

## ADDED Requirements

### Requirement: Only the systemd cgroup manager delegates controllers
A reported cgroup v2 controller SHALL count as delegated only when the verified rootless engine also reports the `systemd` cgroup manager. With `cgroupfs` or any other manager, no controller SHALL count as delegated, whatever the engine reports. An unverifiable cgroup manager response SHALL stop startup before image operations.

#### Scenario: cgroupfs engine reporting every controller
- **WHEN** a session starts on a rootless engine with the `cgroupfs` manager that reports `cpu`, `memory` and `pids`
- **THEN** the container is created without memory, CPU or cgroup process limits
- **AND** the session prints notices that the memory and CPU budgets are not enforced, naming the `cgroupfs` cgroup manager
- **AND** the process budget follows the process rlimit fallback

#### Scenario: systemd engine
- **WHEN** a session starts on a rootless engine with the `systemd` manager that reports `cpu`, `memory` and `pids`
- **THEN** the memory, CPU and cgroup process limits are applied as before

#### Scenario: Unverifiable cgroup manager
- **WHEN** the engine's cgroup manager response is empty, malformed or has more than one record
- **THEN** the wrapper exits non-zero before image operations or container creation

### Requirement: Process budget falls back to the process rlimit
When the verified engine does not delegate the `pids` controller and the engine host counts the process rlimit per container, the agent container SHALL be created with a soft and hard process rlimit equal to the selected process budget. When per-container counting is not established, the process budget SHALL stay unenforced. The memory and CPU budgets SHALL have no fallback.

#### Scenario: Process controller missing on a per-container host
- **WHEN** a session starts with the default budgets on an engine delegating `cpu` and `memory` but not `pids`, on a host that counts the process rlimit per container
- **THEN** the container is created with a soft and hard process rlimit of 512 and without a cgroup process limit
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

### Requirement: Process rlimit fallback is verified
When the process budget uses the rlimit fallback, each launch SHALL require the created agent container to carry a soft and hard process rlimit equal to the selected budget. Setup smoke and restricted qualification SHALL measure the same effective limit inside the agent container. A mismatch SHALL stop startup or setup with an actionable diagnostic, without a retry using weaker limits.

#### Scenario: Engine drops the process rlimit
- **WHEN** the created container reports no process rlimit, or a soft or hard value different from the selected budget
- **THEN** the wrapper removes only its own container and exits non-zero before the application starts
- **AND** the diagnostic names the process rlimit fallback

#### Scenario: Effective rlimit is measured
- **WHEN** setup smoke or the restricted qualification probe runs inside an agent container on the fallback
- **THEN** it reads the effective soft and hard process rlimit and requires both to equal the selected budget
- **AND** it requires the cgroup process interface to be absent or unlimited

## MODIFIED Requirements

### Requirement: Agent containers have explicit resource budgets
Every agent container SHALL be created with a memory limit, a CPU limit and a process limit for each budget whose cgroup v2 controller (`memory`, `cpu`, `pids`) the verified rootless engine delegates. The defaults are 4 GiB memory, 2 CPUs and 512 processes. `CLAUDE_CONTAINER_MEMORY_LIMIT`, `CLAUDE_CONTAINER_CPU_LIMIT` and `CLAUDE_CONTAINER_PIDS_LIMIT` SHALL override them. No value SHALL disable a budget; only a missing controller leaves it unenforced.

#### Scenario: Default budgets
- **WHEN** a session starts with none of the budget variables set on an engine delegating the `cpu`, `memory` and `pids` controllers
- **THEN** the container is created with 4 GiB memory, 2 CPUs and 512 processes

#### Scenario: Operator overrides budgets
- **WHEN** the operator sets `CLAUDE_CONTAINER_MEMORY_LIMIT=8g`, `CLAUDE_CONTAINER_CPU_LIMIT=1.5` and `CLAUDE_CONTAINER_PIDS_LIMIT=1024` on an engine delegating all three controllers
- **THEN** the container is created with exactly those limits

#### Scenario: Invalid or unbounded budget value
- **WHEN** a budget variable is empty-but-set with whitespace, zero, negative, `-1`, `max`, non-numeric, or has an unsupported unit
- **THEN** the wrapper exits with status 1 and names the variable before any engine query, state creation or image operation

#### Scenario: Controller not delegated
- **WHEN** the verified engine does not delegate the `cpu` controller
- **THEN** the container is created without a CPU limit, while the memory and process limits are still applied when their controllers are delegated
- **AND** the session continues and prints a notice naming the unenforced CPU budget and why it is unenforced

### Requirement: Resource budgets are verified, not assumed
Before starting the application, each launch SHALL inspect the created agent container and require each cgroup-enforced budget to equal its selected value and each budget whose controller is not delegated to have no cgroup limit. Setup smoke and restricted qualification SHALL verify the effective cgroup v2 limits inside the agent container in the same way. A mismatch SHALL stop startup or setup with an actionable diagnostic, without a retry using weaker limits.

#### Scenario: Engine ignores a budget
- **WHEN** the created container reports no limit or a different limit for a budget whose controller the engine delegates
- **THEN** the wrapper removes only its own container and exits non-zero before the application starts
- **AND** the diagnostic names rootless cgroup v2 controller delegation

#### Scenario: Effective limits are measured
- **WHEN** setup smoke or the restricted qualification probe runs inside the agent container
- **THEN** it reads the container's cgroup v2 `memory.max`, `pids.max` and `cpu.max` for every cgroup-enforced budget and requires them to match the selected budgets
- **AND** for every budget whose controller is not delegated it requires the controller interface to be absent or unlimited

#### Scenario: Budgets do not bound persistent storage
- **WHEN** the operator reads the README or wrapper help
- **THEN** it states that the budgets and tmpfs sizes do not limit workspace or state storage growth
