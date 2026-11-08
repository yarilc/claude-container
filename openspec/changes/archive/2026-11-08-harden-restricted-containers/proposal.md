# Proposal

## Why

Restricted agent containers and their Internet-facing proxies currently retain the engine's default capability set and lack explicit container-level no-new-privileges. The proxy also has no explicit process or memory limit; N18 calls for reducing this authority and bounding resource consumption without weakening confinement.

## What Changes

- Require `--cap-drop=all` and `--security-opt=no-new-privileges` for offline/provider agent containers and session egress proxies.
- Bound each proxy to 128 processes and 256 MiB memory, subject to real acceptance under the existing bounded multiplex workload.
- Fail preparation if the engine cannot enforce required hardening or resource limits; never retry without them.
- Verify caller identity, bootstrap, relay, proxy socket/readiness, concurrent TLS traffic and owned cleanup under these settings.
- Preserve unrestricted launches and existing seccomp, SELinux, mount, CA, network and delegation contracts.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-isolation`: Require removal of capabilities and container-level no-new-privileges for restricted agents and proxies.
- `network-egress`: Require enforced proxy process/memory budgets and fail-closed behavior on resource exhaustion.

## Impact

Implementation targets are the two container creation paths in `claude-container.sh`, synthetic assertions in `tests/test_wrapper.py`, and real guard/network acceptance. README, `network/README.md`, the network contract and validation record must describe the effective settings and measured results. No new user-configurable authority or dependencies are introduced. This change can be implemented first on the currently measured WSL target; N19's `validate-linux-restricted-compatibility` must subsequently include these settings in its installation fingerprint and gate. N20-N25 and sibling rollout remain outside scope.
