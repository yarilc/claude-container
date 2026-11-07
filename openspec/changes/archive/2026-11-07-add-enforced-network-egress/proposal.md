# Proposal

## Why

The fourteen pending network tasks in `todo.md` require an independently enforced boundary that survives arbitrary commands and mutable settings. Implementation proved that IP isolation alone is insufficient: a Unix socket exposed in a workspace can reach an outside service without an Internet interface or the approved proxy.

## What Changes

- **BREAKING**: introduce operator-selected `offline`, `provider`, and explicitly `unrestricted` runtime modes; default to offline, with documented migration from today's implicit unrestricted network.
- Isolate restricted sessions from Internet, host, LAN, metadata services, and other sessions. Provider mode reaches only a session-owned trusted destination-filtering proxy; unsupported enforcement stops startup.
- **BREAKING**: support Linux 6.6.87.2-microsoft-standard-WSL2 x86_64 with Landlock ABI 3 through a protected native bootstrap, filesystem Landlock rules and an additional restrictive in-process seccomp filter. Preserve the standard OCI seccomp profile and SELinux policy; require no kernel upgrade.
- **BREAKING**: deny new named/abstract Unix services in restricted modes, including private temporary listeners. Preserve own-loopback services and connected stream/seqpacket socket pairs; host daemon/SSH-agent sockets remain unavailable. Ordinary file persistence and shared/isolated configuration remain unchanged.
- Permit one bootstrap-verified, preconnected proxy data channel in provider mode, multiplexing independently authorized tunnels without opening new Unix sockets. Deny VSOCK/other socket families and asynchronous socket-creation bypasses; cover late-created sockets, aliases, socket placement, descriptor hygiene and same-session IPC in the release gate.
- Introduce protected, versioned policies with exact destinations, connection-time DNS/address checks, redacted diagnostics, and bounded ownership-based cleanup. Never expand policy from agent-writable settings or failed requests.
- Separate Anthropic API, account authentication, optional features, and maintenance access. Preserve TLS verification and existing single-file host CA trust. Keep API-key support implemented and covered by synthetic integration tests; a separately authorized real-key check is optional and non-blocking when a key is unavailable, with its unverified status explicit.
- **BREAKING**: reject exact `CLAUDE_CONTAINER_PODMAN=1` in offline and provider modes, including shell/YOLO sessions.
- Make image acquisition/build access an explicit operator maintenance decision, independent of runtime filtering.
- Add synthetic and real-rootless IP/IPC bypass tests and separately record authenticated Claude compatibility evidence. Keep restricted startup held closed until the complete revised gate passes; the observed WSL2 ABI-3 environment is the mandatory initial acceptance target. Current implementation/enforcement results and remaining authenticated gaps are recorded in docs/validation.md.
- Define a portable common contract for the five-wrapper initiative; implement only this repository's Claude wrapper and publish a parity checklist for sibling wrappers.

## Capabilities

### New Capabilities

- `network-egress`: runtime modes, inherited IPC enforcement, kernel capability requirements, trusted policy/proxy enforcement, transport restrictions, diagnostics, owned resources, Claude profiles, and acceptance evidence.

### Modified Capabilities

- `container-launcher`: explicitly authorized image preparation, mandatory restricted-mode bootstrap with transparent invocation, and network-resource shutdown within the existing lifecycle budget.
- `container-podman-access`: unrestricted runtime mode becomes an additional prerequisite for socket delegation.
- `container-isolation`: preserve standard runtime security policy while adding inherited Landlock and additional restrictive seccomp confinement; native approvals remain independent and socket delegation requires unrestricted mode.

## Impact

Implementation affects `claude-container.sh`, runtime/build inputs, protected native bootstrap and proxy/policy/relay assets, tests and documentation. It adds a kernel/ABI/bootstrap/engine support matrix with the measured WSL2 ABI-3 environment as its required initial target. Positive acceptance must run on that environment; upgrading the kernel is not a prerequisite. Workspace paths, ordinary shared/isolated file state, read-only root, tmpfs limits, standard OCI seccomp/SELinux, and opt-in CA trust remain constraints. This revision narrowly permits an additive unprivileged seccomp filter, never a replacement or weakened OCI profile. No kernel upgrade, privilege addition or implementation is performed by this planning revision.

No sibling repository is in scope; their rollout remains separately tracked. Completed component tasks retain their evidence; affected tasks are reopened and the IPC work is added to the checklist. N01–N14 and full restricted enforcement are not declared complete.
