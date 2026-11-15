# Spec Delta

## ADDED Requirements

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
