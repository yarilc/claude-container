# container-launcher Specification

## Purpose

Provide predictable rootless container startup, transparent CLI invocation, and a lifecycle that preserves session ownership and termination behavior.

## Requirements

### Requirement: Verified launch engine
After ordinary launch configuration is admitted, the wrapper SHALL verify that the engine used for image operations and container launch reports Linux and rootless operation. Failed or unrecognized verification SHALL stop before image inspection, build, or container creation. Every read-only engine query SHALL be bounded by a timeout: `info`, `version`, `ps`, image and container existence and inspection, and the delegation socket query. `create`, `start`, `build` and `pull` SHALL NOT be bounded. Setup SHALL verify the engine after approved user-service preparation and before image operations or smoke/login container creation. Help and missing-setup refusal SHALL require no engine query.

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
- **AND** the rejection applies with delegation enabled or disabled, including an explicit delegation-socket override

#### Scenario: Relative Unix endpoint
- **WHEN** `CONTAINER_HOST` is a Unix endpoint with a relative path
- **THEN** startup fails before querying Podman with guidance to use an absolute socket pathname

#### Scenario: Help ignores invalid launch configuration
- **WHEN** `--container-help` is requested with a pathless Unix endpoint
- **THEN** help succeeds without contacting an engine or creating state

### Requirement: Transparent invocation and terminal handling
The wrapper SHALL preserve the order, spaces, and empty values of forwarded Claude arguments. It SHALL preserve stdin and allocate a TTY only when stdin and stdout are terminals. Shell mode SHALL start Bash with the selected mounts and identity and pass the wrapper's arguments to Bash in every network mode, without the permission-bypass flag.

The session environment SHALL be as follows:
- The session SHALL receive `USER`, `EDITOR=nano` and `VISUAL=nano`, plus `TERM`, `COLORTERM`, `LANG` and `LC_ALL` by name when set.
- Unrestricted sessions SHALL also receive `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY` and their lowercase forms by name when set. Restricted sessions SHALL never receive them.
- Offline and unrestricted sessions SHALL forward no credential variable, unless `CLAUDE_CONTAINER_ENV_VARS` lists it in unrestricted mode.

Restricted-mode Claude and shell invocations SHALL enter through the protected Landlock/seccomp bootstrap before untrusted initialization. Arguments, stdin, terminal allocation, signals, and application status SHALL retain the same contract.

#### Scenario: Pipeline invocation
- **WHEN** Claude is invoked with redirected stdin and arguments containing spaces or empty values
- **THEN** stdin and arguments reach Claude unchanged without mandatory TTY allocation

#### Scenario: Interactive session
- **WHEN** stdin and stdout are terminals
- **THEN** the wrapper allocates a TTY and forwards an existing `TERM` by name

#### Scenario: Shell invocation
- **WHEN** `--container-shell -c 'echo ok'` is used with enabled YOLO, in any network mode
- **THEN** Bash receives `-c 'echo ok'` and not the permission-bypass flag

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

#### Scenario: Locale and proxy forwarding
- **WHEN** the host sets `LANG`, `HTTPS_PROXY` and `EDITOR=vim`
- **THEN** an unrestricted session receives `LANG` and `HTTPS_PROXY` by name and `EDITOR=nano`
- **AND** an offline session receives `LANG` but not `HTTPS_PROXY`

### Requirement: Side effect free wrapper help
`--container-help` SHALL display wrapper options and environment controls successfully without requiring Podman, creating state, or performing engine or image operations.

#### Scenario: Help without prerequisites
- **WHEN** wrapper help is requested with Podman unavailable and invalid runtime configuration
- **THEN** help succeeds without creating directories or contacting an engine

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
- **WHEN** a restricted session, including the default provider mode, lacks a protected installation or its provider settings, selects an invalid policy, or selects enabled socket delegation
- **THEN** startup fails before image build even with maintenance authorization

#### Scenario: Build-only operation
- **WHEN** `--container-build` is given with maintenance authorization and no Claude argument, also together with `--container-git-worktree`
- **THEN** the wrapper validates its settings, builds the image and exits with the build status without creating a container
- **AND** an invalid setting, such as an unusable delegation socket, stops it before the build

#### Scenario: Stale image
- **WHEN** the Containerfile or another build input changed after the image was built
- **THEN** a launch without `--container-build` stops before creation and names the rebuild command

