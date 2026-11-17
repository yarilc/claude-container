# Spec Delta

## ADDED Requirements

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

## REMOVED Requirements

### Requirement: First-user setup and migration guidance
**Reason**: The project has no release, so the history of the missing-mode behavior before and after `c777b73` is not guidance any user needs, and the missing mode now selects provider.
**Migration**: Replaced by "First-user setup guidance".

## MODIFIED Requirements

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
