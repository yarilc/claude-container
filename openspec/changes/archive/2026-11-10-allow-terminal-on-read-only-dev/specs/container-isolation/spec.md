## MODIFIED Requirements

### Requirement: Ephemeral constrained temporary storage
Sessions SHALL explicitly provide ephemeral `/tmp`, `/run`, and `/var/tmp` mounts with `rw,nosuid,nodev,noexec`. Limits SHALL be 256 MiB for `/tmp`, 16 MiB for `/run`, and 256 MiB for `/var/tmp`. `/tmp` and `/var/tmp` SHALL permit caller writes with sticky directory mode `1777`. Temporary contents SHALL disappear after container removal. Internal sandbox compatibility SHALL NOT silently relax these options.

#### Scenario: Temporary file lifecycle
- **WHEN** a session writes temporary files in `/tmp` and `/var/tmp` and a new container starts after its removal
- **THEN** both paths accept caller writes but the previous files are absent
- **AND** all three temporary mounts retain `nosuid,nodev,noexec` and their specified limits

#### Scenario: Temporary mounts are explicit
- **WHEN** a Claude or shell session is created in shared or isolated state mode
- **THEN** `/tmp`, `/run`, `/var/tmp`, `/dev`, `/dev/pts` and `/dev/shm` are explicitly provisioned
- **AND** no writable `/var/log` tmpfs or writable `/dev/shm` is introduced by automatic read-only provisioning

#### Scenario: Execution restrictions apply to both temporary directories
- **WHEN** a session attempts to execute a copied executable directly from `/tmp` or `/var/tmp`
- **THEN** the mount policy prevents direct execution from either directory
- **AND** ordinary temporary file writes remain possible

## ADDED Requirements

### Requirement: Terminal-compatible device mounts
Sessions SHALL provide their own `/dev` tmpfs with `nosuid,noexec`, mode `755` and a 64 MiB limit, an explicit `devpts` at `/dev/pts`, and an empty read-only tmpfs at `/dev/shm`, so that a terminal can be attached when the engine would otherwise mount `/dev` read-only. Automatic read-only tmpfs provisioning SHALL NOT add any writable path beyond the explicit temporary and device mounts.

#### Scenario: Terminal attaches on an engine that mounts /dev read-only
- **WHEN** an interactive session starts with a terminal on Podman 5 with crun 1.27, where `--read-only-tmpfs=false` makes `/dev` read-only
- **THEN** the terminal attaches and the agent starts without any host configuration change
- **AND** `/dev` is not executable, `/dev/pts` is present, and `/dev/shm` is read-only and empty

#### Scenario: Executables cannot run from /dev
- **WHEN** a session copies an executable into `/dev` where the engine leaves it writable
- **THEN** the mount policy prevents its direct execution
