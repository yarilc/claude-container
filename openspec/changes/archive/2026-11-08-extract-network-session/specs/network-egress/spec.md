## ADDED Requirements

### Requirement: Shared restricted session interface
Restricted-session preparation, proxy lifecycle, restricted container arguments and proxy cleanup SHALL be provided by one shared, profile-driven component. Wrappers SHALL invoke it through fixed operations with explicit inputs and outputs. They SHALL NOT re-implement these steps. Its cleanup SHALL use only the remaining launcher shutdown budget and SHALL NOT change the primary exit status.

#### Scenario: Wrapper integration
- **WHEN** a wrapper starts an offline or provider session
- **THEN** preflight, the guard probe, proxy creation, readiness, hardening verification, guard and relay arguments, and proxy cleanup come from the shared component
- **AND** the wrapper adds only agent-specific command, environment, state and credential options

#### Scenario: Interrupted proxy start
- **WHEN** a signal arrives while the shared component is creating or verifying the proxy
- **THEN** the wrapper terminates that operation, then recovers and removes only the proxy owned by this session within the remaining shutdown budget
- **AND** no agent container is created and the signal status is returned

#### Scenario: Stalled proxy cleanup
- **WHEN** proxy recovery or removal stalls during shutdown
- **THEN** each engine call is bounded by the remaining budget
- **AND** the unconfirmed resource is reported without replacing the primary exit status

#### Scenario: Arguments with special characters
- **WHEN** the agent command or its arguments contain spaces, quotes or newlines
- **THEN** the shared component returns them unchanged as separate arguments
