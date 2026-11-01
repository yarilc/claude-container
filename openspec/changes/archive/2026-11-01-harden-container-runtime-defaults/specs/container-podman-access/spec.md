# Spec Delta

## MODIFIED Requirements

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
