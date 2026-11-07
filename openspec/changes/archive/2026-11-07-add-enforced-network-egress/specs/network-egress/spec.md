# Spec Delta

## Purpose

Constrain network egress and external IPC independently of Claude and its tools, with operator-owned policies and evidence of real rootless enforcement.

## ADDED Requirements

### Requirement: Operator-selected runtime modes
The wrapper SHALL accept `CLAUDE_CONTAINER_NETWORK=offline|provider|unrestricted`, defaulting unset or empty values to `offline`. Other values SHALL fail before image operations. Only explicit `unrestricted` SHALL remove the runtime destination boundary. Agent-writable configuration SHALL NOT select or broaden the outer policy.

#### Scenario: Default and invalid selection
- **WHEN** the operator leaves the mode unset or empty
- **THEN** the session uses offline networking and reports the selected mode
- **AND** an unknown nonempty mode fails without image operations or agent startup

#### Scenario: Policy cannot escalate itself
- **WHEN** workspace settings, application state, or commands request a broader policy or remove proxy variables
- **THEN** the running session retains its operator-selected outer boundary

### Requirement: Restricted sessions have no direct external path
Offline sessions SHALL have only their own loopback services. Provider sessions SHALL additionally reach only the trusted proxy frontend. Restricted sessions SHALL have no direct Internet route or secondary unrestricted attachment and SHALL deny host, LAN, metadata, other sessions, and proxy administration access. Unsupported enforcement SHALL stop startup before the agent runs.

#### Scenario: Direct connection attempts
- **WHEN** a restricted session tries direct IPv4/IPv6 sockets, host aliases, host gateway, private destinations, or a second session
- **THEN** those connections fail independently of client proxy settings

#### Scenario: Host or shared namespace defaults
- **WHEN** engine defaults would share host PID/IPC namespaces or those of another container
- **THEN** the restricted launch explicitly selects private namespaces and exposes no host process or IPC handles
- **AND** the proxy remains outside the agent's PID/IPC domains

#### Scenario: Backend cannot enforce isolation
- **WHEN** the selected rootless backend/version or resource setup cannot establish the required boundary
- **THEN** startup fails with a diagnostic and cleans up owned resources without starting the agent

### Requirement: Mandatory inherited IPC enforcement
Restricted sessions SHALL support Linux 6.6.87.2-microsoft-standard-WSL2 x86_64 with usable Landlock ABI 3, using filesystem confinement plus an additional restrictive in-process seccomp filter before agent code. Restrictions SHALL survive descendants. The standard OCI seccomp profile and SELinux policy SHALL remain active. No ABI-9 feature or kernel upgrade SHALL be required.

#### Scenario: Target WSL kernel
- **WHEN** the measured WSL x86_64 target provides usable ABI 3 and permits both required enforcement layers
- **THEN** restricted preparation does not reject it solely for lacking newer Landlock IPC rights
- **AND** full support is established only after the real-rootless acceptance gate passes

#### Scenario: Unsupported or blocked kernel features
- **WHEN** ABI is below 3, required Landlock rules or the additional filter cannot install, or the syscall architecture is unsupported
- **THEN** startup fails before Claude, Bash, relay or application initialization
- **AND** no privilege addition, replacement/weakened OCI profile, automatic kernel change or unrestricted retry occurs

#### Scenario: Native approvals cannot remove confinement
- **WHEN** a session forks, execs, creates threads or uses native permission bypass
- **THEN** all agent-controlled descendants retain both enforcement layers and cannot acquire unfiltered external peers
- **AND** another session sharing file state does not gain access to its IPC

### Requirement: External Unix endpoints are denied
Restricted processes SHALL be unable to connect or explicitly send to unapproved external Unix endpoints through mounts or aliases, including sockets created after startup. Provider mode SHALL retain only one bootstrap-verified preconnected proxy data channel as an external Unix exception; offline SHALL retain none. A socket's presence in a permitted file mount SHALL NOT authorize its use.

#### Scenario: Host socket exists or arrives in a shared tree
- **WHEN** a host service exposes a stream, datagram, or seqpacket Unix socket in the workspace, worktree parent, shared state or isolated home before or after startup
- **THEN** agent connection and explicit-recipient send operations to it fail
- **AND** renaming, symlinking, hard-linking or using an alternate visible pathname does not authorize that service

