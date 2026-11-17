# Spec Delta

## MODIFIED Requirements

### Requirement: Ephemeral constrained temporary storage
Sessions SHALL explicitly provide ephemeral `/tmp`, `/run`, `/var/tmp` mounts and, in shared-state mode, an ephemeral home mount, all with `rw,nosuid,nodev,noexec`. Limits SHALL be:
- 512 MiB for `/tmp`;
- 32 MiB for `/run`;
- 512 MiB for `/var/tmp`;
- 512 MiB for the ephemeral home.

`/tmp`, `/var/tmp` and the ephemeral home SHALL permit caller writes with sticky directory mode `1777`. The Claude profile SHALL NOT declare executable temporary storage (`native.exec_tmp`). Temporary contents SHALL disappear after container removal. Internal sandbox compatibility SHALL NOT silently relax these options.

#### Scenario: Temporary file lifecycle
- **WHEN** a session writes temporary files in `/tmp` and `/var/tmp` and a new container starts after its removal
- **THEN** both paths accept caller writes but the previous files are absent
- **AND** all three temporary mounts retain `nosuid,nodev,noexec` and their specified limits

#### Scenario: Temporary mounts are explicit
- **WHEN** a Claude or shell session is created in shared or isolated state mode
- **THEN** `/tmp`, `/run`, `/var/tmp` and `/dev/shm` are explicitly provisioned, and `/dev` with its `devpts` is left to the engine
- **AND** no writable `/var/log` tmpfs or writable `/dev/shm` is introduced by automatic read-only provisioning

#### Scenario: Execution restrictions apply to both temporary directories
- **WHEN** a session attempts to execute a copied executable directly from `/tmp` or `/var/tmp`
- **THEN** the mount policy prevents direct execution from either directory
- **AND** ordinary temporary file writes remain possible

### Requirement: Independent approvals and delegation
`CLAUDE_YOLO` SHALL control only the `--dangerously-skip-permissions` argument that Claude's approval-bypass hook adds in Claude mode. It SHALL accept the shared boolean forms case-insensitively and reject invalid values before image operations. Shell mode SHALL NOT receive the flag.

Socket access SHALL require exact `CLAUDE_CONTAINER_PODMAN=1` and explicit unrestricted network mode, independently of YOLO and state mode. Restricted modes, including the default provider mode, SHALL reject exact socket opt-in.

Shell, YOLO, and native permission settings SHALL NOT weaken the outer network boundary. Disabling YOLO SHALL NOT override native CLI arguments or saved permission settings.

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
