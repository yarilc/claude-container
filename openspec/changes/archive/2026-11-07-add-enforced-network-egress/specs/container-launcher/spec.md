# Spec Delta

## MODIFIED Requirements

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
- **WHEN** the session runs on Linux 6.6.87.2-microsoft-standard-WSL2 x86_64 with usable Landlock ABI 3 and standard OCI policy
- **THEN** bootstrap preparation supports that ABI without requiring a kernel upgrade or ABI-9 features
- **AND** both required enforcement layers must install before application initialization

#### Scenario: Guarded pipeline and terminal
- **WHEN** a supported restricted session receives piped input or an interactive terminal
- **THEN** the bootstrap and relay preserve empty/spaced arguments and input/terminal behavior
- **AND** bootstrap diagnostics do not contaminate application stdout


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
