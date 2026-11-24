# Spec Delta

## MODIFIED Requirements

### Requirement: Evidence and common contract documentation
Documentation SHALL map N01–N14 to implementation and acceptance, publish the portable mode/profile contract and sibling-wrapper parity status, and date/version endpoint inventories. Validation SHALL distinguish synthetic enforcement, real-rootless bypass checks, and authenticated provider compatibility. Untested checks SHALL remain unavailable.

#### Scenario: Provider profile readiness
- **WHEN** a profile is declared verified for a CLI/authentication version
- **THEN** evidence covers login, token refresh, streaming, long-lived requests, supported WebSockets, proxy/CA behavior, shell and native permission modes
- **AND** credential-free bypass tests separately cover DNS/UDP/IPv6, direct IP/ports, deceptive hosts, redirects, host/LAN/metadata, administration, concurrency, leftover delegation opt-in rejection, containment of the session container engine and its nested containers, failure closure, and cleanup
- **AND** IPC evidence covers existing and late-created host sockets, persistent socket placement, aliases, explicit datagram sends, abstract endpoints, inherited descriptors, compat/x32 and asynchronous syscall bypasses, pair retargeting, descendant enforcement, denied private named listeners, permitted pairs/loopback, ordinary files and alternate host transports

#### Scenario: Real API key unavailable during acceptance
- **WHEN** API-key support has mandatory synthetic client/policy/proxy coverage but no real API key is available
- **THEN** the real-key compatibility check is optional, recorded as unavailable and excluded from mandatory change completion
- **AND** API-key support remains implemented, account use does not depend on that key, and no real-provider verification is claimed without actual evidence
- **AND** mandatory enforcement tests and separate account acceptance are not waived

#### Scenario: Target environment and historical component passes
- **WHEN** a user reviews the measured WSL ABI-3 environment or passes collected before the revised guard exists
- **THEN** documentation identifies WSL as the required initial target, separates measured enforcement from remaining validation gaps, and labels historical passes as component evidence
- **AND** ABI-3 prerequisites, additive filter/protocol identity, named Unix IPC limitations and actual acceptance results are stated separately

#### Scenario: User reviews limits
- **WHEN** a user reads the network documentation
- **THEN** it explains that allowed services can receive session data, remote provider tools are outside local filtering, and runtime filtering does not constrain host-side image pulls or builds
- **AND** no sibling wrapper is claimed implemented or verified without repository-specific evidence
