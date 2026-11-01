# Proposal

## Why

With `CLAUDE_CONTAINER_PODMAN=1`, the wrapper currently checks only that the expected Unix socket exists; its location does not prove that it serves a rootless engine. Adopt Antigravity's explicit socket-service query so an enabled session cannot receive wrapper-provided access to an unverified or rootful service.

## What Changes

- Query the exact socket selected for exposure using Podman's explicit remote URL and require a successful response reporting rootless operation.
- **BREAKING**: Enabled launches stop before image operations or container startup if the service is unreachable, reports rootful operation, or returns an unexpected rootless result.
- Preserve the fixed `/run/user/<caller-uid>/podman/podman.sock` path, exact-value opt-in, socket mount, and container environment in both launch modes. Disabled sessions perform no API-service probe.
- Document the enforced check and its failure recovery in wrapper help, README, and repository verification guidance.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-podman-access`: Require affirmative rootless verification of the exposed service when access is enabled, with actionable failures and conditional probing.

## Impact

- Implementation: `claude-container.sh` enabled-access validation, shared by Claude and shell modes.
- Documentation: `README.md`, wrapper help, and `AGENTS.md` testing guidance.
- Verification: stubbed Podman responses and optional real rootless-service checks; no new runtime dependency, image change, socket configuration, or persistent-state migration.
- Reference: [Antigravity wrapper](https://github.com/yarilc/antigravity-container/blob/main/antigravity-container.sh), inspected on 2026-11-01. Only its selected-service rootless check is adopted; its broader engine/context restrictions and socket-path remapping are outside this change.
