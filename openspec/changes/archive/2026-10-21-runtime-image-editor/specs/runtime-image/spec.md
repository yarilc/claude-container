# Spec Delta

## ADDED Requirements

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
