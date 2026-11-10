# Spec Delta

## ADDED Requirements

### Requirement: Engine default secrets mount is masked
Every agent container, every provider proxy and every qualification gate container SHALL be created with an empty read-only tmpfs at `/run/secrets`, so that an engine default mount there (such as RHEL subscription secrets from `mounts.conf`) is neither visible nor writable. The sandbox SHALL NOT require host configuration changes to achieve this.

#### Scenario: Host with a default secrets mount
- **WHEN** the engine's `mounts.conf` maps `/usr/share/rhel/secrets` to `/run/secrets`
- **THEN** the agent container has exactly one mount at `/run/secrets`, an empty tmpfs mounted read-only
- **AND** no host subscription file is readable inside the container

#### Scenario: Host without a default secrets mount
- **WHEN** the engine adds no mount at `/run/secrets`
- **THEN** the agent container still has the empty read-only tmpfs there, and the session behaves as before
