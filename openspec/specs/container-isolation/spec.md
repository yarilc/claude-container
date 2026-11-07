# container-isolation Specification

## Purpose

Define the outer container's filesystem and authority boundaries and require evidence that distinguishes container isolation from native agent approvals and internal sandbox execution.

## Requirements

### Requirement: Read-only system and caller identity
Sessions SHALL use a read-only container root, `--userns=keep-id`, and the caller's UID/GID. Writable persistent binds SHALL be limited to the selected workspace and state mode, plus the delegated socket when enabled. The host CA exception SHALL remain a read-only single-file mount governed by `host-ca-trust`.

#### Scenario: Ordinary session boundaries
- **WHEN** a session writes to its workspace and attempts to change `/usr`
- **THEN** workspace files belong to the caller and the system write fails
- **AND** a host sentinel outside all selected mounts is inaccessible when socket delegation is disabled

#### Scenario: Worktree expansion
- **WHEN** `--container-git-worktree` selects the immediate physical parent
- **THEN** the entire selected parent is writable as specified by `workspace-mounts`, with no additional inferred Git mounts

### Requirement: Ephemeral constrained temporary storage
Sessions SHALL disable automatic read-only tmpfs provisioning and explicitly provide ephemeral `/tmp`, `/run`, and `/var/tmp` mounts with `rw,nosuid,nodev,noexec`. Limits SHALL be 256 MiB for `/tmp`, 16 MiB for `/run`, and 256 MiB for `/var/tmp`. `/tmp` and `/var/tmp` SHALL permit caller writes with sticky directory mode `1777`. Temporary contents SHALL disappear after container removal. Internal sandbox compatibility SHALL NOT silently relax these options.

#### Scenario: Temporary file lifecycle
- **WHEN** a session writes temporary files in `/tmp` and `/var/tmp` and a new container starts after its removal
- **THEN** both paths accept caller writes but the previous files are absent
- **AND** all three temporary mounts retain `nosuid,nodev,noexec` and their specified limits

#### Scenario: Temporary mounts are explicit
- **WHEN** a Claude or shell session is created in shared or isolated state mode
- **THEN** automatic read-only tmpfs provisioning is disabled and `/tmp`, `/run`, and `/var/tmp` are explicitly provisioned
- **AND** no writable `/var/log` tmpfs is introduced by automatic read-only provisioning

#### Scenario: Execution restrictions apply to both temporary directories
- **WHEN** a session attempts to execute a copied executable directly from `/tmp` or `/var/tmp`
- **THEN** the mount policy prevents direct execution from either directory
- **AND** ordinary temporary file writes remain possible

### Requirement: Standard runtime security policy
The wrapper SHALL NOT add privileged execution, extra capabilities, replacement or weakened OCI seccomp profiles, disabled SELinux labels, or automatic host bind relabeling. Restricted sessions SHALL additionally apply unprivileged Landlock filesystem confinement and an additional restrictive in-process seccomp filter through a protected bootstrap while preserving those standard runtime policies. Policy failures SHALL remain visible with actionable guidance rather than triggering an automatic security-policy bypass.

#### Scenario: SELinux denial
- **WHEN** host policy denies a workspace, state, or socket bind
- **THEN** startup reports the engine failure without adding relabel options or disabling labels

#### Scenario: Internal sandbox denied by policy
- **WHEN** Claude's internal sandbox cannot execute under the standard container policy
- **THEN** the failure is recorded without automatically broadening container privileges or weakening either seccomp layer or tmpfs policy

#### Scenario: Required enforcement is unavailable under the standard policy
- **WHEN** the kernel lacks the required ABI-3 filesystem features or the existing seccomp/SELinux policy blocks either enforcement layer
- **THEN** restricted startup fails before agent-controlled code executes
- **AND** no replacement seccomp profile, disabled label, added privilege, or automatic host policy change is used to make it work

#### Scenario: Confinement persists across execution modes
- **WHEN** a restricted session starts Bash, Claude, a native permission-bypass mode, or descendant tools
- **THEN** inherited Landlock and additive seccomp restrictions cover them before their initialization
- **AND** live writable workspace/state binds grant ordinary file access without granting external Unix services or new Unix listeners or unconnected Unix sockets

### Requirement: Independent approvals and delegation
`CLAUDE_YOLO` SHALL control only wrapper injection of `--dangerously-skip-permissions` in Claude mode. It SHALL accept existing boolean forms case-insensitively and reject invalid values before image operations. Socket access SHALL require exact `CLAUDE_CONTAINER_PODMAN=1` and explicit unrestricted network mode, independently of YOLO and state mode. Restricted modes SHALL reject exact socket opt-in. Shell, YOLO, and native permission settings SHALL NOT weaken the outer network boundary. Disabling YOLO SHALL NOT override native CLI arguments or saved permission settings.

#### Scenario: Four combinations in either state mode
- **WHEN** unrestricted runtime mode is selected and all enabled/disabled combinations of YOLO and Podman delegation are used in shared and isolated modes
- **THEN** only YOLO determines flag injection and only exact Podman opt-in determines delegation mounts and variables

#### Scenario: Native permissions explicitly supplied
- **WHEN** YOLO is disabled but a native permission flag is passed directly to Claude
- **THEN** the wrapper forwards that argument without claiming to enforce native approvals

#### Scenario: Approvals cannot change egress
- **WHEN** an offline or provider session uses shell mode, YOLO, or a native permission-bypass setting
- **THEN** its selected network restriction still applies
- **AND** exact socket opt-in rejects startup in either state mode

### Requirement: Evidence-based isolation documentation
Documentation SHALL distinguish approvals, internal sandboxing, filesystem isolation, network egress enforcement, and socket authority. A validation record SHALL identify environment and versions and label checks as passed, failed, or unavailable. A sandboxed tool operation and its expected output SHALL be verified before claiming internal sandbox compatibility; executable availability or CLI exit status alone SHALL NOT establish it.

#### Scenario: Synthetic runtime checks
- **WHEN** automated boundary checks run
- **THEN** they use synthetic state without real credentials or paid model requests and check external sentinels, ownership, state persistence, and temporary storage

#### Scenario: Sandbox operation unavailable or unsuccessful
- **WHEN** an authenticated sandbox check cannot run or fails to produce the expected result
- **THEN** the validation record reports unavailable or failed rather than passed, even if `bwrap` probes succeed or the CLI exits zero

#### Scenario: User reviews access boundaries
- **WHEN** the user reads the README
- **THEN** it explains shared-state write access, parent/worktree expansion, and socket-enabled host mounts beyond the workspace and identifies offline/provider enforcement, explicit unrestricted networking, and the limits of destination filtering
