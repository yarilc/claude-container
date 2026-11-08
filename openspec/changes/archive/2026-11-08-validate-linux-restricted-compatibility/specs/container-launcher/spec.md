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
- **WHEN** the session runs on the measured WSL x86_64 target or a locally qualified native Linux/WSL2 x86_64 installation with usable Landlock ABI >= 3 and standard OCI policy
- **THEN** bootstrap preparation supports that ABI without requiring a kernel upgrade or ABI-9 features
- **AND** both required enforcement layers must install before application initialization

#### Scenario: Guarded pipeline and terminal
- **WHEN** a supported restricted session receives piped input or an interactive terminal
- **THEN** the bootstrap and relay preserve empty/spaced arguments and input/terminal behavior
- **AND** bootstrap diagnostics do not contaminate application stdout

## ADDED Requirements

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
