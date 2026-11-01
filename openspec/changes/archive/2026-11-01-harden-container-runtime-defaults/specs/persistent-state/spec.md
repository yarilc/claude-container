# Spec Delta

## ADDED Requirements

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