### Requirement: Owned container lifecycle
Concurrent sessions SHALL reserve distinct workspace-index names without removing another session's container. The wrapper SHALL clean up only its own container, propagate its process exit code, and forward INT, TERM, and HUP.

Naming collisions SHALL be retried within a bounded limit. Unrelated creation failures SHALL retain their diagnostics and status. A failed create whose name holds this session's own container SHALL never count as a collision: that container SHALL be removed, or reported as unresolved. Interruption during creation SHALL retain recoverable evidence of session ownership.

Each create attempt SHALL set `CONTAINER_NAME` to the reserved name and run with stdin from `/dev/null`. Unrestricted sessions SHALL run with `--init`.

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

#### Scenario: Own container behind a failed create
- **WHEN** create fails without publishing an ID and the engine reports this session's ownership label for the name
- **THEN** the wrapper returns the create status without retrying and removes that container

#### Scenario: Session name inside the container
- **WHEN** an unrestricted session starts as `<prefix>-3`
- **THEN** it runs with `--init` and `CONTAINER_NAME=<prefix>-3`

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
Launch-engine verification SHALL accept exactly one valid response record, with no terminator or one final LF. Additional records, including empty records or extra trailing LF characters, and any CR character SHALL fail before image operations or container creation. Capture SHALL preserve record boundaries and command failure status; successful-looking output from a failed query SHALL NOT verify the engine. The same capture SHALL serve every read-only engine query.

#### Scenario: Normal response terminator
- **WHEN** a successful engine query emits one valid response with no final LF or exactly one final LF
- **THEN** launch-engine verification accepts the response

#### Scenario: Additional blank or nonblank records
- **WHEN** the engine query emits a valid first record followed by a blank record, additional nonblank record, or multiple trailing LF characters
- **THEN** startup fails with an invalid-engine-response diagnostic before image inspection, build, or creation

#### Scenario: Query fails after emitting valid data
- **WHEN** the engine query emits valid-looking output but exits nonzero
- **THEN** startup fails with the engine-query diagnostic and performs no image operation or launch

#### Scenario: Carriage return in a response
- **WHEN** an engine query response contains a CR character
- **THEN** startup fails with the invalid-response diagnostic

### Requirement: Restricted launches require current local qualification
Before an ordinary offline or provider application runs, the wrapper SHALL validate a protected successful qualification report. The report SHALL match the current host, engine and enforcement inputs, and the network mode the launcher resolved, including Claude's provider default. Missing or mismatched evidence SHALL stop startup with requalification guidance. A report SHALL NOT replace per-launch engine, protected-path, guard, policy or readiness checks. Unrestricted launches and wrapper help SHALL NOT require this report.

#### Scenario: Changed environment or artifacts
- **WHEN** any of these differs from the report: kernel/boot, engine version/backend/endpoint, effective security-policy state, guard/code, runtime/proxy image identity, hardening, gate revision, or the selected mode/profile/policy
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

#### Scenario: Default mode reaches the qualification check
- **WHEN** a launch leaves `CLAUDE_CONTAINER_NETWORK` unset
- **THEN** the qualification check and every Python helper use `provider`, the mode the launcher resolved from the profile

### Requirement: Consistent restricted prerequisite decisions
Wrapper startup and interactive setup SHALL use the same protected platform eligibility rules and diagnostic categories. Malformed or unavailable engine/platform evidence SHALL fail closed. The shared rules SHALL preserve launch endpoint verification and SHALL NOT reject SELinux/AppArmor merely for being enabled.

#### Scenario: Setup and direct wrapper receive the same evidence
- **WHEN** setup and direct restricted startup inspect equivalent host and engine evidence
- **THEN** they agree on capability eligibility and identify the same failed prerequisite
- **AND** setup additionally requires candidate qualification before activation while ordinary startup requires current qualification

### Requirement: Actionable missing-setup admission
An ordinary launch with an unset or empty effective `CLAUDE_CONTAINER_NETWORK` SHALL select `provider`, Claude's default mode. When the checkout or installation has no built guard, or when any of `CLAUDE_CONTAINER_NETWORK_PROFILE`, `CLAUDE_CONTAINER_NETWORK_POLICY`, `CLAUDE_CONTAINER_NETWORK_RUNTIME_DIR` and `CLAUDE_CONTAINER_EGRESS_IMAGE` is missing, it SHALL exit with status 1 and an English stderr message directing the user to invoke the wrapper with `--container-setup`. That refusal SHALL precede engine queries, state creation and image or resource operations. It SHALL NOT prompt, run setup or launch an application. With all four settings present, the default provider launch SHALL apply every provider check, as an explicit one does.

