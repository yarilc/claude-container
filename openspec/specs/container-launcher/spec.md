# container-launcher Specification

## Purpose

Provide predictable rootless container startup, transparent CLI invocation, and a lifecycle that preserves session ownership and termination behavior.

## Requirements

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
The wrapper SHALL preserve the order, spaces, and empty values of forwarded Claude arguments. It SHALL preserve stdin and allocate a TTY only when stdin and stdout are terminals. Shell mode SHALL start Bash with the selected mounts and identity, without Claude arguments or wrapper-injected YOLO flags. Restricted-mode Claude and shell invocations SHALL enter through the protected Landlock/seccomp bootstrap before untrusted initialization; arguments, stdin, terminal allocation, signals, and application status SHALL retain the same contract.

#### Scenario: Pipeline invocation
- **WHEN** Claude is invoked with redirected stdin and arguments containing spaces or empty values
- **THEN** stdin and arguments reach Claude unchanged without mandatory TTY allocation

#### Scenario: Interactive session
- **WHEN** stdin and stdout are terminals
- **THEN** the wrapper allocates a TTY and forwards an existing `TERM` by name

#### Scenario: Shell invocation
- **WHEN** `--container-shell` is combined with Claude arguments and enabled YOLO
- **THEN** Bash starts without receiving those arguments or the permission-bypass flag

#### Scenario: Bootstrap rejects preparation
- **WHEN** restricted-mode bootstrap validation or confinement fails
- **THEN** it exits nonzero without executing the application or an agent-controlled initialization hook
- **AND** the wrapper preserves that failure, reports the enforcement stage on stderr, and removes owned setup resources

#### Scenario: Target WSL enforcement
- **WHEN** the session runs on the measured WSL x86_64 target or a locally qualified native Linux/WSL2 x86_64 installation with usable Landlock ABI >= 3 and standard OCI policy
- **THEN** bootstrap preparation supports that ABI without requiring a kernel upgrade or ABI-9 features
- **AND** both required enforcement layers must install before application initialization

#### Scenario: Guarded pipeline and terminal
- **WHEN** a supported restricted session receives piped input or an interactive terminal
- **THEN** the bootstrap and relay preserve empty/spaced arguments and input/terminal behavior
- **AND** bootstrap diagnostics do not contaminate application stdout

### Requirement: Side effect free wrapper help
`--container-help` SHALL display wrapper options and environment controls successfully without requiring Podman, creating state, or performing engine or image operations.

#### Scenario: Help without prerequisites
- **WHEN** wrapper help is requested with Podman unavailable and invalid runtime configuration
- **THEN** help succeeds without creating directories or contacting an engine

### Requirement: Predictable image operations
The wrapper SHALL build an absent image and refresh it on `--container-build` only with explicit `CLAUDE_CONTAINER_MAINTENANCE=1`, using the Containerfile beside the resolved wrapper script. Without that exact authorization, a required build SHALL fail with maintenance guidance before image acquisition or build. Runtime network mode SHALL NOT grant maintenance authority or imply filtering of host image pulls or build RUN steps. An image-inspection error other than absence SHALL fail without starting a build or container. Build failures SHALL stop launch and preserve the failure status.

#### Scenario: Image absent from an external workspace
- **WHEN** the wrapper is invoked through a symlink outside its repository, the image is absent, and maintenance is explicitly authorized
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
- **WHEN** a restricted session selects an invalid policy, unsupported enforcement backend, or enabled socket delegation
- **THEN** startup fails before image build even with maintenance authorization

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
After a setup failure, session signal, or application exit, wrapper shutdown SHALL finish within a 20-second overall budget shared by the agent container, proxy containers, transport endpoints, configuration, and local clients. Only resources with confirmed session ownership SHALL be removed. Signal shutdown SHALL allow at most five seconds for graceful application exit before attempting forced removal. Engine control calls and local client termination/reaping SHALL be bounded within that budget. Cleanup failures SHALL be reported without replacing the primary application or signal exit status.

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

#### Scenario: Network cleanup shares the deadline
- **WHEN** setup fails or shutdown encounters stalled proxy or transport cleanup
- **THEN** ownership recovery, container removal, and local cleanup share one deadline without replacing the primary exit status
- **AND** diagnostics identify any owned resource whose removal could not be confirmed

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

### Requirement: Restricted launches require current local qualification
Before ordinary offline/provider application execution, the wrapper SHALL validate a protected successful qualification report matching the current host, engine and enforcement inputs. Missing or mismatched evidence SHALL stop startup with requalification guidance. A report SHALL NOT replace per-launch engine, protected-path, guard, policy or readiness checks. Unrestricted launches and wrapper help SHALL NOT require this report.

