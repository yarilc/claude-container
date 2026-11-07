# Spec Delta

## MODIFIED Requirements

### Requirement: Podman API access requires the exact opt-in value
The wrapper SHALL grant access to the host Podman API only when `CLAUDE_CONTAINER_PODMAN` equals the exact string `1` and the operator explicitly selects unrestricted runtime networking. Exact socket opt-in in offline or provider mode SHALL fail before delegation-endpoint checks, image operations, or resource creation. An unset, empty, or different value SHALL disable that access, omit the socket mount, and ensure `CONTAINER_HOST` is absent from the launched container environment, including values supplied by image or engine defaults.

#### Scenario: Variable is unset
- **WHEN** the wrapper starts with `CLAUDE_CONTAINER_PODMAN` unset
- **THEN** it does not mount the host Podman socket and container `CONTAINER_HOST` is absent

#### Scenario: Variable does not equal one
- **WHEN** the wrapper starts with `CLAUDE_CONTAINER_PODMAN` empty or set to `0`, `true`, `yes`, `01`, or another value other than the exact string `1`
- **THEN** it starts with Podman API access disabled without rejecting that value
- **AND** it does not mount the host Podman socket and container `CONTAINER_HOST` is absent

#### Scenario: Access is explicitly enabled
- **GIVEN** unrestricted runtime networking is selected and the selected Unix socket serves a reachable engine that reports rootless operation and an absolute host-side socket path
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
- **WHEN** unrestricted runtime networking is selected, delegation is enabled, and its selected service passes verification
- **THEN** the container receives exactly `CONTAINER_HOST=unix:///run/podman/podman.sock`

#### Scenario: Restricted mode rejects exact opt-in
- **WHEN** offline or provider mode is selected with exact `CLAUDE_CONTAINER_PODMAN=1`
- **THEN** startup rejects the combination before querying the delegation endpoint or performing image/resource operations
- **AND** the diagnostic explains that host API access bypasses network enforcement and requires explicit unrestricted mode


### Requirement: Access policy applies across launch modes
The wrapper SHALL apply the same access policy in Claude and `--container-shell` modes, including when combined with `--container-build` or `--container-git-worktree`. Restricted modes SHALL reject exact socket opt-in in every composition, including YOLO/native permission settings. Host Podman SHALL remain required for image operations and launching the outer container regardless of the opt-in.

#### Scenario: Shell mode follows the opt-in
- **WHEN** the caller selects unrestricted networking and launches with `--container-shell`, with and without `CLAUDE_CONTAINER_PODMAN=1`
- **THEN** only the enabled launch receives the socket mount and `CONTAINER_HOST`

#### Scenario: Build and workspace options preserve the access policy
- **WHEN** the caller selects unrestricted networking and explicitly authorized maintenance with `--container-build --container-git-worktree` in either access mode
- **THEN** the image build and parent workspace mount retain their existing behavior
- **AND** only the enabled launch receives the socket mount and `CONTAINER_HOST`

#### Scenario: Host Podman is missing
- **WHEN** the wrapper starts without Podman installed on the host, regardless of `CLAUDE_CONTAINER_PODMAN`
- **THEN** it fails with the existing host Podman prerequisite error

### Requirement: Document the optional authority grant
Wrapper help and README SHALL document exact `CLAUDE_CONTAINER_PODMAN=1`, the disabled default, endpoint selection, and remapped socket support. They SHALL distinguish launch-engine verification from delegation verification, explain that delegation permits host mounts beyond the workspace, and show migration for child-container workflows through explicit unrestricted mode. Documentation SHALL explain restricted-mode rejection and that delegated builds need a separately enforced environment or policy broker; child proxy variables alone are insufficient.

#### Scenario: Discover and enable access
- **WHEN** a user reads wrapper help and README usage instructions
- **THEN** the exact enabling value and disabled default are stated
- **AND** the README shows `CLAUDE_CONTAINER_NETWORK=unrestricted CLAUDE_CONTAINER_PODMAN=1 ./claude-container.sh` and explains that delegation socket setup is needed only for enabled access
- **AND** it explains control over the service user's containers, volumes, and additional host bind mounts beyond the workspace

#### Scenario: Explain enforced rootless verification
- **WHEN** a user reads wrapper help and README instructions for enabled access
- **THEN** they learn that the selected socket must serve a reachable rootless engine and report an absolute host-side socket path, and failed verification blocks startup
- **AND** the README shows how to query the selected socket and recover from service or rootful-engine failures

#### Scenario: Endpoint migration reviewed
- **WHEN** a user reads the endpoint instructions
- **THEN** precedence, same-host path requirements, and an explicit override to pin an endpoint are documented
- **AND** the mandatory launch-engine check is distinguished from optional delegation verification
