# Proposal

## Why

Restricted startup currently rejects every kernel except one WSL release, every Podman server except 4.9.3, and all hosts reporting SELinux or AppArmor enabled. N19 should admit qualifying native Linux and WSL2 installations through actual local enforcement evidence, without claiming every distribution/security-policy combination has been measured.

## What Changes

- Replace exact version pins with Linux x86_64, rootless Podman >= 4.9 with Netavark over the existing same-host Unix service, usable Landlock ABI >= 3, standard OCI seccomp and successful additive guard enforcement. Do not impose a kernel release minimum in place of capability checks or an upper version bound.
- Consolidate wrapper/setup platform validation in protected installed code.
- Permit SELinux/AppArmor to remain enabled without guaranteeing compatibility; a policy denial stops preparation or launch and never triggers policy changes.
- **BREAKING**: Require a protected, matching, successful local enforcement report before ordinary restricted startup, including manually prepared installations. Setup performs this gate before activation; changed enforcement inputs require revalidation.
- Extend the existing smoke check into a credential-free local IP/IPC/transport gate with controlled positive controls and provider checks, while retaining per-launch bootstrap enforcement.
- Distinguish locally qualified installations from release combinations with recorded full acceptance. Publish the actual environment, tested boundaries and unavailable checks without requiring an exhaustive platform matrix.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `network-egress`: Replace the measured-platform admission model with capability prerequisites, mandatory local qualification and precise evidence labels.
- `container-setup`: Require candidate qualification, protected reports, invalidation and rollback before activation.
- `container-launcher`: Require matching local qualification and common platform validation for ordinary restricted launches.

## Impact

Targets include `claude-container.sh`, `network/control.py` or a protected shared validator, `setup/setup.py`, `setup/smoke.py`, `setup/common.py`, protected qualification fixtures and wrapper/setup/runtime tests. Update README/help, AGENTS.md, setup/network guidance, contract, validation and the N19 TODO entry during implementation. Implement after N18 (`harden-restricted-containers`) so qualification covers the final container hardening. Preserve default offline selection, explicit environment-based invocation, authentication/maintenance separation, existing socket restrictions and all TLS destination-binding guarantees. N20's mandatory first-run setup UX, other architectures/backends, TLS interception and sibling wrappers are excluded.