#### Scenario: Changed environment or artifacts
- **WHEN** kernel/boot, engine version/backend/endpoint, effective security-policy state, guard/code, runtime/proxy image identity, hardening, gate revision or selected mode/profile/policy differs from the report
- **THEN** ordinary restricted startup fails before application execution and requests requalification
- **AND** changing environment variables or managed defaults never suppresses that failure

#### Scenario: Matching evidence
- **WHEN** a trusted complete report matches the effective restricted workflow and all per-launch enforcement checks pass
- **THEN** the requested application can start with its existing argument, stdin, terminal and exit-status semantics
- **AND** a locally qualified combination without recorded full acceptance is visibly identified as not release-measured

#### Scenario: Explicit qualification operation
- **WHEN** the operator invokes the dedicated qualification operation without a current report
- **THEN** only the protected gate fixtures run through normal confinement and resource preparation
- **AND** no supplied application command or writable fixture can execute through the report-check exception

### Requirement: Consistent restricted prerequisite decisions
Wrapper startup and interactive setup SHALL use the same protected platform eligibility rules and diagnostic categories. Malformed or unavailable engine/platform evidence SHALL fail closed. The shared rules SHALL preserve launch endpoint verification and SHALL NOT reject SELinux/AppArmor merely for being enabled.

#### Scenario: Setup and direct wrapper receive the same evidence
- **WHEN** setup and direct restricted startup inspect equivalent host and engine evidence
- **THEN** they agree on capability eligibility and identify the same failed prerequisite
- **AND** setup additionally requires candidate qualification before activation while ordinary startup requires current qualification

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

### Requirement: Optional session lifetime limit
`CLAUDE_CONTAINER_RUN_TIMEOUT` SHALL set the native engine lifetime of the agent container in whole seconds. When it is unset, empty or `0`, no lifetime limit SHALL apply. Any other value that is not a positive decimal integer SHALL fail with status 1 before engine queries. The limit SHALL be independent of the 20-second shutdown budget and of proxy lifetime.

#### Scenario: Lifetime disabled by default
- **WHEN** `CLAUDE_CONTAINER_RUN_TIMEOUT` is unset
- **THEN** the agent container is created without a lifetime limit

#### Scenario: Lifetime expires
- **WHEN** `CLAUDE_CONTAINER_RUN_TIMEOUT=60` is set and the application is still running after 60 seconds
- **THEN** the engine stops the agent container
- **AND** the wrapper prints a stderr notice that the session lifetime limit was reached
- **AND** the wrapper exits with the engine client's status (255 on the measured Podman 4.9.3 server), then cleans up owned resources, including a provider proxy, within the shutdown budget

#### Scenario: Session ends before the limit
- **WHEN** the application exits before the limit
- **THEN** the wrapper propagates the application exit status unchanged and prints no lifetime notice

#### Scenario: Invalid lifetime value
- **WHEN** `CLAUDE_CONTAINER_RUN_TIMEOUT` is negative, fractional or non-numeric
- **THEN** the wrapper exits with status 1 and names the variable before any engine query or state creation

### Requirement: Qualification binds agent hardening settings
The qualification identity of a restricted installation SHALL include:
- the agent capability and no-new-privileges settings;
- the selected memory, CPU and process budgets;
- the session lifetime setting.

A launch whose effective settings differ from the qualified identity SHALL stop with requalification guidance.

#### Scenario: Budget changed after qualification
- **WHEN** a restricted installation was qualified with default budgets and the operator launches with `CLAUDE_CONTAINER_PIDS_LIMIT=1024`
- **THEN** the qualification check reports mismatched evidence and the application does not start

#### Scenario: Qualification with matching settings
- **WHEN** the operator qualifies and launches with the same budgets and lifetime
- **THEN** the qualification check accepts the report

### Requirement: Hardening controls are documented
Wrapper help and the README SHALL document:
- the budget variables, their defaults and accepted formats;
- the lifetime variable;
- the unsafe-workspace override and the refused directories;
- that capabilities are dropped in every mode.

Help SHALL remain side effect free.

#### Scenario: Operator reads wrapper help
- **WHEN** the operator runs `--container-help`
- **THEN** the output lists `CLAUDE_CONTAINER_MEMORY_LIMIT`, `CLAUDE_CONTAINER_CPU_LIMIT`, `CLAUDE_CONTAINER_PIDS_LIMIT`, `CLAUDE_CONTAINER_RUN_TIMEOUT` and `CLAUDE_CONTAINER_ALLOW_UNSAFE_WORKSPACE` with their defaults
- **AND** no engine query or state creation occurs