#### Scenario: Proxy exception is a preconnected channel
- **WHEN** provider preparation connects to the verified session frontend before confinement
- **THEN** only that connected policy-filtered data channel survives into the confined relay
- **AND** new connections, socket replacement and channel death cannot broaden access or trigger unfiltered reconnection

#### Scenario: External abstract socket
- **WHEN** an agent attempts to create a Unix socket for an external abstract endpoint
- **THEN** creation is denied independently of pathname permissions or writable settings

### Requirement: Restricted local IPC compatibility
Restricted sessions SHALL deny new Unix listeners or unconnected Unix sockets even in private temporary directories. Own-loopback services, pipes and connected AF_UNIX stream/seqpacket socket pairs SHALL remain usable. Retargetable datagram/raw pairs SHALL be denied. Socket publication on host binds SHALL fail, while ordinary file persistence and baseline-permitted rename/link operations SHALL remain available.

#### Scenario: Named socket placement and aliases
- **WHEN** a process attempts named/abstract Unix listener or unconnected socket creation or socket placement into host file state
- **THEN** the operation fails, including in private temporary directories or through aliases
- **AND** binds overlapping reserved private runtime hierarchies are rejected

#### Scenario: Names on connected pairs
- **WHEN** an already connected stream/seqpacket pair binds or autobinds a private pathname or abstract name
- **THEN** the name is permitted only while the pair remains fixed to its original peer and cannot become a listener
- **AND** publication on a host workspace/state bind remains denied

#### Scenario: Fixed-peer local communication
- **WHEN** descendants use permitted connected pairs, pipes or own-loopback services
- **THEN** local communication works without authorizing any external Unix endpoint
- **AND** reconnect, disconnect, explicit-recipient sends and descriptor transfer cannot retarget permitted pairs to external services

#### Scenario: Ordinary files and incompatible daemons
- **WHEN** the session uses ordinary file/Git/worktree operations or a tool requiring a named Unix daemon
- **THEN** baseline-permitted file operations preserve caller ownership and persistence
- **AND** the named daemon fails with documented compatibility guidance rather than a policy bypass

### Requirement: Trusted bootstrap and descriptor hygiene
Restricted startup SHALL use a protected native bootstrap that establishes confinement before untrusted loaders, interpreters, environment hooks or settings execute. It SHALL close unrelated inherited descriptors and leave no unconfined agent-side supervisor. Only ordinary validated standard I/O and the provider relay's verified preconnected proxy data channel SHALL survive preparation. No other external connected socket, namespace handle or asynchronous I/O capability SHALL reach agent code.

#### Scenario: Early execution or descriptor injection
- **WHEN** image/workspace/state settings attempt pre-policy execution, an unexpected descriptor is inherited, or bootstrap identity/rule installation is invalid
- **THEN** startup rejects the condition or closes the unauthorized descriptor before any agent-controlled sentinel executes
- **AND** connected host sockets cannot bypass the policy through inherited handles, descriptor transfer, or asynchronous I/O paths

### Requirement: Full platform support requires transport evidence
Successful installation of both required enforcement layers SHALL be necessary but insufficient for declaring a platform supported. The release gate SHALL verify IP, Unix IPC and enabled alternate host-facing transports under the actual kernel, bootstrap, engine/backend and standard security policy. An uncontained or unassessable path SHALL keep restricted startup unavailable. Socket creation or absence of a listening peer SHALL NOT prove containment.

#### Scenario: Alternate host transport or incomplete evidence
- **WHEN** a platform exposes a non-IP transport such as AF_VSOCK or lacks controlled evidence for a required boundary
- **THEN** it remains unsupported until required denial is established with syscall tests and controlled positive controls
- **AND** the existing restricted-startup hold remains until the complete revised gate passes

### Requirement: Bounded multiplexed proxy data transport
Provider mode SHALL carry concurrent independently authorized tunnels over its sole preconnected channel using a protected versioned protocol. Stream, frame, queue and flow-control resources SHALL be bounded. Invalid protocol/state or channel failure SHALL fail closed without policy changes or descriptor transfer. Sequential requests SHALL NOT be limited to a finite preopened socket pool.

