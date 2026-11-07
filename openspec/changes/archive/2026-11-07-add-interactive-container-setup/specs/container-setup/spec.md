# Spec Delta

## Purpose

Provide an interactive, repeatable host-side procedure that prepares a usable sandbox, persists non-secret working preferences and reports remaining prerequisites honestly.

## ADDED Requirements

### Requirement: Dedicated interactive setup invocation
`--container-setup` SHALL run a dedicated setup operation before normal runtime preflight. It SHALL require an interactive terminal, reject combinations with launch options or Claude arguments, and never start an ordinary Claude session implicitly. Wrapper help SHALL remain side effect free and describe setup.

#### Scenario: Setup before runtime configuration exists
- **WHEN** an interactive user requests setup with missing provider settings or an absent image
- **THEN** the questionnaire and prerequisite diagnosis run without requiring those settings first
- **AND** setup is not forwarded to Claude

#### Scenario: Unattended or ambiguous invocation
- **WHEN** setup has no interactive terminal or is combined with shell, build, worktree or Claude arguments
- **THEN** it fails with usage guidance before mutations or image operations

#### Scenario: Help takes precedence
- **WHEN** wrapper help is requested together with setup and invalid configuration
- **THEN** help succeeds without loading managed preferences, prompting or requiring Podman

### Requirement: Workflow questionnaire with explicit defaults
Setup SHALL explain and collect network mode, provider authentication method when relevant, state sharing, installation paths, host CA trust, permission bypass and workspace scope. First-run defaults SHALL select provider networking, account authentication, shared state and disabled optional authority. Existing saved choices SHALL be offered for review on rerun.

#### Scenario: First setup choices
- **WHEN** the user reviews first-run defaults
- **THEN** network options distinguish offline, provider-restricted and unrestricted use, and provider questions distinguish account from API authentication
- **AND** accepting the first-run network/authentication defaults selects provider/account without requiring an API key
- **AND** shared host credentials, isolated fresh state, worktree-parent exposure and permission bypass are explained before selection

#### Scenario: Provider selected
- **WHEN** the user chooses provider mode and account authentication without an API key
- **THEN** setup selects the protected account policy profile without requiring an API key
- **AND** API authentication instead selects the separate API profile

#### Scenario: Previously saved network mode
- **WHEN** setup is rerun with a saved configuration, including explicit offline mode
- **THEN** the saved network mode remains the proposed choice instead of the first-run provider default

### Requirement: Optional authority requires deliberate selection
Setup SHALL explain and require explicit selection of unrestricted networking, Podman delegation, permission bypass, worktree-parent exposure and host CA trust. Delegation SHALL be available only with unrestricted networking. Enabling the host launch service SHALL NOT implicitly grant its socket to the application.

#### Scenario: Restricted networking and delegation conflict
- **WHEN** the user requests delegation while choosing offline or provider mode
- **THEN** setup explains the conflict and requires an explicit compatible choice before proceeding
- **AND** it never silently broadens networking

#### Scenario: Launch service without delegation
- **WHEN** setup enables the API service for restricted launch
- **THEN** the saved application delegation setting remains disabled unless separately selected in unrestricted mode

### Requirement: Installed host prerequisites only
Setup SHALL check that Podman is installed and the chosen engine supports Linux rootless operation. It SHALL diagnose missing user-session, rootless, native-storage and selected-mode dependencies with actionable guidance. It SHALL NOT install host packages, invoke privilege escalation, edit subordinate ID ranges, enable lingering or modify system-wide WSL configuration.

#### Scenario: Podman missing or rootless unavailable
- **WHEN** Podman is absent or the engine cannot operate rootlessly
- **THEN** setup stops before image operations and reports the prerequisite and next action
- **AND** no package manager, sudo command or rootful fallback runs

#### Scenario: Unsupported restricted platform
- **WHEN** the selected restricted mode fails the existing platform or enforcement prerequisites
- **THEN** setup reports that mode as unavailable and does not publish a ready configuration or select unrestricted mode automatically

### Requirement: User-scoped Podman service preparation
When the selected workflow needs a same-host Unix Podman service, setup SHALL reuse a verified endpoint or offer to enable and start `podman.socket` through a working systemd user session. Service changes SHALL require confirmation. The resulting endpoint SHALL pass existing rootless verification before image operations or container creation.

