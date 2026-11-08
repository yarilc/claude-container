# Spec Delta

## MODIFIED Requirements

### Requirement: Verified launch engine
After ordinary launch configuration is admitted, the wrapper SHALL verify that the engine used for image operations and container launch reports Linux and rootless operation. Failed or unrecognized verification SHALL stop before image inspection, build, or container creation. Setup SHALL verify the engine after approved user-service preparation and before image operations or smoke/login container creation. Help and missing-configuration refusal SHALL require no engine query.

#### Scenario: Local rootless engine without delegation
- **WHEN** local Podman reports Linux and rootless operation and delegation is disabled
- **THEN** engine verification succeeds without requiring a delegation socket

#### Scenario: Engine cannot be verified
- **WHEN** engine verification fails or reports rootful, non-Linux, empty, or malformed results
- **THEN** the wrapper exits nonzero with an actionable engine error before image operations or launch

#### Scenario: Setup can diagnose missing prerequisites
- **WHEN** interactive setup is requested before Podman or its required user service is usable
- **THEN** it can diagnose prerequisites and offer permitted user-service preparation without normal session preflight
- **AND** no image operation or container creation occurs until the selected engine passes verification

#### Scenario: Unconfigured invocation does not need an engine
- **WHEN** ordinary invocation has no usable runtime mode and Podman is missing or unavailable
- **THEN** the wrapper reports the setup-required diagnostic without querying an engine

## ADDED Requirements

### Requirement: Actionable missing-setup admission
An ordinary launch with an unset or empty effective `CLAUDE_CONTAINER_NETWORK` SHALL exit with status 1 and an English stderr message directing the user to invoke the wrapper with `--container-setup`. Refusal SHALL precede runtime prerequisite checks, engine queries, state creation and image/resource operations. It SHALL NOT prompt, run setup or launch an application.

#### Scenario: First ordinary invocation
- **WHEN** the wrapper is invoked without an effective network mode, interactively or with redirected input
- **THEN** it returns status 1 with the setup-required stderr message and no application stdout
- **AND** it creates no state or runtime resources and performs no engine or image operation

#### Scenario: Build and shell options cannot supply configuration
- **WHEN** an unconfigured ordinary invocation uses shell, build or worktree options, including combinations with `CLAUDE_CONTAINER_MAINTENANCE=1`
- **THEN** it receives the same setup-required refusal before state creation or engine operations
- **AND** maintenance consent does not select a runtime mode

#### Scenario: Other environment settings do not imply setup
- **WHEN** an ordinary invocation supplies state, image, endpoint, provider-policy or authority settings without a nonempty network mode
- **THEN** it receives setup guidance before runtime validation of those settings
- **AND** configuration or report files present in the current directory do not admit the launch

#### Scenario: Dedicated entry points remain reachable
- **WHEN** help, interactive setup or the standalone qualification operation is requested without a network mode
- **THEN** that entry point retains its own existing argument, terminal, prerequisite and enforcement checks without ordinary missing-setup admission
- **AND** help still takes precedence and qualification still cannot execute a supplied application command

### Requirement: First-user setup and migration guidance
README, wrapper help and setup guidance SHALL identify `--container-setup` as the mandatory first step for new users. They SHALL explain managed launch, the explicit operator alternative, offline API unavailability and migration from versions before `c777b73`. Network documentation SHALL describe missing-mode refusal consistently.

#### Scenario: User follows first-run guidance
- **WHEN** a new user reads help or the README
- **THEN** instructions show how to invoke setup and subsequently use its managed launcher
- **AND** explain that an offline session cannot reach the Claude API and no unrestricted fallback is automatic

#### Scenario: Operator migrates an existing direct invocation
- **WHEN** an operator reads the migration guidance
- **THEN** it explains that versions before `c777b73` did not require explicit runtime network selection, subsequent versions defaulted to offline, and this change refuses an ordinary missing-mode launch
- **AND** gives explicit mode examples, including separately authorized maintenance, without implying that mode selection proves restricted readiness
