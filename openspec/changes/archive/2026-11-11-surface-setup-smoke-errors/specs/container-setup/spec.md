# Spec Delta

## ADDED Requirements

### Requirement: Smoke failure diagnostics
When the installed-sandbox smoke launch exits nonzero or does not confirm readiness, setup SHALL print a bounded excerpt of the launch's standard error before its failure message. The excerpt SHALL keep only printable characters and SHALL be limited to the last 5 non-empty lines, each truncated to 2048 characters. Setup SHALL still report incomplete setup, return nonzero and leave the candidate inactive. Successful smoke launches SHALL print no excerpt.

#### Scenario: Wrapper refuses during the smoke launch
- **WHEN** the wrapper exits nonzero during the smoke launch with a refusal on standard error, such as a non-private state directory
- **THEN** setup prints that refusal line, followed by the incomplete-setup message
- **AND** the candidate installation is not activated

#### Scenario: Smoke output lacks the readiness marker
- **WHEN** the smoke launch exits zero without printing the readiness marker exactly once
- **THEN** setup prints the bounded standard-error excerpt and reports that the smoke check did not confirm readiness

#### Scenario: Hostile or oversized diagnostics
- **WHEN** the smoke launch writes terminal control sequences, non-printable bytes or very long lines to standard error
- **THEN** the excerpt contains no control characters, at most 5 lines and at most 2048 characters per line

### Requirement: Profile-declared shared-directory privacy
The optional boolean agent-profile field `native.private_shared_dirs` (default `false`) SHALL declare that the wrapper requires every shared directory to be private. When it is `true`, setup SHALL check each shared directory before image preparation, as it checks the configuration directory: caller-owned, private and accessible. Setup SHALL NOT report a shared directory as private unless it passed that check.

#### Scenario: Pi or OpenCode shared directory with group or other permissions
- **WHEN** the profile sets `private_shared_dirs: true` and an existing shared directory has group or other permissions
- **THEN** setup fails before image preparation, names that directory and does not change its permissions

#### Scenario: Claude shared tool settings
- **WHEN** the profile leaves `private_shared_dirs` unset and an existing shared directory is accessible but not private
- **THEN** setup accepts it as before: shared directories are created privately when missing and must be accessible
- **AND** the setup summary does not call the directory private

#### Scenario: Invalid profile field
- **WHEN** `native.private_shared_dirs` is present but not a boolean
- **THEN** profile validation fails and setup does not start

### Requirement: Actionable private-directory refusal
When setup refuses an existing state directory as not private, the message SHALL name the path and state the reason found:
- a different owner;
- group or other permissions, with the observed octal mode;
- missing read, write or traverse access.

For the permission case, the message SHALL name `chmod 700 <path>` or native Linux storage as the fix. Setup SHALL NOT change the permissions itself.

#### Scenario: Directory created by a host tool with mode 755
- **WHEN** an existing configuration directory has mode `755` and belongs to the caller
- **THEN** the refusal names the path, mode `755`, and the `chmod 700` fix
- **AND** the directory mode is unchanged after setup exits
