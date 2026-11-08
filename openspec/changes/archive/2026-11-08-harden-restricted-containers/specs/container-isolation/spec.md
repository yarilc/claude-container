# Spec Delta

## ADDED Requirements

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
- **THEN** this hardening change introduces no new container flags, limits or delegation restrictions for that session
