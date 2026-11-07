# Proposal

## Why

Preparing a usable sandbox currently requires coordinating a rootless Podman service, a protected installation, a compiled guard, multiple images and many environment variables. An interactive setup should turn those manual steps into a reviewed, repeatable procedure, including for the supported WSL environment and users authenticating through a Claude account without an API key.

## What Changes

- Add `--container-setup` as a dedicated interactive host-side operation, usable before runtime configuration is valid and without launching a normal Claude session.
- Ask about network access, account or API authentication, shared or isolated state, optional Podman delegation, host CA trust, permission bypass and worktree exposure, with plain-language explanations and conservative defaults.
- Default first-run setup to provider-restricted networking and account authentication, preserving saved network choices on rerun and the direct wrapper's existing offline default.
- Check installed Podman and rootless prerequisites. Reuse a verified same-host Unix service or offer to enable `podman.socket` in a working systemd user session; otherwise provide exact manual recovery guidance. Do not install Podman or other host packages, use sudo, or change system-wide account/WSL configuration.
- Prepare a protected native installation, required runtime/toolchain/proxy images, the static guard and its manifest, private directories and selected policy through an explicitly confirmed maintenance phase.
- Save non-secret preferences outside application-writable mounts and provide a managed `claude-container` launcher that works from other workspaces without repeated exports or shell-profile changes.
- Validate the selected configuration with a guarded smoke check, offer account login when needed, and distinguish sandbox readiness from authentication that still needs user action.
- Support rerunning setup, reviewing existing choices and recovering from interrupted preparation without replacing the last working installation prematurely.

## Capabilities

### New Capabilities

- `container-setup`: Interactive sandbox preparation, user-scoped Podman service enablement, persistent managed launch preferences and truthful readiness reporting.

### Modified Capabilities

- `container-launcher`: Permit setup prerequisite diagnosis before launch-engine verification while retaining mandatory verification before all image operations and container creation.

## Impact

- `claude-container.sh`: setup dispatch/help and separation of setup from normal argument forwarding and runtime preflight.
- New host-side setup/configuration helpers and a generated user launcher; protected installation manifest covering runtime, setup and guard build inputs.
- Existing `network/build-guard.sh`, pinned build recipes, policy validation and runtime preflight reused rather than replaced; image preparation stays operator maintenance outside runtime egress filtering.
- User-owned installation/preferences/state paths and optional systemd user socket enablement; no host package installation, new runtime privileges, broader mounts, credential copying or automatic endpoint-policy expansion.
- `README.md`, `network/README.md`, `docs/validation.md`, synthetic setup tests and opt-in rootless/WSL acceptance instructions. Existing direct-wrapper environment-based invocation remains available.
