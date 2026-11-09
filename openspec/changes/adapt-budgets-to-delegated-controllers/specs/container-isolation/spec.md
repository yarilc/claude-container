# Spec Delta

## MODIFIED Requirements

### Requirement: Agent containers have explicit resource budgets
Every agent container SHALL be created with a memory limit, a CPU limit and a process limit for each budget whose cgroup v2 controller (`memory`, `cpu`, `pids`) the verified rootless engine reports as available. The defaults are 4 GiB memory, 2 CPUs and 512 processes. `CLAUDE_CONTAINER_MEMORY_LIMIT`, `CLAUDE_CONTAINER_CPU_LIMIT` and `CLAUDE_CONTAINER_PIDS_LIMIT` SHALL override them. No value SHALL disable a budget; only a missing controller leaves it unenforced.

#### Scenario: Default budgets
- **WHEN** a session starts with none of the budget variables set on an engine reporting the `cpu`, `memory` and `pids` controllers
- **THEN** the container is created with 4 GiB memory, 2 CPUs and 512 processes

#### Scenario: Operator overrides budgets
- **WHEN** the operator sets `CLAUDE_CONTAINER_MEMORY_LIMIT=8g`, `CLAUDE_CONTAINER_CPU_LIMIT=1.5` and `CLAUDE_CONTAINER_PIDS_LIMIT=1024` on an engine reporting all three controllers
- **THEN** the container is created with exactly those limits

#### Scenario: Invalid or unbounded budget value
- **WHEN** a budget variable is empty-but-set with whitespace, zero, negative, `-1`, `max`, non-numeric, or has an unsupported unit
- **THEN** the wrapper exits with status 1 and names the variable before any engine query, state creation or image operation

#### Scenario: Controller not delegated
- **WHEN** the verified engine does not report the `cpu` controller
- **THEN** the container is created without a CPU limit, while the memory and process limits are still applied when their controllers are reported
- **AND** the session continues and prints a notice naming the unenforced CPU budget and the missing controller

### Requirement: Resource budgets are verified, not assumed
Before starting the application, each launch SHALL inspect the created agent container and require each enforced budget to equal its selected value and each unenforced budget to be absent. Setup smoke and restricted qualification SHALL verify the effective cgroup v2 limits inside the agent container in the same way. A mismatch SHALL stop startup or setup with an actionable diagnostic, without a retry using weaker limits.

#### Scenario: Engine ignores a budget
- **WHEN** the created container reports no limit or a different limit for a budget whose controller the engine reports as available
- **THEN** the wrapper removes only its own container and exits non-zero before the application starts
- **AND** the diagnostic names rootless cgroup v2 controller delegation

#### Scenario: Effective limits are measured
- **WHEN** setup smoke or the restricted qualification probe runs inside the agent container
- **THEN** it reads the container's cgroup v2 `memory.max`, `pids.max` and `cpu.max` for every enforced budget and requires them to match the selected budgets
- **AND** for every unenforced budget it requires the controller interface to be absent or unlimited

#### Scenario: Budgets do not bound persistent storage
- **WHEN** the operator reads the README or wrapper help
- **THEN** it states that the budgets and tmpfs sizes do not limit workspace or state storage growth
