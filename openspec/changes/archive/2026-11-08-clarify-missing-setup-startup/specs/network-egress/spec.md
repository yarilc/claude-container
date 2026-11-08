# Spec Delta

## MODIFIED Requirements

### Requirement: Operator-selected runtime modes
The wrapper SHALL accept `CLAUDE_CONTAINER_NETWORK=offline|provider|unrestricted` from explicit operator configuration or validated managed preferences. An ordinary launch with an unset or empty effective mode SHALL stop with setup guidance before runtime preparation. Other values SHALL fail before image operations. Only explicit `unrestricted` SHALL remove the runtime destination boundary. Agent-writable configuration SHALL NOT select or broaden the outer policy.

#### Scenario: Default and invalid selection
- **WHEN** an ordinary invocation leaves the effective mode unset or empty
- **THEN** it receives missing-setup guidance rather than starting an implicitly offline session
- **AND** an unknown nonempty mode fails with the existing invalid-mode diagnostic without image operations or agent startup

#### Scenario: Policy cannot escalate itself
- **WHEN** workspace settings, application state, or commands request a broader policy or remove proxy variables
- **THEN** the running session retains its operator-selected outer boundary

#### Scenario: Explicit offline operation
- **WHEN** an operator explicitly chooses offline mode or a validated managed launcher supplies saved offline mode
- **THEN** the wrapper applies all existing restricted platform, protected-installation, guard and qualification requirements
- **AND** the resulting session cannot reach external services, including the Claude API

#### Scenario: Explicit provider or unrestricted operation
- **WHEN** an operator explicitly chooses provider or unrestricted mode, or the validated managed launcher supplies that saved choice
- **THEN** the mode retains its existing policy, authority, prerequisite and separate maintenance requirements
- **AND** failed restricted preparation never falls back to unrestricted networking

#### Scenario: Qualification is not an ordinary session
- **WHEN** the standalone fixed qualification operation is invoked with no effective network mode
- **THEN** its existing offline qualification default and protected-fixture checks remain available
- **AND** neither that operation nor its internal probe admits an arbitrary application command or bypasses enforcement