#### Scenario: User socket activation accepted
- **WHEN** a service is required, the systemd user manager is usable and the user confirms enablement
- **THEN** setup enables and starts the user socket and verifies the exact selected Unix endpoint
- **AND** it reports the persistent user-service change

#### Scenario: Existing explicit service
- **WHEN** the user selects an existing same-host Unix endpoint
- **THEN** setup validates and uses that endpoint without replacing it or enabling an unrelated socket
- **AND** unsupported remote or named contexts remain rejected

#### Scenario: No working systemd user session
- **WHEN** a needed service is unavailable and user socket activation is unavailable or declined
- **THEN** setup prints the applicable foreground-service and runtime-directory instructions and reports incomplete setup until an endpoint is verified
- **AND** it does not start an unmanaged background daemon or change the host init system

### Requirement: Reviewed setup mutations and maintenance
Setup SHALL show selected settings, paths, service changes and required image acquisition/builds before applying them. It SHALL obtain explicit consent for mutations and maintenance, explaining that host pulls and build steps are outside runtime network filtering. Maintenance authorization SHALL be limited to approved setup operations and never persisted as a launch default.

#### Scenario: Review declined
- **WHEN** the user declines the proposed filesystem/image changes before preparation
- **THEN** no installation is activated and no image pull or build occurs
- **AND** any previously approved service change is reported separately

#### Scenario: Approved build
- **WHEN** the user approves preparation requiring image builds
- **THEN** only the approved maintenance operations receive exact maintenance authorization
- **AND** ordinary subsequent launches still require separate authorization for missing-image builds or refreshes

### Requirement: Protected complete installation
Setup SHALL prepare all files needed for the selected workflow in a native installation outside writable workspace, worktree-parent and state trees. It SHALL validate ownership, ancestor permissions and overlaps, create missing private directories, and refuse unsafe existing paths without recursive permission repair, credential imports, relabeling or added privileges.

#### Scenario: Checkout on a Windows mount
- **WHEN** setup runs from a checkout on a permission-emulating Windows filesystem and the user selects a valid native installation
- **THEN** it copies the required installation inputs to native storage and validates them there
- **AND** it does not require executing a compiled guard on the source mount

#### Scenario: Unsafe installation or state path
- **WHEN** a chosen path has unsafe ancestors, cannot enforce private permissions or overlaps an application-writable mount
- **THEN** setup identifies the path and fails without modifying existing permissions or claiming completion

### Requirement: Mode-specific image and guard preparation
Setup SHALL inspect or prepare the runtime image and the additional components required by the selected mode. Restricted modes SHALL receive a validated static guard and digest manifest; provider mode SHALL also receive a valid selected policy, private runtime directory and immutable proxy image identity. Existing suitable artifacts SHALL be reused unless refresh is approved.

#### Scenario: Fresh provider setup
- **WHEN** provider setup is approved with no prepared artifacts
- **THEN** setup prepares the pinned build inputs, toolchain, runtime and proxy images, compiles the guard and validates its manifest and policy
- **AND** launch preferences refer to an inspected immutable proxy image rather than an unresolved local tag

#### Scenario: Offline or unrestricted setup
- **WHEN** setup prepares offline mode
- **THEN** it prepares the runtime and guard without requiring a provider proxy image or authentication
- **AND** unrestricted setup requires neither the restricted guard nor provider proxy components

#### Scenario: Preparation fails
- **WHEN** an image build, image inspection, guard compilation or validation fails
- **THEN** setup reports the failed stage and leaves the last working installation selected
- **AND** it does not substitute a different policy, toolchain or network mode

### Requirement: Persistent non-secret managed launch preferences
Setup SHALL save versioned non-secret preferences and provide a managed launcher usable from another workspace without repeated exports. Preferences and launcher code SHALL remain outside application-writable mounts and be validated before use. The launcher SHALL preserve arguments, stdin, terminal handling and current-directory semantics. Direct wrapper invocation SHALL retain its existing environment-based behavior.

#### Scenario: New terminal and workspace
- **WHEN** the user invokes the managed launcher in a new terminal from a separate workspace
- **THEN** the saved network, profile, state, service, CA and approval choices apply without modifying shell startup files
- **AND** the current directory determines the mounted workspace and container working directory

#### Scenario: Explicit environment overrides
- **WHEN** a supported runtime variable is explicitly present in the launch environment
- **THEN** its value, including an empty value, takes precedence over the saved default
- **AND** the effective configuration still passes existing conflict, privacy and enforcement checks

