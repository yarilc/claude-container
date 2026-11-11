# Spec Delta

## MODIFIED Requirements

### Requirement: Session proxies have enforced resource budgets
Each Internet-facing session proxy SHALL have a limit of 128 processes and 256 MiB memory, enforced by the engine and host cgroups, for each budget whose cgroup v2 controller (`pids`, `memory`) the verified rootless engine reports as available. Startup SHALL fail before agent execution if an enforced limit is not applied, or if an unenforced limit is unexpectedly present. These budgets SHALL coexist with existing multiplex, TLS inspection and lifecycle bounds without broadening runtime access.

#### Scenario: Proxy readiness with applied limits
- **WHEN** a provider session prepares its proxy on an engine reporting the `pids` and `memory` controllers
- **THEN** both configured budgets are verified as effective before the agent starts
- **AND** matching-SNI TLS, streaming, concurrent tunnels, readiness and protected logs operate within the budgets

#### Scenario: Rootless resource control unavailable
- **WHEN** the engine rejects or silently ignores a limit whose controller it reports as available, or its effective value cannot be established
- **THEN** provider preparation fails and cleans up only owned resources
- **AND** it never substitutes an unrestricted connection

#### Scenario: Controller not delegated for the proxy
- **WHEN** the verified engine does not report the `memory` controller
- **THEN** the proxy is created without a memory limit, and its process limit is still applied and verified when `pids` is reported
- **AND** the session prints a notice naming the unenforced proxy budget

#### Scenario: Proxy exceeds a resource budget
- **WHEN** a proxy reaches its process or memory budget or is terminated because of exhaustion
- **THEN** affected outbound operations fail closed
- **AND** cleanup preserves the primary application/signal status and bounded shutdown contract
- **AND** other sessions retain their independent proxy resources and budgets
