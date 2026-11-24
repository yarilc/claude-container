# Spec Delta

## ADDED Requirements

### Requirement: Leftover delegation opt-in is refused
An exact `CLAUDE_CONTAINER_PODMAN=1` in the launch environment SHALL stop every session launch and build-only operation, in every network mode, before any engine query or image operation. The diagnostic SHALL state that host Podman delegation was removed. It SHALL direct the operator to add needed images as toolchains and to unset the variable. Other values of the variable, and the former socket override, SHALL be ignored.

#### Scenario: Unrestricted launch with the old opt-in
- **WHEN** an operator starts an unrestricted session with `CLAUDE_CONTAINER_PODMAN=1`
- **THEN** the wrapper exits nonzero before querying an engine, names the variable, and points to image toolchains and the README section on container tests

#### Scenario: Other values
- **WHEN** `CLAUDE_CONTAINER_PODMAN` is empty or `0`, or `CLAUDE_CONTAINER_PODMAN_SOCKET` is set
- **THEN** the launch proceeds as if the variables were unset, and no Podman socket is mounted

#### Scenario: Help and toolchain commands
- **WHEN** `--container-help` or `--container-toolchain list` runs with `CLAUDE_CONTAINER_PODMAN=1`
- **THEN** the command succeeds unchanged

## MODIFIED Requirements

### Requirement: Verified launch engine
After ordinary launch configuration is admitted, the wrapper SHALL verify that the engine used for image operations and container launch reports Linux and rootless operation. Failed or unrecognized verification SHALL stop before image inspection, build, or container creation. Every read-only engine query SHALL be bounded by a timeout: `info`, `version`, `ps`, image and container existence and inspection, and the session container engine's readiness query. `create`, `start`, `build` and `pull` SHALL NOT be bounded. Setup SHALL verify the engine after approved user-service preparation and before image operations or smoke/login container creation. Help and missing-setup refusal SHALL require no engine query.

#### Scenario: Local rootless engine without delegation
- **WHEN** local Podman reports Linux and rootless operation
- **THEN** engine verification succeeds without requiring or exposing any Podman API socket

#### Scenario: Engine cannot be verified
- **WHEN** engine verification fails or reports rootful, non-Linux, empty, or malformed results
- **THEN** the wrapper exits nonzero with an actionable engine error before image operations or launch

#### Scenario: Setup can diagnose missing prerequisites
- **WHEN** interactive setup is requested before Podman or its required user service is usable
- **THEN** it can diagnose prerequisites and offer permitted user-service preparation without normal session preflight
- **AND** no image operation or container creation occurs until the selected engine passes verification

#### Scenario: Unconfigured invocation does not need an engine
- **WHEN** an ordinary invocation without a network mode and without provider settings runs while Podman is missing or unavailable
- **THEN** the wrapper reports the setup-required diagnostic without querying an engine

#### Scenario: Stalled engine query
- **WHEN** a read-only engine query does not answer
- **THEN** the wrapper stops after the query timeout with the query's diagnostic and creates no container

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
- **AND** the rejection applies whether or not the session would get a container engine

#### Scenario: Relative Unix endpoint
- **WHEN** `CONTAINER_HOST` is a Unix endpoint with a relative path
- **THEN** startup fails before querying Podman with guidance to use an absolute socket pathname

#### Scenario: Help ignores invalid launch configuration
- **WHEN** `--container-help` is requested with a pathless Unix endpoint
- **THEN** help succeeds without contacting an engine or creating state

### Requirement: Predictable image operations
The wrapper SHALL build an absent image, and refresh it on `--container-build`, only with explicit `CLAUDE_CONTAINER_MAINTENANCE=1`. It SHALL use the Containerfile beside the resolved wrapper script. Without that exact authorization, a required build SHALL fail with maintenance guidance before image acquisition or build. Runtime network mode SHALL NOT grant maintenance authority or imply filtering of host image pulls or build RUN steps. An image-inspection error other than absence SHALL fail without starting a build or container. Build failures SHALL stop the launch and preserve the failure status.

A build SHALL proceed as follows:
- It SHALL first pull any missing exact `FROM` base.
- It SHALL then run `podman build --pull=never --format docker` without a timeout and with stdin from `/dev/null`.
- It SHALL pass a trusted host CA bundle only as the `build-ca` build secret.

Every image SHALL carry a `build-inputs-hash` label over its build inputs. A launch SHALL refuse an image whose label does not match the current inputs, with rebuild guidance.

`--container-build` with no Claude argument SHALL validate every launch setting, build, and exit without a session. `--container-git-worktree` and `--container-shell` do not count as Claude arguments.

An image name with whitespace or control characters SHALL be refused before any engine operation.

#### Scenario: Image absent from an external workspace
- **WHEN** the wrapper is invoked through a symlink outside its repository with explicit unrestricted mode, the image is absent, and maintenance is explicitly authorized
- **THEN** it builds using the Containerfile beside the physical wrapper script

#### Scenario: Inspection failure
- **WHEN** image inspection reports an engine error rather than absence
- **THEN** the wrapper exits nonzero without attempting a build or launch

#### Scenario: Explicit build fails
- **WHEN** `--container-build` is requested with explicit maintenance authorization and the build fails
- **THEN** the wrapper returns the build failure status without creating a session container

#### Scenario: Build requires separate authorization
- **WHEN** an image is absent or `--container-build` is requested without exact maintenance authorization
- **THEN** the wrapper exits before any pull or build with guidance for an operator maintenance invocation
- **AND** neither provider nor unrestricted runtime mode implicitly authorizes that build

#### Scenario: Restricted setup gates build
- **WHEN** a restricted session, including the default provider mode, lacks a protected installation or its provider settings, selects an invalid policy, or carries a leftover exact `CLAUDE_CONTAINER_PODMAN=1`
- **THEN** startup fails before image build even with maintenance authorization

#### Scenario: Build-only operation
- **WHEN** `--container-build` is given with maintenance authorization and no Claude argument, also together with `--container-git-worktree`
- **THEN** the wrapper validates its settings, builds the image and exits with the build status without creating a container
- **AND** an invalid setting, such as a leftover delegation opt-in, stops it before the build

#### Scenario: Stale image
- **WHEN** the Containerfile or another build input changed after the image was built
- **THEN** a launch without `--container-build` stops before creation and names the rebuild command
