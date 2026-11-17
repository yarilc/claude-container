# shared-launcher Specification

## Purpose
Defines how Claude's launcher is built from the shared Bash core of the `sandbox-container` reference and Claude's own agent part, so launcher behavior is specified, fixed and tested once for all wrappers.

## Requirements

### Requirement: Launcher runs on the shared core
`claude-container.sh` SHALL be the thin entry script of the reference. It SHALL be identical to the reference's `sandbox-container.sh` after the wrapper name is replaced, and SHALL only source `launcher/core.sh` with `agent/launcher.sh` and its arguments. `launcher/core.sh` SHALL be a byte-identical copy from the adopted reference tag, recorded in the reference-copy manifest. Claude SHALL NOT keep launcher logic outside the core and its agent part.

#### Scenario: Core edited in this wrapper
- **WHEN** `launcher/core.sh` differs from the adopted reference tag
- **THEN** the reference-copy test fails naming the file

#### Scenario: Entry script compared with the reference
- **WHEN** `claude-container.sh` is compared with the reference entry script after replacing the wrapper name
- **THEN** they are identical

### Requirement: Claude agent launcher part
`agent/launcher.sh` SHALL hold Claude's profile data for the core, consistent with `agent/profile.json` and `agent/policies/default.json`, including a credential entry for each policy profile. It SHALL declare Claude's optional-traffic settings as provider-only settings. Claude's hooks SHALL be `agent_approval_bypass`, which turns an enabled `CLAUDE_YOLO` into the `--dangerously-skip-permissions` argument, and `agent_help`, which documents `CLAUDE_YOLO` and its effect.

#### Scenario: Profile and launcher part disagree
- **WHEN** `agent/launcher.sh` and `agent/profile.json` or the default policy declare different values for the same property
- **THEN** the shared alignment test fails naming the property

#### Scenario: Credential entries
- **WHEN** the alignment test reads `AGENT_CREDENTIALS`
- **THEN** it lists `anthropic-api=ANTHROPIC_API_KEY` and `anthropic-account=` with an empty credential

#### Scenario: Provider-only settings
- **WHEN** a provider session starts
- **THEN** it receives `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`, `DISABLE_AUTOUPDATER=1`, `DISABLE_TELEMETRY=1`, `DISABLE_ERROR_REPORTING=1`, `ENABLE_CLAUDEAI_MCP_SERVERS=false` and `CLAUDE_CODE_DISABLE_ARTIFACT=1`
- **AND** offline and unrestricted sessions receive none of them from the agent part

#### Scenario: No other agent code
- **WHEN** the core runs Claude's agent part
- **THEN** every hook other than `agent_approval_bypass` and `agent_help` uses the core default

#### Scenario: Help documents the approval bypass
- **WHEN** `--container-help` runs
- **THEN** it lists `CLAUDE_YOLO` with `--dangerously-skip-permissions` after the common variables

### Requirement: Claude launcher tests cover only Claude's part
Claude's launcher behavior SHALL be tested by the shared `tests/test_launcher.py` and `tests/fake_podman.py`, copied unchanged from the reference tag. `tests/test_wrapper.py` SHALL test only:
- Claude's hooks;
- Claude's agent data;
- its credential and provider settings;
- its shipped policy inventories;
- the real image.

A Claude launcher case that the shared tests do not cover SHALL be added to the reference before this wrapper adopts it, not kept as a wrapper copy.

#### Scenario: Wrapper runtime tests
- **WHEN** `bash tests/run-runtime.sh --wrapper` runs
- **THEN** it runs both `tests/test_launcher.py` and `tests/test_wrapper.py` against this checkout

#### Scenario: Approval bypass combinations
- **WHEN** `tests/test_wrapper.py` runs every combination of `CLAUDE_YOLO` and `CLAUDE_CONTAINER_PODMAN=1` in unrestricted shared and isolated modes
- **THEN** only `CLAUDE_YOLO` determines the `--dangerously-skip-permissions` argument, and only the Podman opt-in determines the delegation mounts and variables
