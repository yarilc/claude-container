# Spec Delta

## ADDED Requirements

### Requirement: Read-only state
`CLAUDE_CONTAINER_READONLY_STATE`, a boolean (`1`, `true`, `yes`; empty, `0`, `false`, `no`), SHALL mount the Claude configuration directory and every shared directory read-only below the ephemeral home. They are taken from shared state or from the isolated home. Those directories SHALL already exist. The launcher SHALL NOT create them, SHALL NOT check their owner or privacy, and SHALL NOT pass them to restricted preparation as writable. The isolated home itself SHALL NOT be mounted.

#### Scenario: Read-only shared state
- **WHEN** `CLAUDE_CONTAINER_READONLY_STATE=1` is set and `~/.claude` and `~/.config/openspec` exist
- **THEN** the session sees them read-only and writes there fail

#### Scenario: Missing state
- **WHEN** read-only state is selected and a configuration directory does not exist
- **THEN** the launch stops before the engine and names the missing directory

## MODIFIED Requirements

### Requirement: Compatible shared state by default
With `CLAUDE_CONTAINER_STATE_DIR` unset or empty, the wrapper SHALL mount, read/write, below a 512 MiB ephemeral tmpfs home:
- `${CLAUDE_CONFIG_DIR:-$HOME/.claude}` at `/claude-home/.claude`;
- host `$HOME/.config/openspec` at `/claude-home/.config/openspec`.

Other home content SHALL disappear with the session. The wrapper SHALL NOT create unused host cache or share directories.

#### Scenario: Existing default profile
- **WHEN** no state or Claude configuration override is selected
- **THEN** the existing host `~/.claude` and OpenSpec configuration remain the shared persistent sources

#### Scenario: Custom shared Claude directory
- **WHEN** `CLAUDE_CONFIG_DIR` names a custom directory and isolated state is not selected
- **THEN** that directory supplies Claude state and shared host OpenSpec configuration remains mounted

#### Scenario: Ephemeral home content
- **WHEN** a shared-state session writes a file directly in `/claude-home`
- **THEN** the write succeeds and the file is absent in the next session

### Requirement: Resolved state paths and isolation scope
The wrapper SHALL resolve selected state sources to physical absolute paths. `CLAUDE_CONTAINER_STATE_DIR` and `CLAUDE_CONFIG_DIR` SHALL be absolute and free of colon, CR and LF, checked before any engine operation. In isolated mode, every configuration child and the CA mount parent SHALL resolve within that home and be private. Escaping configuration symlinks SHALL fail. Documentation SHALL distinguish application-state isolation from access granted independently by workspace mounts or socket delegation.

#### Scenario: Top-level state alias
- **WHEN** the selected state path is a symlink to an accessible private directory
- **THEN** its resolved physical path is used as the bind source

#### Scenario: Isolated configuration escapes home
- **WHEN** `.claude` or `.config/openspec` resolves outside the selected isolated home through a symlink
- **THEN** startup fails with a path-specific isolation error

#### Scenario: Unusable state path
- **WHEN** `CLAUDE_CONTAINER_STATE_DIR` or `CLAUDE_CONFIG_DIR` is relative or contains a colon
- **THEN** startup fails before any engine query

#### Scenario: Shared isolated child
- **WHEN** an existing `.config/openspec` inside the isolated home is readable by group or others
- **THEN** startup fails naming the directory
