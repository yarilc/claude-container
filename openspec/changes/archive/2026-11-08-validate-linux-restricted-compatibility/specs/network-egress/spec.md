# Spec Delta

## MODIFIED Requirements

### Requirement: Mandatory inherited IPC enforcement
Restricted sessions SHALL admit qualifying native Linux and WSL2 x86_64 installations with usable Landlock ABI >= 3, using filesystem confinement plus an additional restrictive in-process seccomp filter before agent code. Restrictions SHALL survive descendants. The standard OCI seccomp profile and any active SELinux/AppArmor policy SHALL remain active. Compatibility with SELinux/AppArmor SHALL NOT be guaranteed; their enabled status alone SHALL NOT reject preparation. No ABI-9 feature or kernel upgrade SHALL be required.

#### Scenario: Target WSL kernel
- **WHEN** the measured WSL x86_64 target provides usable ABI 3 and permits both required enforcement layers
- **THEN** restricted preparation does not reject it solely for lacking newer Landlock IPC rights
- **AND** local qualification requires the installation enforcement gate, while measured release support requires separately recorded real-rootless acceptance

#### Scenario: Unsupported or blocked kernel features
- **WHEN** ABI is below 3, required Landlock rules or the additional filter cannot install, or the syscall architecture is unsupported
- **THEN** startup fails before Claude, Bash, relay or application initialization
- **AND** no privilege addition, replacement/weakened OCI profile, automatic kernel change or unrestricted retry occurs

#### Scenario: Native approvals cannot remove confinement
- **WHEN** a session forks, execs, creates threads or uses native permission bypass
- **THEN** all agent-controlled descendants retain both enforcement layers and cannot acquire unfiltered external peers
- **AND** another session sharing file state does not gain access to its IPC

#### Scenario: Native Linux with active security modules
- **WHEN** native Linux x86_64 reports SELinux or AppArmor enabled
- **THEN** preparation evaluates actual enforcement and local qualification without rejecting the enabled status alone
- **AND** any policy denial stops preparation without disabling security modules, changing labels or adding privileges

### Requirement: Full platform support requires transport evidence
Successful installation of both enforcement layers SHALL be necessary but insufficient for restricted startup. A protected installation gate SHALL verify IP, Unix IPC and enabled alternate host-facing transports under the actual kernel, bootstrap, engine/backend and security policy. An uncontained or unassessable path SHALL keep startup unavailable. Local qualification SHALL NOT imply an exhaustively measured platform. Socket creation or absence of a listening peer SHALL NOT prove containment.

#### Scenario: Alternate host transport or incomplete evidence
- **WHEN** a platform exposes a non-IP transport such as AF_VSOCK or lacks controlled evidence for a required boundary
- **THEN** local qualification fails until required denial is established with syscall tests and controlled positive controls
- **AND** restricted startup remains unavailable until the installation gate passes; an unavailable required check is not a pass

#### Scenario: New combination qualifies locally
- **WHEN** an eligible native Linux or WSL2 installation passes every required local check but lacks full release acceptance for its combination
- **THEN** ordinary restricted startup can proceed with a visible locally-qualified, not-release-measured notice
- **AND** no exhaustive distribution matrix, authenticated-provider verification or SELinux/AppArmor compatibility guarantee is claimed

## ADDED Requirements

### Requirement: Capability-based restricted platform prerequisites
Restricted preparation SHALL require Linux x86_64, rootless Podman server >= 4.9 with Netavark over a verified same-host Unix service, host Python 3, usable Landlock ABI >= 3 and standard OCI seccomp. Exact kernel/server pins and upper version bounds SHALL NOT determine admission. Effective enforcement, protected assets and the local qualification gate SHALL remain mandatory.

#### Scenario: Different kernel and Podman versions
- **WHEN** an installation satisfies the prerequisites with a native Linux kernel or WSL2 release and a parseable stable Podman server version at or above 4.9
- **THEN** preparation does not reject it because its version differs from the recorded WSL/4.9.3 target
- **AND** actual guard installation and qualification still determine readiness

#### Scenario: Missing or unverifiable prerequisite
- **WHEN** architecture, rootless status, service identity, version, backend, ABI or seccomp is unsupported, missing or malformed
- **THEN** preparation fails before ordinary agent execution with the failed prerequisite identified
- **AND** no local-engine, rootful, different-backend or unrestricted fallback occurs

### Requirement: Credential-free local enforcement qualification
Each restricted installation SHALL pass a bounded credential-free gate through its production launch and guard path before ordinary use. Required denial checks SHALL have controlled positive controls or demonstrate explicit enforcing syscall rejection. Missing fixtures, unrelated connectivity failure, skipped required checks and unavailable transport evidence SHALL fail qualification.

#### Scenario: Mandatory IP and IPC controls
- **WHEN** offline or provider mode is qualified
- **THEN** the gate verifies direct IPv4/IPv6 denial, no external DNS/UDP path, denial of existing and late external Unix endpoints and host-bind socket publication, and denial of alternate socket families and pair retargeting
- **AND** actual loopback and permitted connected-pair data exchange, descendant enforcement and ordinary caller-owned file persistence succeed
- **AND** controlled host endpoints are reachable by an unconfined positive control when the denial depends on a listening peer

#### Scenario: Provider boundary qualification
- **WHEN** provider mode is qualified
- **THEN** controlled TLS endpoints exercise matching CONNECT/SNI with certificate verification, mismatched-SNI zero-byte rejection, denied authority and fail-closed channel/proxy loss through the production guard, relay and proxy
- **AND** isolated fixture policy and certificates never modify production host inventories, private-address exclusions or CA defaults

#### Scenario: Probe or ordinary smoke is insufficient
- **WHEN** only an ABI query, socket creation result, version query or the previous smoke check succeeds
- **THEN** no successful qualification report is issued
- **AND** ordinary restricted startup remains blocked
