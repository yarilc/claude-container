# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
