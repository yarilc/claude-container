# Spec Delta

## ADDED Requirements

### Requirement: Private runtime hierarchies admit only verified read-only masks
Before agent code runs, the restricted bootstrap SHALL reject every nested mount below `/tmp`, `/run` and `/var/tmp`, except the engine metadata file `/run/.containerenv`, the provider runtime `/run/sandbox-egress` and `/run/secrets` when it is a `tmpfs` whose per-mount options are read-only. A writable or non-tmpfs `/run/secrets` SHALL be rejected like any other nested mount.

#### Scenario: Read-only secrets mask
- **WHEN** a restricted session starts with the read-only tmpfs mask at `/run/secrets`
- **THEN** the bootstrap accepts the layout and the agent starts

#### Scenario: Writable secrets mount
- **WHEN** `/run/secrets` is a writable mount, for example the engine default without the mask
- **THEN** startup stops with the nested private IPC mount diagnostic before agent code runs

#### Scenario: Other nested mount
- **WHEN** any other host or tmpfs mount appears below `/tmp`, `/run` or `/var/tmp`, read-only or not
- **THEN** startup stops before agent code runs
