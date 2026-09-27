# Spec Delta

## Purpose

The runtime image provides the command-line tools needed by Claude Code sessions and commands run inside the container.

## ADDED Requirements

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
