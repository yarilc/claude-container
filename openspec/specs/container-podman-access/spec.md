# container-podman-access Specification

## Purpose

Control access from wrapper-launched Claude and shell sessions to the host Podman API, granting it only through an explicit host environment opt-in.

## Requirements

### Requirement: Podman API access requires the exact opt-in value
The wrapper SHALL grant access to the host Podman API only when `CLAUDE_CONTAINER_PODMAN` equals the exact string `1`. An unset, empty, or different value SHALL disable that access, omit the socket mount, and ensure `CONTAINER_HOST` is absent from the launched container environment, including values supplied by image or engine defaults.

#### Scenario: Variable is unset
- **WHEN** the wrapper starts with `CLAUDE_CONTAINER_PODMAN` unset
- **THEN** it does not mount the host Podman socket and container `CONTAINER_HOST` is absent

#### Scenario: Variable does not equal one
- **WHEN** the wrapper starts with `CLAUDE_CONTAINER_PODMAN` empty or set to `0`, `true`, `yes`, `01`, or another value other than the exact string `1`
- **THEN** it starts with Podman API access disabled without rejecting that value
- **AND** it does not mount the host Podman socket and container `CONTAINER_HOST` is absent

#### Scenario: Access is explicitly enabled
- **GIVEN** the selected Unix socket serves a reachable engine that reports rootless operation and an absolute host-side socket path
- **WHEN** the wrapper starts with `CLAUDE_CONTAINER_PODMAN=1`
- **THEN** it mounts the service-reported host-side socket at `/run/podman/podman.sock`
- **AND** it sets `CONTAINER_HOST=unix:///run/podman/podman.sock` in the container

#### Scenario: Disabled delegation clears inherited defaults
- **GIVEN** the image or engine defaults define a nonempty container `CONTAINER_HOST`
- **WHEN** the wrapper launches Claude or shell mode with delegation disabled
- **THEN** `CONTAINER_HOST` is absent from the container environment rather than merely empty
- **AND** no delegation socket is mounted

#### Scenario: Launch endpoint remains available to the host client
- **GIVEN** a valid same-host Unix `CONTAINER_HOST` selects the launch engine
- **WHEN** delegation is disabled
- **THEN** the host Podman client retains that endpoint for engine verification, image operations, and launch
- **AND** the session container has no `CONTAINER_HOST` or delegated socket

#### Scenario: Enabled delegation replaces inherited defaults
- **GIVEN** the image defines a different container `CONTAINER_HOST`
- **WHEN** delegation is enabled and its selected service passes verification
- **THEN** the container receives exactly `CONTAINER_HOST=unix:///run/podman/podman.sock`

### Requirement: Socket validation is conditional
The wrapper SHALL validate the selected delegation socket only when Podman API access is enabled. Disabled delegation SHALL NOT require or query that endpoint separately from mandatory launch-engine verification. An enabled missing, non-socket, or inaccessible endpoint SHALL fail before image operations or launch with an actionable path-specific error.

#### Scenario: Disabled access without an API socket
- **GIVEN** the delegation socket does not exist and local host Podman can otherwise run containers
- **WHEN** the wrapper starts without `CLAUDE_CONTAINER_PODMAN=1`
- **THEN** socket absence does not prevent the wrapper from launching its container
- **AND** the wrapper verifies the launch engine without querying the delegation service

#### Scenario: Enabled access without a valid socket
- **GIVEN** the selected socket path is missing, is not a Unix socket, or is inaccessible
- **WHEN** the wrapper starts with `CLAUDE_CONTAINER_PODMAN=1`
- **THEN** it exits with a nonzero status before image operations or starting the container
- **AND** its error names the socket path and explains how to check or start the API service

#### Scenario: Disabled values skip service verification
- **WHEN** `CLAUDE_CONTAINER_PODMAN` is unset, empty, or any value other than the exact string `1`
- **THEN** the wrapper performs no separate delegation-endpoint verification and supplies neither the socket mount nor container `CONTAINER_HOST`
- **AND** an invalid delegation-socket override is ignored

#### Scenario: Wrapper uses a Unix launch service without delegation
- **WHEN** the wrapper uses an explicit same-host Unix launch service with delegation disabled
- **THEN** it verifies that launch engine but does not expose the launch socket inside the session

### Requirement: Access policy applies across launch modes
The wrapper SHALL apply the same access policy in Claude and `--container-shell` modes, including when combined with `--container-build` or `--container-git-worktree`. Host Podman SHALL remain required for image operations and launching the outer container regardless of the opt-in.