#### Scenario: First ordinary invocation
- **WHEN** the wrapper is invoked without an effective network mode and without provider settings, interactively or with redirected input
- **THEN** it returns status 1 with the setup-required stderr message and no application stdout
- **AND** it creates no state or runtime resources and performs no engine or image operation

#### Scenario: Build and shell options cannot supply configuration
- **WHEN** an unconfigured ordinary invocation uses shell, build or worktree options, including combinations with `CLAUDE_CONTAINER_MAINTENANCE=1`
- **THEN** it receives the same setup-required refusal before state creation or engine operations
- **AND** maintenance consent does not select a runtime mode

#### Scenario: Other environment settings do not imply setup
- **WHEN** an ordinary invocation without a nonempty network mode supplies state, image, endpoint or authority settings, or only some of the four provider settings
- **THEN** it receives setup guidance before runtime validation of those settings
- **AND** configuration or report files present in the current directory do not admit the launch

#### Scenario: Default provider launch with saved settings
- **WHEN** the network mode is unset and the four provider settings are present
- **THEN** the wrapper runs a provider session with every provider, protected-installation and qualification check

#### Scenario: Dedicated entry points remain reachable
- **WHEN** help, interactive setup or the standalone qualification operation is requested without a network mode
- **THEN** that entry point keeps its own argument, terminal, prerequisite and enforcement checks without ordinary missing-setup admission
- **AND** help still takes precedence and qualification still cannot execute a supplied application command

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
- the set of agent and proxy budgets actually enforced, as determined by the controllers the engine delegates;
- the mechanism enforcing each agent and proxy process budget: cgroup controller, process rlimit, or none;
- the session lifetime setting.

A launch whose effective settings differ from the qualified identity SHALL stop with requalification guidance.

#### Scenario: Budget changed after qualification
- **WHEN** a restricted installation was qualified with default budgets and the operator launches with `CLAUDE_CONTAINER_PIDS_LIMIT=1024`
- **THEN** the qualification check reports mismatched evidence and the application does not start

#### Scenario: Qualification with matching settings
- **WHEN** the operator qualifies and launches with the same budgets and lifetime
- **THEN** the qualification check accepts the report

#### Scenario: Controller delegation changed after qualification
- **WHEN** an installation was qualified while `cpu` was not delegated and the engine later delegates `cpu`
- **THEN** the qualification check reports mismatched evidence and requires requalification

#### Scenario: Process budget mechanism changed after qualification
- **WHEN** an installation was qualified with the agent process budget on the process rlimit fallback and the engine later delegates `pids`
- **THEN** the qualification check reports mismatched evidence and requires requalification

### Requirement: Hardening controls are documented
Wrapper help and the README SHALL document:
- the budget variables, their defaults and accepted formats;
- the process rlimit fallback, its per-session scope, the condition under which it applies, and that memory and CPU have no fallback;
- the lifetime variable;
- the unsafe-workspace override and the refused directories;
- that capabilities are dropped in every mode.

Help SHALL remain side effect free.

#### Scenario: Operator reads wrapper help
- **WHEN** the operator runs `--container-help`
- **THEN** the output lists `CLAUDE_CONTAINER_MEMORY_LIMIT`, `CLAUDE_CONTAINER_CPU_LIMIT`, `CLAUDE_CONTAINER_PIDS_LIMIT`, `CLAUDE_CONTAINER_RUN_TIMEOUT` and `CLAUDE_CONTAINER_ALLOW_UNSAFE_WORKSPACE` with their defaults
- **AND** no engine query or state creation occurs

#### Scenario: Operator reads about the process rlimit fallback
- **WHEN** the operator reads the README or wrapper help
- **THEN** it states that, without the `pids` controller, the process budget is enforced through the process rlimit per session when the host counts it per container
- **AND** it states that the usable process count is slightly below the budget because of container startup tasks

