## ADDED Requirements

### Requirement: Single protected agent profile
All agent-specific values used by the shared network sandbox and setup components SHALL come from one data-only agent profile and its provider policy file. Examples are wrapper and variable names, images, labels, installation and state names, native configuration and credential variables, authentication assistance and policy profiles. The profile SHALL be schema-validated, trusted-path checked and outside agent-writable mounts.

#### Scenario: Invalid or unprotected profile
- **WHEN** the profile is missing, malformed, has duplicate or unknown keys, fails field validation, or is reachable through a writable workspace or state mount or an escaped symlink
- **THEN** setup, qualification and restricted startup fail before the agent runs, identify the profile, and do not fall back to built-in defaults

#### Scenario: Profile not taken from the workspace
- **WHEN** the current workspace contains a file with the profile's name or layout
- **THEN** the wrapper uses only the profile in its protected installation or checkout and ignores the workspace copy

### Requirement: Profile-bound restricted identity
The agent profile and its provider policy file SHALL be part of the protected code identity recorded in local qualification reports. Any change to either SHALL invalidate matching qualification evidence.

#### Scenario: Profile changed after qualification
- **WHEN** the installed profile or provider policy differs from the one recorded in the current qualification report
- **THEN** ordinary restricted launches are refused with setup or requalification guidance

### Requirement: Agent-neutral shared sandbox components
The shared network sandbox and setup components, including the compiled guard, SHALL contain no agent-specific identifiers. In-container paths, the guard binary name and the multiplex protocol marker SHALL be agent-neutral. Host-visible images, labels, variables and installation paths SHALL stay per-agent, as declared by the profile.

#### Scenario: Shared components contain an agent identifier
- **WHEN** a shared network or setup file contains an agent-specific identifier declared by the profile, outside the documented allow-list
- **THEN** the alignment test fails

#### Scenario: Two wrappers on the same host
- **WHEN** two wrappers using different profiles run restricted sessions or qualification concurrently
- **THEN** each creates, inspects and cleans up only resources carrying its own profile's labels and image names

#### Scenario: Unchanged operator interface
- **WHEN** an existing user runs the wrapper with the same environment variables, images and saved setup preferences after requalification
- **THEN** modes, profiles, hosts, defaults, hardening and diagnostics behave as before the change