#### Scenario: Shell mode follows the opt-in
- **WHEN** the caller launches with `--container-shell`, with and without `CLAUDE_CONTAINER_PODMAN=1`
- **THEN** only the enabled launch receives the socket mount and `CONTAINER_HOST`

#### Scenario: Build and workspace options preserve the access policy
- **WHEN** the caller launches with `--container-build --container-git-worktree` in either access mode
- **THEN** the image build and parent workspace mount retain their existing behavior
- **AND** only the enabled launch receives the socket mount and `CONTAINER_HOST`

#### Scenario: Host Podman is missing
- **WHEN** the wrapper starts without Podman installed on the host, regardless of `CLAUDE_CONTAINER_PODMAN`
- **THEN** it fails with the existing host Podman prerequisite error

### Requirement: Document the optional authority grant
Wrapper help and README SHALL document exact `CLAUDE_CONTAINER_PODMAN=1`, the disabled default, endpoint selection, and remapped socket support. They SHALL distinguish launch-engine verification from delegation verification, explain that delegation permits host mounts beyond the workspace, and show migration for child-container workflows.

#### Scenario: Discover and enable access
- **WHEN** a user reads wrapper help and README usage instructions
- **THEN** the exact enabling value and disabled default are stated
- **AND** the README shows `CLAUDE_CONTAINER_PODMAN=1 ./claude-container.sh` and explains that delegation socket setup is needed only for enabled access
- **AND** it explains control over the service user's containers, volumes, and additional host bind mounts beyond the workspace

#### Scenario: Explain enforced rootless verification
- **WHEN** a user reads wrapper help and README instructions for enabled access
- **THEN** they learn that the selected socket must serve a reachable rootless engine and report an absolute host-side socket path, and failed verification blocks startup
- **AND** the README shows how to query the selected socket and recover from service or rootful-engine failures

#### Scenario: Endpoint migration reviewed
- **WHEN** a user reads the endpoint instructions
- **THEN** precedence, same-host path requirements, and an explicit override to pin an endpoint are documented
- **AND** the mandatory launch-engine check is distinguished from optional delegation verification

### Requirement: Exposed Podman service must report rootless operation
With API access enabled, the wrapper SHALL explicitly query the selected Unix endpoint and require successful rootless `true` and an absolute service-reported host socket path. Query failure or an invalid result SHALL fail before image operations or launch with an actionable error identifying the endpoint. The host-side path SHALL be the bind source exposed at `/run/podman/podman.sock`.

#### Scenario: Rootless service is verified
- **GIVEN** the selected Unix socket exists and its service reports rootless `true` and an absolute host socket path
- **WHEN** the wrapper starts with `CLAUDE_CONTAINER_PODMAN=1`
- **THEN** verification succeeds before image operations and container startup
- **AND** the service-reported socket mount and container `CONTAINER_HOST` are supplied

#### Scenario: Rootful service is rejected
- **GIVEN** the selected Unix socket exists and its service reports rootless operation as `false`
- **WHEN** the wrapper starts with `CLAUDE_CONTAINER_PODMAN=1`
- **THEN** it exits nonzero before image operations or container startup
- **AND** the error identifies the socket and explains that a rootless service is required

#### Scenario: Unreachable service is rejected
- **GIVEN** the selected Unix socket exists but the service query fails
- **WHEN** the wrapper starts with `CLAUDE_CONTAINER_PODMAN=1`
- **THEN** it exits nonzero before image operations or container startup
- **AND** the error identifies the socket and directs the user to check the service and access permissions

#### Scenario: Unrecognized service result is rejected
- **GIVEN** the service query succeeds but returns an empty or unexpected rootless result
- **WHEN** the wrapper starts with `CLAUDE_CONTAINER_PODMAN=1`
- **THEN** it exits nonzero before image operations or container startup because rootless operation was not confirmed
- **AND** the error identifies the socket and explains the rootless requirement

#### Scenario: Verification targets the exposed endpoint
- **GIVEN** default Podman configuration points at a different service from the selected delegation endpoint
- **WHEN** the wrapper verifies enabled API access
- **THEN** verification explicitly queries the selected Unix endpoint and uses that service's result

#### Scenario: Verification applies in all enabled launch modes
- **WHEN** enabled access is used in Claude or shell mode, including with `--container-build` and `--container-git-worktree`
- **THEN** the same service verification gates image operations and container startup
- **AND** a failed verification prevents even an explicitly requested image build

