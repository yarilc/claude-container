# persistent-state Specification

## Purpose

Preserve compatible shared Claude state while offering explicit application-home isolation and enforcing private credential directory ownership and permissions.

## Requirements

### Requirement: Compatible shared state by default
With `CLAUDE_CONTAINER_STATE_DIR` unset or empty, the wrapper SHALL mount `${CLAUDE_CONFIG_DIR:-$HOME/.claude}` read/write at `/claude-home/.claude` and host `$HOME/.config/openspec` read/write at `/claude-home/.config/openspec`. It SHALL keep the remaining application home read-only and SHALL NOT create unused host cache or share directories.

#### Scenario: Existing default profile
- **WHEN** no state or Claude configuration override is selected
- **THEN** the existing host `~/.claude` and OpenSpec configuration remain the shared persistent sources

#### Scenario: Custom shared Claude directory
- **WHEN** `CLAUDE_CONFIG_DIR` names a custom directory and isolated state is not selected
- **THEN** that directory supplies Claude state and shared host OpenSpec configuration remains mounted

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
The wrapper SHALL resolve selected state sources to physical absolute paths. In isolated mode, existing Claude and OpenSpec configuration paths SHALL resolve within that home; escaping configuration symlinks SHALL fail. Documentation SHALL distinguish application-state isolation from access granted independently by workspace mounts or socket delegation.

#### Scenario: Top-level state alias
- **WHEN** the selected state path is a symlink to an accessible private directory
- **THEN** its resolved physical path is used as the bind source

#### Scenario: Isolated configuration escapes home
- **WHEN** `.claude` or `.config/openspec` resolves outside the selected isolated home through a symlink
- **THEN** startup fails with a path-specific isolation error

### Requirement: Explicit migration and reversible selection
The wrapper SHALL neither copy nor merge credentials or settings automatically. Documentation SHALL describe fresh isolated login, deliberate copying of selected state with sessions stopped, permission checks, and returning to shared mode by unsetting `CLAUDE_CONTAINER_STATE_DIR`. Changing modes SHALL NOT delete either profile.

#### Scenario: Isolated state reused and deselected
- **WHEN** a user restarts with the same dedicated home and later unsets the state override
- **THEN** the dedicated profile persists across its restarts and shared mode resumes without merging or deleting profiles

#### Scenario: Migration instructions reviewed
- **WHEN** a user reads the state-mode documentation
- **THEN** it identifies source and destination layouts, conflict handling, credential visibility to the agent, backup privacy, and the lack of automatic imports
