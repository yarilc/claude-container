# runtime-image Specification

## Purpose

The runtime image provides the command-line tools needed by Claude Code sessions and commands run inside the container.

## Requirements

### Requirement: Python 3 is available in the runtime image
The runtime image SHALL provide the Python 3 interpreter through the `python3` command.

#### Scenario: Invoke Python 3
- **WHEN** a user runs `python3 --version` in a container started from the runtime image
- **THEN** the Python 3 interpreter reports its version and exits successfully

### Requirement: Bubblewrap is available in the runtime image
The runtime image SHALL provide Bubblewrap through the `bwrap` command.

#### Scenario: Invoke Bubblewrap
- **WHEN** a user runs `bwrap --version` in a container started from the runtime image
- **THEN** Bubblewrap reports its version and exits successfully

### Requirement: A terminal editor is available in the runtime image
The runtime image SHALL provide the `nano` terminal editor through the `nano` command.

#### Scenario: Invoke nano
- **WHEN** a user runs `nano --version` in a container started from the runtime image
- **THEN** nano reports its version and exits successfully

### Requirement: The runtime image sets the default editor
The runtime image SHALL set the `EDITOR` and `VISUAL` environment variables to `nano`, so commands that open an editor use it without further configuration.

#### Scenario: Editor variables inside the container
- **WHEN** a user runs `echo "$EDITOR" "$VISUAL"` in a container started from the runtime image
- **THEN** both values are `nano`

#### Scenario: Host editor is not forwarded
- **WHEN** the host sets `EDITOR` to an editor that the runtime image does not provide
- **THEN** the container still sets `EDITOR` and `VISUAL` to `nano`