#### Scenario: Socket is remapped in the wrapper container
- **GIVEN** the wrapper reaches a same-host service through a remapped Unix path
- **WHEN** the selected endpoint reports a different absolute host-side socket path
- **THEN** the outer launch binds that host-side path rather than the client-visible path

#### Scenario: Host socket path is invalid
- **WHEN** an enabled delegation endpoint reports rootless `true` but a missing or relative host socket path
- **THEN** startup fails before image operations with a socket-specific diagnostic

### Requirement: Delegation endpoint selection
When delegation is enabled, the wrapper SHALL select a nonempty `CLAUDE_CONTAINER_PODMAN_SOCKET` first, then an explicit Unix `CONTAINER_HOST`, then `${XDG_RUNTIME_DIR:-/run/user/<caller-uid>}/podman/podman.sock`. It SHALL require an absolute accessible socket path and resolve its physical path. Selection SHALL NOT retarget the engine used to launch the outer container.

#### Scenario: Explicit override wins
- **WHEN** a socket override, Unix launch endpoint, and runtime directory are all configured
- **THEN** delegation verification explicitly targets the socket override without changing the launch endpoint

#### Scenario: Unix launch endpoint reused
- **WHEN** no socket override is set and an explicit Unix launch endpoint is configured
- **THEN** that endpoint is selected for delegation verification

#### Scenario: Runtime directory fallback
- **WHEN** neither an override nor a Unix launch endpoint is configured
- **THEN** the socket is selected under `XDG_RUNTIME_DIR`, falling back to `/run/user/<caller-uid>` when unset or empty

#### Scenario: Relative override rejected
- **WHEN** delegation is enabled and its selected socket path is relative
- **THEN** startup fails with an absolute-path requirement before image operations

### Requirement: Single-record delegation verification response
Enabled delegation verification SHALL accept exactly one valid rootless/socket-path response record, with no terminator or one final LF. Any CR character SHALL be rejected before field parsing or host-path use. Additional records, including blank records or extra trailing LF characters, SHALL fail before image operations or launch with an endpoint-specific error. Capture SHALL preserve record boundaries and query failure status. Disabled delegation SHALL continue to skip this separate query.

#### Scenario: Normal delegated response terminator
- **WHEN** the selected service successfully returns one valid response with no final LF or exactly one final LF
- **THEN** delegation verification accepts the response and retains its reported host-side socket path

#### Scenario: Extra blank delegated response records
- **WHEN** the selected service returns a valid first record followed by one or more blank records
- **THEN** startup fails with an invalid-response error naming the selected endpoint
- **AND** no image inspection, explicit build, or launch occurs

#### Scenario: Extra nonblank delegated response records
- **WHEN** the selected service returns a valid first record followed by another nonblank record
- **THEN** startup fails before image operations or launch with an endpoint-specific invalid-response error

#### Scenario: Delegated query fails after emitting valid data
- **WHEN** the selected service query emits valid-looking output but exits nonzero
- **THEN** startup fails with the existing endpoint-specific query-failure guidance
- **AND** the output does not establish rootless operation

#### Scenario: Disabled delegation does not introduce a query
- **WHEN** delegation is disabled, including while using a valid Unix launch endpoint
- **THEN** only mandatory launch-engine verification applies
- **AND** the wrapper performs no separate delegation-response validation or socket query

#### Scenario: CRLF delegated response is rejected
- **WHEN** the selected service successfully returns an otherwise valid record terminated by CRLF
- **THEN** startup fails with an invalid-response error naming the selected endpoint before field parsing or host-path use
- **AND** no image inspection, explicit build, or container creation occurs

#### Scenario: Embedded or standalone CR is rejected
- **WHEN** the selected service successfully returns a response containing CR anywhere, including in the rootless field, between fields, inside the host socket path, or as a standalone final CR
- **THEN** startup fails with an invalid-response error naming the selected endpoint before field parsing or host-path use
- **AND** no image inspection, explicit build, or container creation occurs

#### Scenario: Host socket path containing spaces is preserved
- **WHEN** the selected service successfully returns a valid CR-free record reporting an absolute host socket path containing spaces, with no terminator or exactly one final LF
- **THEN** delegation verification accepts the response
- **AND** the reported host socket path is preserved as the bind source exposed at `/run/podman/podman.sock`
