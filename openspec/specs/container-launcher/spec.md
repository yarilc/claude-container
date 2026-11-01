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
The wrapper SHALL support local Podman and an explicitly selected absolute Unix `CONTAINER_HOST` on the same Linux host. It SHALL reject named connections, TCP/SSH endpoints, and implicit remote contexts. Documentation SHALL require bind sources and build paths to exist at their original absolute paths on that host.

#### Scenario: Explicit same-host Unix service
- **WHEN** the wrapper runs inside a container using an explicit Unix service endpoint on the same host
- **THEN** it supports launch after engine verification and preserves absolute bind paths

#### Scenario: Unsupported context
- **WHEN** `CONTAINER_CONNECTION` is nonempty, `CONTAINER_HOST` uses TCP/SSH, or the engine reports remote operation without an explicit Unix endpoint
- **THEN** startup fails before image operations with supported-context guidance

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
Concurrent sessions SHALL reserve distinct workspace-index names without removing another session's container. The wrapper SHALL clean up only its own container, propagate its process exit code, and forward INT, TERM, and HUP. Naming collisions SHALL be retried within a bounded limit; unrelated creation failures SHALL retain their diagnostics and status.

#### Scenario: Name collision
- **WHEN** another session reserves the candidate name between enumeration and creation
- **THEN** the wrapper retries a different numeric name without deleting the other container

#### Scenario: Application exits with an engine-like status
- **WHEN** the started application exits with status 125
- **THEN** the wrapper returns 125 and cleans up its own container without treating the application exit as a name collision

#### Scenario: Interrupted session
- **WHEN** the wrapper receives INT, TERM, or HUP while attached
- **THEN** it forwards the signal, terminates with the corresponding signal status, and cleans up its owned container

#### Scenario: Unrelated creation failure
- **WHEN** container creation fails without a name collision
- **THEN** the wrapper reports the original failure and removes no unrelated containers
