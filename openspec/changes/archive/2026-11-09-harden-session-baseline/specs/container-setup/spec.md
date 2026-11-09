## ADDED Requirements

### Requirement: Setup collects agent resource budgets and session lifetime
Setup SHALL ask for the agent memory, CPU and process budgets and the optional session lifetime. It SHALL validate each answer with the same rules as the wrapper and repeat the question after an invalid answer. First-run defaults SHALL be `4g`, `2`, `512` and `0` (disabled). On rerun, the saved values SHALL be proposed. The setup plan SHALL list the selected values before confirmation.

#### Scenario: First setup accepts defaults
- **WHEN** the user accepts the proposed budget and lifetime answers on first setup
- **THEN** the saved preferences contain memory `4g`, CPU `2`, processes `512` and lifetime `0`
- **AND** the setup plan shows these values before the apply confirmation

#### Scenario: Invalid answer is asked again
- **WHEN** the user answers `0`, `max`, `-1` or a unitless memory value to a budget question
- **THEN** setup explains the accepted format and asks the same question again without saving anything

#### Scenario: Rerun proposes saved values
- **WHEN** setup is rerun after saving memory `8g` and lifetime `3600`
- **THEN** those values are the proposed answers

### Requirement: Saved budgets govern managed launches and verification
The managed launcher SHALL supply the saved budgets and lifetime through `CLAUDE_CONTAINER_MEMORY_LIMIT`, `CLAUDE_CONTAINER_CPU_LIMIT`, `CLAUDE_CONTAINER_PIDS_LIMIT` and `CLAUDE_CONTAINER_RUN_TIMEOUT` when these are absent from the launch environment. An explicitly present variable SHALL take precedence. Setup smoke and qualification SHALL use the saved values.

#### Scenario: Managed launch uses saved budgets
- **WHEN** the user launches through the managed command with no budget variables exported
- **THEN** the agent container receives the saved budgets and lifetime
- **AND** a restricted launch matches the qualification report produced by setup

#### Scenario: Explicit override differs from qualified values
- **WHEN** the user exports `CLAUDE_CONTAINER_MEMORY_LIMIT=16g` for a restricted managed launch qualified with `4g`
- **THEN** the override is used and the qualification check stops the launch with requalification guidance

#### Scenario: Smoke verifies saved values
- **WHEN** setup runs its installed smoke check
- **THEN** the smoke compares the effective cgroup limits with the saved budgets, not with ambient environment values

### Requirement: Preferences without budgets are migrated
Setup SHALL read saved preferences from earlier schema versions that lack budget and lifetime fields. It SHALL fill in the first-run defaults as proposed answers. New installations SHALL always be saved with the current schema. Unknown fields or unsupported schema versions SHALL still be rejected.

#### Scenario: Rerun from an earlier installation
- **WHEN** setup is rerun over an installation whose preferences use the previous schema
- **THEN** setup proposes the default budgets and lifetime and saves the activated release with the current schema

#### Scenario: Unsupported schema
- **WHEN** preferences declare an unknown schema version or contain an unknown field
- **THEN** setup and the launcher fail before image operations, as before
