# container-podman-access Specification

## Purpose

Control access from wrapper-launched Claude and shell sessions to the host Podman API, granting it only through an explicit host environment opt-in.

## Requirements

### Requirement: Podman API access requires the exact opt-in value
The wrapper SHALL grant access to the host Podman API only when `CLAUDE_CONTAINER_PODMAN` equals the exact string `1`. An unset, empty, or different value SHALL disable that access.

#### Scenario: Variable is unset
- **WHEN** the wrapper starts with `CLAUDE_CONTAINER_PODMAN` unset
- **THEN** it does not mount the host Podman socket or set `CONTAINER_HOST` in the container

#### Scenario: Variable does not equal one
- **WHEN** the wrapper starts with `CLAUDE_CONTAINER_PODMAN` empty or set to `0`, `true`, `yes`, `01`, or another value other than the exact string `1`
- **THEN** it starts with Podman API access disabled without rejecting that value
- **AND** it does not mount the host Podman socket or set `CONTAINER_HOST` in the container

#### Scenario: Access is explicitly enabled
- **GIVEN** `/run/user/<caller-uid>/podman/podman.sock` is a Unix socket
- **WHEN** the wrapper starts with `CLAUDE_CONTAINER_PODMAN=1`
- **THEN** it mounts that socket at `/run/podman/podman.sock`
- **AND** it sets `CONTAINER_HOST=unix:///run/podman/podman.sock` in the container

### Requirement: Socket validation is conditional
The wrapper SHALL validate the existing rootless host socket path only when Podman API access is enabled. Disabled access SHALL NOT require an API socket. Enabled access with a missing or non-socket path SHALL fail before starting the container with an actionable message identifying the socket path.

#### Scenario: Disabled access without an API socket
- **GIVEN** the rootless host API socket does not exist and host Podman can otherwise run containers
- **WHEN** the wrapper starts without `CLAUDE_CONTAINER_PODMAN=1`
- **THEN** socket absence does not prevent the wrapper from launching its container

#### Scenario: Enabled access without a valid socket
- **GIVEN** the expected rootless host socket path is missing or is not a Unix socket
- **WHEN** the wrapper starts with `CLAUDE_CONTAINER_PODMAN=1`
- **THEN** it exits with a non-zero status before starting the container
- **AND** its error names the socket path and explains how to start the API service

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
Wrapper help and the README SHALL document `CLAUDE_CONTAINER_PODMAN=1`, the disabled default, and exact-value semantics. The README SHALL distinguish the host Podman prerequisite from the optional API socket, explain the authority granted by enabling access, and show how existing child-container workflows migrate.

#### Scenario: Discover and enable access
- **WHEN** a user reads wrapper help and README usage instructions
- **THEN** the exact enabling value and disabled default are stated
- **AND** the README shows `CLAUDE_CONTAINER_PODMAN=1 ./claude-container.sh` and explains that API socket setup is needed only for enabled access
- **AND** the README explains that enabling access grants control over containers and volumes available to the host Podman user
