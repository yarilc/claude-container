# Spec Delta

## MODIFIED Requirements

### Requirement: Verified launch engine
Except for wrapper help and setup prerequisite diagnosis, the wrapper SHALL verify that the engine used for image operations and container launch reports Linux and rootless operation. Failed or unrecognized verification SHALL stop before image inspection, build, or container creation. Setup SHALL perform this verification after any approved user-service preparation and before its image operations or smoke/login container creation.

#### Scenario: Local rootless engine without delegation
- **WHEN** local Podman reports Linux and rootless operation and delegation is disabled
- **THEN** engine verification succeeds without requiring a delegation socket

#### Scenario: Engine cannot be verified
- **WHEN** engine verification fails or reports rootful, non-Linux, empty, or malformed results
- **THEN** the wrapper exits nonzero with an actionable engine error before image operations or launch

#### Scenario: Setup can diagnose missing prerequisites
- **WHEN** interactive setup is requested before Podman or its required user service is usable
- **THEN** it can diagnose prerequisites and offer permitted user-service preparation without normal session preflight
- **AND** no image operation or container creation occurs until the selected engine passes verification
