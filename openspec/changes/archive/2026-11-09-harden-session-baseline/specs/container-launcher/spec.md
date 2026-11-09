## ADDED Requirements

### Requirement: Optional session lifetime limit
`CLAUDE_CONTAINER_RUN_TIMEOUT` SHALL set the native engine lifetime of the agent container in whole seconds. When it is unset, empty or `0`, no lifetime limit SHALL apply. Any other value that is not a positive decimal integer SHALL fail with status 1 before engine queries. The limit SHALL be independent of the 20-second shutdown budget and of proxy lifetime.

#### Scenario: Lifetime disabled by default
- **WHEN** `CLAUDE_CONTAINER_RUN_TIMEOUT` is unset
- **THEN** the agent container is created without a lifetime limit

#### Scenario: Lifetime expires
- **WHEN** `CLAUDE_CONTAINER_RUN_TIMEOUT=60` is set and the application is still running after 60 seconds
- **THEN** the engine stops the agent container
- **AND** the wrapper prints a stderr notice that the session lifetime limit was reached
- **AND** the wrapper exits with the engine client's status (255 on the measured Podman 4.9.3 server), then cleans up owned resources, including a provider proxy, within the shutdown budget

#### Scenario: Session ends before the limit
- **WHEN** the application exits before the limit
- **THEN** the wrapper propagates the application exit status unchanged and prints no lifetime notice

#### Scenario: Invalid lifetime value
- **WHEN** `CLAUDE_CONTAINER_RUN_TIMEOUT` is negative, fractional or non-numeric
- **THEN** the wrapper exits with status 1 and names the variable before any engine query or state creation

### Requirement: Qualification binds agent hardening settings
The qualification identity of a restricted installation SHALL include:
- the agent capability and no-new-privileges settings;
- the selected memory, CPU and process budgets;
- the session lifetime setting.

A launch whose effective settings differ from the qualified identity SHALL stop with requalification guidance.

#### Scenario: Budget changed after qualification
- **WHEN** a restricted installation was qualified with default budgets and the operator launches with `CLAUDE_CONTAINER_PIDS_LIMIT=1024`
- **THEN** the qualification check reports mismatched evidence and the application does not start

#### Scenario: Qualification with matching settings
- **WHEN** the operator qualifies and launches with the same budgets and lifetime
- **THEN** the qualification check accepts the report

### Requirement: Hardening controls are documented
Wrapper help and the README SHALL document:
- the budget variables, their defaults and accepted formats;
- the lifetime variable;
- the unsafe-workspace override and the refused directories;
- that capabilities are dropped in every mode.

Help SHALL remain side effect free.

#### Scenario: Operator reads wrapper help
- **WHEN** the operator runs `--container-help`
- **THEN** the output lists `CLAUDE_CONTAINER_MEMORY_LIMIT`, `CLAUDE_CONTAINER_CPU_LIMIT`, `CLAUDE_CONTAINER_PIDS_LIMIT`, `CLAUDE_CONTAINER_RUN_TIMEOUT` and `CLAUDE_CONTAINER_ALLOW_UNSAFE_WORKSPACE` with their defaults
- **AND** no engine query or state creation occurs