#### Scenario: Repeated and concurrent tunnels
- **WHEN** clients open concurrent tunnels or more sequential tunnels than the active concurrency limit
- **THEN** each logical connection independently passes authority, DNS and address checks
- **AND** TLS, streaming, supported WebSockets and backpressure operate within bounded resources

#### Scenario: Malformed transport and channel death
- **WHEN** clients send invalid versions, lengths, stream IDs, state transitions or credits, or the channel dies
- **THEN** affected operations fail closed with bounded sanitized diagnostics and no unfiltered reconnection
- **AND** the protocol exposes neither administration nor host descriptor transfer

### Requirement: Exact destination enforcement outside the agent
A trusted proxy outside agent control SHALL allow only normalized exact policy hostnames and approved ports, normally CONNECT on 443. It SHALL reject unapproved IP literals, wildcard/suffix matches, ambiguous authorities, unsafe ports, and unsupported proxy methods. TLS SHALL remain end-to-end without decryption or disabled certificate verification.

#### Scenario: Authority validation
- **WHEN** a client requests an approved exact hostname on its approved port
- **THEN** the proxy evaluates it for connection
- **AND** deceptive suffixes, userinfo, malformed authorities, unapproved ports, literals, and wildcard destinations are rejected

#### Scenario: Redirect or tunnel target changes
- **WHEN** an approved HTTPS response redirects the client to an unapproved hostname
- **THEN** a new connection to that hostname is denied
- **AND** documentation makes no claim to inspect encrypted paths, payloads, SNI mismatches, domain fronting, or provider-side forwarding inside an allowed tunnel

### Requirement: Trusted DNS and connection-time address validation
Only trusted infrastructure SHALL resolve approved upstream names. Each connection SHALL use an address validated against denied IPv4/IPv6 special, private, loopback, link-local, and metadata ranges without a second unchecked resolution. Restricted agents SHALL have no external DNS, UDP/QUIC, or alternate direct transport path.

#### Scenario: Rebinding and mixed address records
- **WHEN** an approved name resolves or changes to a forbidden IPv4/IPv6 address, including mapped IPv4 or a mixed public/private answer
- **THEN** the proxy refuses that connection without connecting to the forbidden address

#### Scenario: Arbitrary DNS and alternate transports
- **WHEN** a tool sends DNS queries, UDP, QUIC, or traffic to a resolver or unapproved HTTPS destination
- **THEN** the traffic cannot leave the restricted session
- **AND** necessary local name handling does not forward arbitrary agent-selected names upstream

### Requirement: Protected and versioned policy inputs
Policy and proxy configuration SHALL be outside all agent-writable mounts, with validated ownership, access, syntax, schema revision, profile, and required hosts. Only read-only policy inputs SHALL be exposed where needed. The agent SHALL have no proxy administration or policy-write authority. Revision and tested CLI/authentication versions SHALL be recorded.

#### Scenario: Unsafe policy or mount overlap
- **WHEN** policy input is malformed, untrusted, missing required hosts, or reachable through a writable workspace/state mount or escaped symlink
- **THEN** startup rejects it before the agent runs without repairing permissions or importing credentials

### Requirement: Narrow explicit exceptions
Any local-provider or optional-service exception SHALL be operator-approved and versioned with an exact destination and port. Local exceptions SHALL identify the approved address scope as well as hostname, and SHALL NOT exempt unrelated private ranges. Exceptions SHALL NOT appear automatically after failures.

#### Scenario: Local provider requested without approval
- **WHEN** an agent requests a LAN provider or a denied feature endpoint absent from the selected policy
- **THEN** access is denied with an actionable policy diagnostic and the policy remains unchanged

### Requirement: Client compatibility does not establish enforcement
Provider mode SHALL set consistent uppercase/lowercase HTTP/HTTPS proxy values and narrowly scoped loopback bypasses, clearing conflicting inherited and image defaults including alternate proxy variables. Unsetting or ignoring them SHALL NOT create a direct route. TLS trust SHALL preserve the existing single-file opt-in host CA contract.

#### Scenario: Client bypass and incompatible transport
- **WHEN** a command clears proxy variables, uses a wildcard bypass, or requires an unsupported transport
- **THEN** direct egress still fails and no automatic direct fallback or TLS relaxation occurs

