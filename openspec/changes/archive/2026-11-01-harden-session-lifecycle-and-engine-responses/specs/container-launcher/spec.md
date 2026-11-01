# Spec Delta

## MODIFIED Requirements

### Requirement: Owned container lifecycle
Concurrent sessions SHALL reserve distinct workspace-index names without removing another session's container. The wrapper SHALL clean up only its own container, propagate its process exit code, and forward INT, TERM, and HUP. Naming collisions SHALL be retried within a bounded limit; unrelated creation failures SHALL retain their diagnostics and status. Interruption during creation SHALL retain recoverable evidence of session ownership.

#### Scenario: Name collision
- **WHEN** another session reserves the candidate name between enumeration and creation
- **THEN** the wrapper retries a different numeric name without deleting the other container

#### Scenario: Application exits with an engine-like status
- **WHEN** the started application exits with status 125
- **THEN** the wrapper returns 125 and cleans up its own container without treating the application exit as a name collision

#### Scenario: Interrupted session
- **GIVEN** the engine remains reachable for signal delivery and removal
- **WHEN** the wrapper receives INT, TERM, or HUP while attached
- **THEN** it forwards the signal, terminates with the corresponding signal status, and cleans up its owned container
- **AND** shutdown follows the bounded-shutdown contract

#### Scenario: Unrelated creation failure
- **WHEN** container creation fails without a name collision
- **THEN** the wrapper reports the original failure and removes no unrelated containers

#### Scenario: Interrupted creation has recoverable ownership
- **GIVEN** the engine creates a container for this session before the create client returns its ID
- **WHEN** the wrapper receives INT, TERM, or HUP during creation
- **THEN** it attempts bounded recovery and removal using evidence identifying that session's container
- **AND** it does not start the application after the interruption or remove an unrelated container by workspace name

## ADDED Requirements

### Requirement: Bounded session shutdown
After a session signal or application exit, wrapper shutdown SHALL finish within a 20-second overall budget. Signal shutdown SHALL allow at most five seconds for graceful application exit before attempting forced removal. Engine control calls and local client termination/reaping SHALL be bounded within that budget. Cleanup failures SHALL be reported without replacing the primary application or signal exit status.

#### Scenario: Application ignores the forwarded signal
- **WHEN** a running application ignores TERM, INT, or HUP forwarded by the wrapper
- **THEN** the wrapper waits no longer than the graceful allowance and attempts forced removal of only its own container
- **AND** it returns 143 for TERM, 130 for INT, or 129 for HUP within the shutdown budget

#### Scenario: Engine control call stalls
- **WHEN** a shutdown signal, ownership-recovery, or removal call stalls
- **THEN** the wrapper bounds that call and any subsequent local-client wait within the overall shutdown budget
- **AND** it reports incomplete cleanup without claiming the remote container was removed

#### Scenario: Cleanup fails after application exit
- **WHEN** an application exits with status 0, a nonzero status, or 125 and cleanup fails or times out
- **THEN** the wrapper retains that exact application exit status
- **AND** stderr identifies the cleanup failure and available session/container identity

#### Scenario: Repeated signals do not extend shutdown
- **WHEN** additional TERM, INT, or HUP signals arrive after shutdown has started
- **THEN** they do not restart the deadline or recursive cleanup
- **AND** the first terminal signal determines the signal exit status

#### Scenario: Ordinary session duration is unrestricted
- **WHEN** a healthy application or image build runs longer than the shutdown budget without a shutdown event
- **THEN** the wrapper does not terminate it because of the shutdown policy

### Requirement: Single-record launch verification response
Launch-engine verification SHALL accept exactly one valid response record, with no terminator or one final LF. Additional records, including empty records or extra trailing LF characters, SHALL fail before image operations or container creation. Capture SHALL preserve record boundaries and command failure status; successful-looking output from a failed query SHALL NOT verify the engine.

#### Scenario: Normal response terminator
- **WHEN** a successful engine query emits one valid response with no final LF or exactly one final LF
- **THEN** launch-engine verification accepts the response

#### Scenario: Additional blank or nonblank records
- **WHEN** the engine query emits a valid first record followed by a blank record, additional nonblank record, or multiple trailing LF characters
- **THEN** startup fails with an invalid-engine-response diagnostic before image inspection, build, or creation

#### Scenario: Query fails after emitting valid data
- **WHEN** the engine query emits valid-looking output but exits nonzero
- **THEN** startup fails with the engine-query diagnostic and performs no image operation or launch