### Requirement: Unenforced budgets are announced
Each launch, setup plan and setup smoke SHALL print one notice per unenforced budget, naming the budget, its container (agent or proxy) and the reason: the missing cgroup controller, or a cgroup manager that applies no cgroup limits. A process budget enforced through the process rlimit fallback SHALL get one notice naming the budget, its container and the rlimit mechanism instead. They SHALL NOT ask for confirmation. When every budget is enforced by its cgroup controller, no notice SHALL be printed.

#### Scenario: CPU controller missing
- **WHEN** a session starts on an engine delegating only `memory` and `pids`
- **THEN** stderr shows a notice that the agent CPU budget is not enforced because the `cpu` controller is not delegated to the rootless engine
- **AND** the session starts without waiting for input

#### Scenario: All controllers delegated
- **WHEN** the engine delegates `cpu`, `memory` and `pids`
- **THEN** no budget notice is printed

#### Scenario: Engine with the cgroupfs manager
- **WHEN** a session starts on a rootless engine with the `cgroupfs` cgroup manager that reports `cpu`, `memory` and `pids`
- **THEN** stderr shows notices that the agent memory and CPU budgets are not enforced because the rootless engine uses the `cgroupfs` cgroup manager, which applies no cgroup limits
- **AND** the process budget notice names the process rlimit fallback, or the reason it was not applied

#### Scenario: Process budget on the rlimit fallback
- **WHEN** a session starts on an engine delegating `cpu` and `memory` but not `pids`, on a host that counts the process rlimit per container
- **THEN** stderr shows a notice that the agent process budget is enforced through the process rlimit because the `pids` controller is not delegated
- **AND** the notice states that the limit counts the session user's tasks, threads included
- **AND** no notice reports the agent process budget as unenforced

#### Scenario: Process rlimit fallback not applied
- **WHEN** a session starts without the `pids` controller on a host where per-container counting is not established
- **THEN** stderr shows a notice that the agent process budget is not enforced, naming the missing `pids` controller and why the rlimit fallback was not applied

### Requirement: Signals reach the session once
The attached engine client SHALL NOT proxy signals to the container. The wrapper's own shutdown SHALL be the only path that forwards INT, TERM and HUP, so the application receives one signal per event, and the bounded-shutdown contract applies.

#### Scenario: Process-group signal without a terminal
- **WHEN** a TERM is sent to the wrapper's process group during a session without a TTY
- **THEN** the application receives TERM once, and the wrapper returns 143 after cleanup

#### Scenario: Attach options
- **WHEN** the wrapper starts and attaches to its container
- **THEN** the attach command disables signal proxying

### Requirement: Extra variables forwarded by name
`CLAUDE_CONTAINER_ENV_VARS` SHALL list host variable names, separated by whitespace, to forward into the session by name, never by value. An invalid name SHALL stop the launch before any engine or state operation. Unset or empty variables SHALL NOT be forwarded. Reserved names SHALL be skipped with one notice each.

#### Scenario: Listed variable reaches the session
- **WHEN** `CLAUDE_CONTAINER_ENV_VARS="GH_TOKEN"` is set and `GH_TOKEN` has a value
- **THEN** the session receives `GH_TOKEN` by name and the value is absent from engine arguments

#### Scenario: Names reserved by mode
- **WHEN** the list names a variable the launcher or agent part sets, a proxy, CA or provider-only setting in a restricted mode, or `ANTHROPIC_API_KEY` in a provider session using the `anthropic-account` profile
- **THEN** that name is skipped with a notice

#### Scenario: Reserved or invalid name
- **WHEN** the list names `HOME`, or names `HTTPS_PROXY` in offline mode
- **THEN** that name is skipped with a notice and the session starts
- **AND** a name such as `1BAD` stops the launch before any engine query

### Requirement: First-user setup guidance
README, wrapper help and setup guidance SHALL identify `--container-setup` as the first step for new users. They SHALL explain:
- the managed launch;
- that `provider` is the default mode;
- the explicit operator alternative;
- that offline sessions cannot reach the Claude API.

Network documentation SHALL describe the default-mode admission consistently.

#### Scenario: User follows first-run guidance
- **WHEN** a new user reads help or the README
- **THEN** instructions show how to invoke setup and then use its managed launcher
- **AND** explain that an offline session cannot reach the Claude API and no unrestricted fallback is automatic

#### Scenario: Operator invokes the wrapper directly
- **WHEN** an operator reads the guidance for direct invocation
- **THEN** it gives explicit mode examples, including separately authorized maintenance, without implying that mode selection proves restricted readiness