#### Scenario: Host CA off and on
- **WHEN** provider mode runs with host CA trust unset and then enabled with `1`
- **THEN** the first run has no host CA mount or wrapper CA variables
- **AND** the second has only the read-only bundle at `/claude-home/ca/bundle.pem` and the four existing CA variables pointing there

### Requirement: Separate Claude authentication profiles
Provider mode SHALL require a named protected profile. `anthropic-api` SHALL allow only `api.anthropic.com:443` as its base destination; `anthropic-account` SHALL separately authorize the documented account hosts. SSO, optional features, third-party clouds, and gateways SHALL require distinct explicit additions or profiles with dated inventories.

#### Scenario: API and account inventories
- **WHEN** API authentication is selected
- **THEN** account login and unrelated development/feature hosts are denied
- **AND** an account profile can add `claude.ai`, `claude.com`, and `platform.claude.com` on 443, with SSO destinations only for its selected login method

#### Scenario: Account credentials without an API key
- **WHEN** provider mode selects the account profile with usable existing account credentials and no ANTHROPIC_API_KEY
- **THEN** the wrapper does not require an API key to start that account session
- **AND** the same outer destination and IPC restrictions apply

### Requirement: Optional traffic remains opt-in
Provider profiles SHALL disable unnecessary telemetry, updates, connectors, artifact/documentation lookups, and runtime plugin downloads using settings supported by the tested CLI. A missing supported disable control SHALL NOT broaden the allowlist. Shell and native permission-bypass modes SHALL retain the same outer restrictions.

#### Scenario: Optional feature attempts outbound access
- **WHEN** a disabled feature or writable setting attempts an unapproved download, connector, telemetry, or documentation request
- **THEN** the proxy denies it without adding vendor/CDN wildcards or shared storage domains

### Requirement: Session-owned egress resource lifecycle
Proxy resources, bootstrap/setup channels, transport endpoints, configuration, and local clients SHALL have unique recoverable session ownership. Setup failure SHALL stop launch and remove only owned resources. Cleanup SHALL share the launcher's bounded shutdown budget and preserve primary exit status. Proxy failure SHALL leave outbound attempts closed without changing mode.

#### Scenario: Concurrent sessions and setup interruption
- **WHEN** sessions with different policies start concurrently or setup is interrupted after resource creation
- **THEN** identities remain distinct and cleanup recovers and removes only the interrupted session's resources

#### Scenario: Bootstrap fails after proxy setup
- **WHEN** confinement or descriptor validation fails after creating the session proxy
- **THEN** no agent code runs, the failure status is preserved, and only owned proxy/setup resources are removed within the shared shutdown budget

#### Scenario: Proxy failure
- **WHEN** the proxy becomes unavailable during a provider session
- **THEN** subsequent outbound attempts fail and the agent receives no alternate network attachment

### Requirement: Redacted actionable diagnostics
Startup SHALL report mode, selected profile, and policy revision. Protected logs SHALL distinguish proxy unavailability, DNS failure, destination rejection, and provider authentication failure when observable. Denial records SHALL contain only bounded sanitized destination/port, session identity, and reason; credentials, token URLs, headers, bodies, and prompts SHALL NOT be logged.

#### Scenario: Malicious diagnostic input
- **WHEN** a rejected request includes userinfo, control characters, authorization data, or a token-bearing URL
- **THEN** logs omit secrets and untrusted raw request content and report a bounded reason without allowing log injection

### Requirement: Evidence and common contract documentation
Documentation SHALL map N01–N14 to implementation and acceptance, publish the portable mode/profile contract and sibling-wrapper parity status, and date/version endpoint inventories. Validation SHALL distinguish synthetic enforcement, real-rootless bypass checks, and authenticated provider compatibility. Untested checks SHALL remain unavailable.

#### Scenario: Provider profile readiness
- **WHEN** a profile is declared verified for a CLI/authentication version
- **THEN** evidence covers login, token refresh, streaming, long-lived requests, supported WebSockets, proxy/CA behavior, shell and native permission modes
- **AND** credential-free bypass tests separately cover DNS/UDP/IPv6, direct IP/ports, deceptive hosts, redirects, host/LAN/metadata, administration, concurrency, delegation rejection, failure closure, and cleanup
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