#### Scenario: Unsafe or malformed preferences
- **WHEN** managed preferences are untrusted, invalid or use an unsupported schema
- **THEN** the launcher fails before image operations or container creation without evaluating their contents as shell code

#### Scenario: Invoked dispatcher or alias is writable
- **WHEN** an invocation uses a dispatcher copy or a symlink chain with any entry inside a writable workspace or state mount
- **THEN** launch fails before application execution even if the configured command and final symlink target are protected
- **AND** relative paths and dot-dot components are interpreted with filesystem symlink semantics

#### Scenario: Legacy managed dispatcher needs migration
- **WHEN** an old managed dispatcher cannot identify its actual invocation path to the installed helper
- **THEN** normal launch fails with setup guidance while help and setup remain available
- **AND** setup atomically upgrades the recognized dispatcher without overwriting unrelated command files

### Requirement: Credential-preserving authentication assistance
Setup SHALL support reusing selected shared account state or offering an explicit fresh login in isolated state. It SHALL NOT copy credentials, collect or persist API keys/tokens in setup preferences, or require an API key for account use. Authentication SHALL use the chosen installed sandbox and preserve its selected network and CA policies.

#### Scenario: Fresh account login
- **WHEN** an account user chooses fresh isolated state and accepts login after sandbox validation
- **THEN** setup invokes Claude's account login through the configured sandbox and lets Claude persist credentials in that state
- **AND** setup records no token, authorization code or credential-bearing login URL

#### Scenario: API key unavailable
- **WHEN** API mode is selected but no API key is available
- **THEN** sandbox preparation can complete with authentication explicitly pending and instructions for supplying the key through the existing runtime mechanism
- **AND** no paid model request is made automatically

### Requirement: Verified readiness with separate authentication status
Setup SHALL declare the selected sandbox ready only after installed-path checks, engine verification, artifact validation and a smoke launch succeed through the actual selected runtime path. Restricted smoke checks SHALL exercise real guard enforcement. Completion output SHALL separately report authentication as verified, pending or not applicable, provide the launch/rerun commands and identify PATH requirements.

#### Scenario: Sandbox smoke check succeeds
- **WHEN** the selected installation passes its smoke check
- **THEN** setup reports sandbox readiness and the resolved managed launch command
- **AND** a version or shell smoke check alone does not imply authenticated provider success

#### Scenario: Login or optional authentication check skipped
- **WHEN** the sandbox is usable but authentication was skipped, unavailable or failed
- **THEN** setup reports sandbox ready and authentication pending with the appropriate next command
- **AND** it does not claim a working authenticated model request

#### Scenario: Enforcement check fails
- **WHEN** the restricted smoke launch cannot install required enforcement
- **THEN** setup reports incomplete setup, returns nonzero and does not activate the candidate installation

### Requirement: Repeatable setup with owned recovery
Rerunning setup SHALL review saved choices and reuse valid artifacts. Activation SHALL preserve the previous working installation until the candidate passes validation. Cancellation, interruption or failure SHALL remove only setup-owned temporary resources, preserve credentials and unrelated containers, and report persistent changes already made. Concurrent setup runs SHALL NOT overwrite each other's activation.

#### Scenario: Rerun or interrupted update
- **WHEN** setup is rerun unchanged or interrupted while preparing an update
- **THEN** unchanged suitable artifacts need no rebuild and the last activated launcher remains usable
- **AND** any created images or enabled user socket remaining after interruption are reported without deleting shared resources

#### Scenario: Competing activation
- **WHEN** another setup already holds the target installation's update lock
- **THEN** setup exits with an actionable busy message without modifying that installation

#### Scenario: Unrelated launcher exists
- **WHEN** the desired command path contains a file not owned by this setup
- **THEN** setup offers a different path or stops without overwriting that file

#### Scenario: Managed command path changes
- **WHEN** a validated candidate chooses a different physical command entry
- **THEN** activation retires the previous owned command only after publishing the new command
- **AND** retirement or publication failure restores the previous activation and command
- **AND** two path spellings of the same physical entry do not cause its removal

#### Scenario: Group leader exits before timeout cleanup
- **WHEN** a setup-owned process group has surviving descendants after its leader exits or its captured pipes close
- **THEN** timeout or interruption cleanup terminates the remaining owned group within bounded teardown time
- **AND** the primary timeout/interruption remains the reported outcome
