# Spec Delta

## ADDED Requirements

### Requirement: Signals reach the session once
The attached engine client SHALL NOT proxy signals to the container. The wrapper's own shutdown SHALL be the only path that forwards INT, TERM and HUP, so the application receives one signal per event, and the bounded-shutdown contract applies.

#### Scenario: Process-group signal without a terminal
- **WHEN** a TERM is sent to the wrapper's process group during a session without a TTY
- **THEN** the application receives TERM once, and the wrapper returns 143 after cleanup

#### Scenario: Attach options
- **WHEN** the wrapper starts and attaches to its container
- **THEN** the attach command disables signal proxying
