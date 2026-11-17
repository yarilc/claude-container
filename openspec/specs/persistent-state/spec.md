# persistent-state Specification

## Purpose

Preserve compatible shared Claude state while offering explicit application-home isolation and enforcing private credential directory ownership and permissions.

## Requirements

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

### Requirement: Explicit isolated application home
A nonempty `CLAUDE_CONTAINER_STATE_DIR` SHALL select a dedicated writable home at `/claude-home`, containing Claude state, OpenSpec configuration, caches, and other home data. The wrapper SHALL NOT add shared host Claude or OpenSpec configuration mounts in this mode. A simultaneous nonempty host `CLAUDE_CONFIG_DIR` SHALL fail with an actionable conflict error before image operations or launch.

#### Scenario: Fresh isolated profile
- **WHEN** a dedicated state directory is selected and host `CLAUDE_CONFIG_DIR` is unset or empty
- **THEN** the container uses `HOME=/claude-home` and `CLAUDE_CONFIG_DIR=/claude-home/.claude` with configuration persisted under the selected directory
- **AND** the wrapper adds no shared host configuration mounts or automatic imports

#### Scenario: Conflicting profile controls
- **WHEN** dedicated state and a nonempty host `CLAUDE_CONFIG_DIR` are both selected
- **THEN** startup fails before image operations with instructions to select one state mode

### Requirement: Private credential directories
The wrapper SHALL create selected state directories with user-only permissions and verify caller ownership and read/write/search access. It SHALL reject group/other access on the shared Claude directory or isolated home and its existing `.claude` directory. Errors SHALL identify the path and suggest explicit repair or permission-enforcing storage; existing permissions SHALL NOT be repaired recursively.

#### Scenario: Private state created
- **WHEN** a selected credential directory is absent on a filesystem supporting Unix permissions
- **THEN** it is created privately and verified before container creation

#### Scenario: Unsafe existing directory
- **WHEN** a credential directory has the wrong owner, lacks required access, or grants group/other access
- **THEN** startup fails with a path-specific error without launching a container or recursively changing existing permissions

#### Scenario: Filesystem ignores permissions
- **WHEN** the state filesystem cannot enforce user-only directory access
- **THEN** startup rejects that state and recommends native Linux storage rather than silently weakening privacy

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

### Requirement: Explicit migration and reversible selection
The wrapper SHALL neither copy nor merge credentials or settings automatically. Documentation SHALL describe fresh isolated login, deliberate copying of selected state with sessions stopped, permission checks, and returning to shared mode by unsetting `CLAUDE_CONTAINER_STATE_DIR`. Changing modes SHALL NOT delete either profile.

#### Scenario: Isolated state reused and deselected
- **WHEN** a user restarts with the same dedicated home and later unsets the state override
- **THEN** the dedicated profile persists across its restarts and shared mode resumes without merging or deleting profiles

#### Scenario: Migration instructions reviewed
- **WHEN** a user reads the state-mode documentation
- **THEN** it identifies source and destination layouts, conflict handling, credential visibility to the agent, backup privacy, and the lack of automatic imports

### Requirement: Private state creation preserves the host process umask
Private state-directory creation SHALL NOT change the umask inherited by subsequent host image, launch, or lifecycle commands. Missing state directories SHALL still be created with user-only permissions in shared and isolated modes. Existing ownership, access, mode, and resolved-path checks SHALL remain enforced without recursive permission repair. Documentation SHALL distinguish this host creation policy from actual container process and file modes.

#### Scenario: Caller umask is preserved for later host commands
- **WHEN** the wrapper starts under caller umask `0022` or `0002` and creates missing state directories
- **THEN** subsequent host Podman commands inherit the caller's original umask
- **AND** the created state directories deny group and other access

#### Scenario: Private creation applies in both state modes
- **WHEN** shared Claude/OpenSpec configuration or an isolated application home and its configuration directories must be created
- **THEN** each directory created by those state operations has user-only permissions
- **AND** existing private-directory validation and isolated symlink-escape rejection still apply

#### Scenario: Unsafe existing directories are not repaired
- **WHEN** a selected credential directory already grants group or other access
- **THEN** startup fails with the existing path-specific privacy error
- **AND** existing permissions are not changed recursively

#### Scenario: Runtime permissions have separate evidence
- **WHEN** validation reports the modes of files created by a container session
- **THEN** it records actual container umask and observed file and directory modes
- **AND** it does not infer those modes from the host's private state-creation umask

### Requirement: Isolated state does not overlap the workspace
The wrapper SHALL refuse an isolated state directory that is the workspace mount, contains it, or lies inside it, comparing resolved physical paths. The check SHALL run before image or engine operations, on direct and managed launches, and in worktree mode SHALL use the parent directory that is mounted.

#### Scenario: State directory inside the workspace
- **WHEN** `CLAUDE_CONTAINER_STATE_DIR` names the workspace or a directory below it
- **THEN** startup fails before engine operations, naming the state directory and the workspace

#### Scenario: State directory containing the workspace
- **WHEN** the workspace lies below the selected state directory
- **THEN** startup fails with the same error

#### Scenario: Symlinked state directory
- **WHEN** the selected state path is a symlink that resolves inside the workspace
- **THEN** startup fails with the same error

#### Scenario: Managed launch
- **WHEN** a managed launch selects an isolated state directory that overlaps the workspace
- **THEN** the managed launcher refuses it before starting the wrapper

### Requirement: Read-only state
`CLAUDE_CONTAINER_READONLY_STATE`, a boolean (`1`, `true`, `yes`; empty, `0`, `false`, `no`), SHALL mount the Claude configuration directory and every shared directory read-only below the ephemeral home. They are taken from shared state or from the isolated home. Those directories SHALL already exist. The launcher SHALL NOT create them, SHALL NOT check their owner or privacy, and SHALL NOT pass them to restricted preparation as writable. The isolated home itself SHALL NOT be mounted.

#### Scenario: Read-only shared state
- **WHEN** `CLAUDE_CONTAINER_READONLY_STATE=1` is set and `~/.claude` and `~/.config/openspec` exist
- **THEN** the session sees them read-only and writes there fail

#### Scenario: Missing state
- **WHEN** read-only state is selected and a configuration directory does not exist
- **THEN** the launch stops before the engine and names the missing directory
