# Spec Delta

## REMOVED Requirements

### Requirement: Podman API access requires the exact opt-in value
**Reason**: Host Podman delegation is removed; sessions get a private container engine instead (`session-container-engine`).
**Migration**: A leftover exact `CLAUDE_CONTAINER_PODMAN=1` stops the launch with guidance (`container-launcher`); add the needed images as toolchains.

### Requirement: Socket validation is conditional
**Reason**: Host Podman delegation is removed; sessions get a private container engine instead (`session-container-engine`).
**Migration**: None needed: no session receives a host Podman socket, so there is no endpoint to select, verify or validate.

### Requirement: Access policy applies across launch modes
**Reason**: Host Podman delegation is removed; sessions get a private container engine instead (`session-container-engine`).
**Migration**: None needed: no session receives a host Podman socket, so there is no endpoint to select, verify or validate.

### Requirement: Document the optional authority grant
**Reason**: Host Podman delegation is removed; sessions get a private container engine instead (`session-container-engine`).
**Migration**: The README documents the session container engine and image toolchains instead (`session-container-engine`).

### Requirement: Exposed Podman service must report rootless operation
**Reason**: Host Podman delegation is removed; sessions get a private container engine instead (`session-container-engine`).
**Migration**: None needed: no session receives a host Podman socket, so there is no endpoint to select, verify or validate.

### Requirement: Delegation endpoint selection
**Reason**: Host Podman delegation is removed; sessions get a private container engine instead (`session-container-engine`).
**Migration**: None needed: no session receives a host Podman socket, so there is no endpoint to select, verify or validate.

### Requirement: Single-record delegation verification response
**Reason**: Host Podman delegation is removed; sessions get a private container engine instead (`session-container-engine`).
**Migration**: None needed: no session receives a host Podman socket, so there is no endpoint to select, verify or validate.
