# container-launcher Specification

## Purpose

Provide predictable rootless container startup, transparent CLI invocation, and a lifecycle that preserves session ownership and termination behavior.

## Requirements

### Requirement: Verified launch engine
Except for wrapper help, the wrapper SHALL verify that the engine used for image operations and container launch reports Linux and rootless operation. Failed or unrecognized verification SHALL stop before image inspection, build, or container creation.

#### Scenario: Local rootless engine without delegation
- **WHEN** local Podman reports Linux and rootless operation and delegation is disabled
- **THEN** engine verification succeeds without requiring a delegation socket

#### Scenario: Engine cannot be verified
- **WHEN** engine verification fails or reports rootful, non-Linux, empty, or malformed results
- **THEN** the wrapper exits nonzero with an actionable engine error before image operations or launch

### Requirement: Supported launch contexts
The wrapper SHALL support local Podman and an explicit same-host absolute Unix `CONTAINER_HOST` with a socket pathname beyond `/`. It SHALL reject named connections, TCP/SSH endpoints, implicit remote contexts, and pathless Unix endpoints; malformed explicit endpoints SHALL fail before any engine query. Documentation SHALL require bind sources and build paths to exist at their original absolute host paths.

#### Scenario: Explicit same-host Unix service
- **WHEN** the wrapper runs inside a container using an explicit Unix service endpoint on the same host
- **THEN** it supports launch after engine verification and preserves absolute bind paths

#### Scenario: Unsupported context
- **WHEN** `CONTAINER_CONNECTION` is nonempty, `CONTAINER_HOST` uses TCP/SSH, or the engine reports remote operation without an explicit Unix endpoint
- **THEN** startup fails before image operations with supported-context guidance

#### Scenario: Unix endpoint lacks a socket pathname
- **WHEN** `CONTAINER_HOST` is `unix://`, `unix:///`, or names only slash characters after the scheme
- **THEN** startup fails with an absolute socket-path diagnostic before querying Podman or performing image operations
- **AND** the rejection applies with delegation enabled or disabled, including an explicit delegation-socket override

#### Scenario: Relative Unix endpoint
- **WHEN** `CONTAINER_HOST` is a Unix endpoint with a relative path
- **THEN** startup fails before querying Podman with guidance to use an absolute socket pathname

#### Scenario: Help ignores invalid launch configuration
- **WHEN** `--container-help` is requested with a pathless Unix endpoint
- **THEN** help succeeds without contacting an engine or creating state

### Requirement: Transparent invocation and terminal handling
The wrapper SHALL preserve the order, spaces, and empty values of forwarded Claude arguments. It SHALL preserve stdin and allocate a TTY only when stdin and stdout are terminals. Shell mode SHALL start Bash with the selected mounts and identity, without Claude arguments or wrapper-injected YOLO flags.

#### Scenario: Pipeline invocation
- **WHEN** Claude is invoked with redirected stdin and arguments containing spaces or empty values
- **THEN** stdin and arguments reach Claude unchanged without mandatory TTY allocation

#### Scenario: Interactive session
- **WHEN** stdin and stdout are terminals
- **THEN** the wrapper allocates a TTY and forwards an existing `TERM` by name

#### Scenario: Shell invocation
- **WHEN** `--container-shell` is combined with Claude arguments and enabled YOLO
- **THEN** Bash starts without receiving those arguments or the permission-bypass flag

### Requirement: Side effect free wrapper help
`--container-help` SHALL display wrapper options and environment controls successfully without requiring Podman, creating state, or performing engine or image operations.

#### Scenario: Help without prerequisites
- **WHEN** wrapper help is requested with Podman unavailable and invalid runtime configuration
- **THEN** help succeeds without creating directories or contacting an engine

### Requirement: Predictable image operations
The wrapper SHALL build an absent image and refresh it on `--container-build`, using the Containerfile beside the resolved wrapper script. An image-inspection error other than absence SHALL fail without starting a build or container. Build failures SHALL stop launch and preserve the failure status.

#### Scenario: Image absent from an external workspace
- **WHEN** the wrapper is invoked through a symlink outside its repository and the image is absent
- **THEN** it builds using the Containerfile beside the physical wrapper script

#### Scenario: Inspection failure
- **WHEN** image inspection reports an engine error rather than absence
- **THEN** the wrapper exits nonzero without attempting a build or launch

#### Scenario: Explicit build fails
- **WHEN** `--container-build` is requested and the build fails
- **THEN** the wrapper returns the build failure status without creating a session container

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

### Requirement: Minimal image build context
Automatic and explicit image builds SHALL exclude repository metadata, local credentials and state, caches, and unrelated project files from the build context. The build recipe and explicitly required build inputs SHALL remain available. This filtering SHALL apply when the wrapper is invoked through a symlink or outside its repository.

#### Scenario: Sensitive and unrelated files are excluded
- **GIVEN** a synthetic build context contains Git metadata, Claude configuration, isolated state, environment files, caches, and an unrelated nested file
- **WHEN** the repository's build-context filtering is applied
- **THEN** those files are unavailable to build instructions consuming the context
- **AND** the Containerfile remains available

#### Scenario: Both wrapper build paths use the filter
- **WHEN** an absent image triggers an automatic build or `--container-build` requests a refresh from another working directory
- **THEN** both builds use the filtered context beside the resolved wrapper script
- **AND** build failures retain their existing status and prevent launch

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
