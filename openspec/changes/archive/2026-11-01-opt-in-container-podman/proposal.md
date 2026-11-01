# Proposal

## Why

The wrapper currently gives every Claude session access to the host Podman API, including control of the host user's containers and volumes. This access should require an explicit opt-in so ordinary sessions do not receive that authority or require an API socket.

## What Changes

- **BREAKING**: Enable container access to the host Podman API only when the host environment variable `CLAUDE_CONTAINER_PODMAN` equals the exact string `1`.
- With the variable unset, empty, or any other value, omit the Podman socket mount and `CONTAINER_HOST`, and skip host API socket validation.
- With access enabled, preserve the existing rootless socket location, validation, and remote-client configuration in both Claude and shell modes.
- Document the new default, opt-in examples, migration, and the distinction between host Podman used to run the wrapper and Podman access granted inside the container.

## Capabilities

### New Capabilities

- `container-podman-access`: Control whether wrapper-launched sessions receive access to the host Podman API through an explicit environment opt-in.

### Modified Capabilities

None.

## Impact

- `claude-container.sh`: Conditional socket validation, socket mount, remote-client environment, and wrapper help.
- `README.md`: Update setup, usage, socket prerequisites, and security explanations to reflect optional API access.
- `AGENTS.md`: Align repository guidance and verification expectations with the optional API socket.
- The runtime image retains the Podman client; no new dependency or image variant is required. Existing sessions that launch child containers must set `CLAUDE_CONTAINER_PODMAN=1` to retain that behavior.
