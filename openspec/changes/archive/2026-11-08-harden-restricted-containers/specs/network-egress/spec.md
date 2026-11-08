# Spec Delta

## ADDED Requirements

### Requirement: Session proxies have enforced resource budgets
Each Internet-facing session proxy SHALL have an explicit limit of 128 processes and 256 MiB memory, enforced by the engine and host cgroups. Startup SHALL fail before agent execution if either limit is unavailable or not applied. These budgets SHALL coexist with existing multiplex, TLS inspection and lifecycle bounds without broadening runtime access.

#### Scenario: Proxy readiness with applied limits
- **WHEN** a provider session prepares its proxy
- **THEN** both configured budgets are verified as effective before the agent starts
- **AND** matching-SNI TLS, streaming, concurrent tunnels, readiness and protected logs operate within the budgets

#### Scenario: Rootless resource control unavailable
- **WHEN** the engine rejects a limit, silently ignores it or cannot establish its effective value
- **THEN** provider preparation fails and cleans up only owned resources
- **AND** it never removes the limit or substitutes an unrestricted connection

#### Scenario: Proxy exceeds a resource budget
- **WHEN** a proxy reaches its process or memory budget or is terminated because of exhaustion
- **THEN** affected outbound operations fail closed
- **AND** cleanup preserves the primary application/signal status and bounded shutdown contract
- **AND** other sessions retain their independent proxy resources and budgets
