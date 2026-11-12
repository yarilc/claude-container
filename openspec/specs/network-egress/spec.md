# network-egress Specification

## Purpose

Constrain network egress and external IPC independently of Claude and its tools, with operator-owned policies and evidence of real rootless enforcement.

## Requirements

### Requirement: Operator-selected runtime modes
The wrapper SHALL accept `CLAUDE_CONTAINER_NETWORK=offline|provider|unrestricted` from explicit operator configuration or validated managed preferences. An ordinary launch with an unset or empty effective mode SHALL stop with setup guidance before runtime preparation. Other values SHALL fail before image operations. Only explicit `unrestricted` SHALL remove the runtime destination boundary. Agent-writable configuration SHALL NOT select or broaden the outer policy.

#### Scenario: Default and invalid selection
- **WHEN** an ordinary invocation leaves the effective mode unset or empty
- **THEN** it receives missing-setup guidance rather than starting an implicitly offline session
- **AND** an unknown nonempty mode fails with the existing invalid-mode diagnostic without image operations or agent startup

#### Scenario: Policy cannot escalate itself
- **WHEN** workspace settings, application state, or commands request a broader policy or remove proxy variables
- **THEN** the running session retains its operator-selected outer boundary

#### Scenario: Explicit offline operation
- **WHEN** an operator explicitly chooses offline mode or a validated managed launcher supplies saved offline mode
- **THEN** the wrapper applies all existing restricted platform, protected-installation, guard and qualification requirements
- **AND** the resulting session cannot reach external services, including the Claude API

#### Scenario: Explicit provider or unrestricted operation
- **WHEN** an operator explicitly chooses provider or unrestricted mode, or the validated managed launcher supplies that saved choice
- **THEN** the mode retains its existing policy, authority, prerequisite and separate maintenance requirements
- **AND** failed restricted preparation never falls back to unrestricted networking

#### Scenario: Qualification is not an ordinary session
- **WHEN** the standalone fixed qualification operation is invoked with no effective network mode
- **THEN** its existing offline qualification default and protected-fixture checks remain available
- **AND** neither that operation nor its internal probe admits an arbitrary application command or bypasses enforcement

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
Successful installation of both enforcement layers SHALL be necessary but insufficient for restricted startup. A protected installation gate SHALL verify IP, Unix IPC and enabled alternate host-facing transports under the actual kernel, bootstrap, engine/backend and security policy. An uncontained or unassessable path SHALL keep startup unavailable. Local qualification SHALL NOT imply an exhaustively measured platform. Socket creation or absence of a listening peer SHALL NOT prove containment.

#### Scenario: Alternate host transport or incomplete evidence
- **WHEN** a platform exposes a non-IP transport such as AF_VSOCK or lacks controlled evidence for a required boundary
- **THEN** local qualification fails until required denial is established with syscall tests and controlled positive controls
- **AND** restricted startup remains unavailable until the installation gate passes; an unavailable required check is not a pass

#### Scenario: New combination qualifies locally
- **WHEN** an eligible native Linux or WSL2 installation passes every required local check but lacks full release acceptance for its combination
- **THEN** ordinary restricted startup can proceed with a visible locally-qualified, not-release-measured notice
- **AND** no exhaustive distribution matrix, authenticated-provider verification or SELinux/AppArmor compatibility guarantee is claimed

### Requirement: Bounded multiplexed proxy data transport
Provider mode SHALL carry concurrent independently authorized tunnels over its sole preconnected channel using a protected versioned protocol. Stream, frame, queue and flow-control resources SHALL be bounded. Invalid protocol/state or channel failure SHALL fail closed without policy changes or descriptor transfer. Sequential requests SHALL NOT be limited to a finite preopened socket pool. Absence of incoming frames SHALL NOT expire an established channel; incomplete frames and individual operations SHALL retain finite deadlines. Stream-local failures and recoverable control congestion SHALL preserve unrelated tunnels on a healthy channel.

#### Scenario: Repeated and concurrent tunnels
- **WHEN** clients open concurrent tunnels or more sequential tunnels than the active concurrency limit
- **THEN** each logical connection independently passes authority, DNS and address checks
- **AND** TLS, streaming, supported WebSockets and backpressure operate within bounded resources

#### Scenario: Malformed transport and channel death
- **WHEN** clients send invalid versions, lengths, stream IDs, state transitions or credits, or the channel dies
- **THEN** affected operations fail closed with bounded sanitized diagnostics and no unfiltered reconnection
- **AND** the protocol exposes neither administration nor host descriptor transfer

#### Scenario: Resume after an idle prompt
- **WHEN** a healthy provider session has no open tunnels and receives no transport frames for longer than 300 seconds
- **THEN** the local proxy listener and original preconnected channel remain available
- **AND** a subsequent approved TLS request succeeds through that same channel without restarting the session
- **AND** inactivity alone imposes no session expiration or periodic traffic requirement

#### Scenario: An idle tunnel expires independently
- **WHEN** an individual tunnel exceeds its idle operation deadline and its peer acknowledges closure normally
- **THEN** that tunnel releases its resources without closing the shared channel or other tunnels
- **AND** a new approved request can use the existing channel

#### Scenario: A partial frame stalls
- **WHEN** a peer starts a frame but does not complete its header and declared payload within the finite frame completion deadline
- **THEN** the channel closes and pending operations terminate
- **AND** incremental partial progress does not extend that deadline indefinitely

#### Scenario: Idle channel loses its peer or is cancelled
- **WHEN** an established channel waiting for a new frame receives EOF, a transport error or session cancellation
- **THEN** its receiver terminates and owned channel resources are released
- **AND** outbound access remains closed without a replacement connection or a broader network mode

#### Scenario: One stream fails while another carries traffic
- **WHEN** a tunnel is cancelled, fails an individual operation, or exceeds its close-acknowledgement deadline while the shared transport remains healthy
- **THEN** its application-facing operations terminate within finite lifecycle bounds
- **AND** another authorized tunnel continues exchanging data and the original relay listener remains usable
- **AND** a subsequent authorized tunnel succeeds on the same channel when stream capacity is available

### Requirement: Bounded stream closing state
Provider transport SHALL bound state retained for closing tunnels and validate legal late frames without delivering them to another tunnel. Missing close acknowledgement SHALL NOT alone close the shared channel. Exhausted closing-state capacity SHALL prevent further local admission without discarding validation state or disrupting established healthy tunnels.

#### Scenario: Acknowledgement arrives after local close expiry
- **WHEN** a locally closed tunnel receives a delayed acknowledgement after its caller has stopped waiting
- **THEN** the remaining closing state is released exactly once
- **AND** the channel remains usable and the released capacity can admit another authorized tunnel

#### Scenario: Data and response frames cross a local close
- **WHEN** valid in-flight data, an outstanding open response, credit or half-close arrives for a retained closing tunnel
- **THEN** the transport validates the frame against that tunnel's state and remaining credit
- **AND** discarded data is neither delivered to another tunnel nor granted fresh receive credit
- **AND** an invalid transition or credit violation still fails closed

#### Scenario: Repeated missing acknowledgements exhaust capacity
- **WHEN** unacknowledged closing tunnels reach the finite retention limit
- **THEN** further local tunnel admission fails within a finite bound without closing healthy established tunnels
- **AND** retained state, payload buffers, worker tasks and control work remain bounded independently of the number of attempted connections
- **AND** acknowledgement or channel teardown releases the corresponding retained state

#### Scenario: Retired or unknown identifiers receive frames
- **WHEN** a frame references a fully retired or never-issued tunnel identifier
- **THEN** only explicitly permitted idempotent terminal frames for known retired identifiers are tolerated
- **AND** identifiers are never reused and arbitrary late data is not silently accepted

### Requirement: Recoverable transport control pressure
Provider transport SHALL handle temporary control-queue saturation within fixed queue and task bounds without treating saturation alone as a protocol violation. Required closure controls SHALL NOT be silently dropped. A shared write that cannot complete within its finite transport deadline SHALL fail the channel closed.

#### Scenario: Closure burst exceeds immediately available control capacity
- **WHEN** valid stream closures temporarily fill the control queue and shared writes resume within the transport deadline
- **THEN** the channel preserves required controls and drains them within fixed resource bounds
- **AND** unrelated authorized traffic resumes and new authorized tunnels can use the original channel once capacity becomes available
- **AND** no replacement channel or unrestricted path is created

#### Scenario: Shared writer remains blocked
- **WHEN** required control or data writes cannot complete within the shared transport deadline
- **THEN** the channel closes and wakes affected operations within bounded cleanup time
- **AND** no policy relaxation or automatic reconnection occurs

#### Scenario: Cancellation during control pressure
- **WHEN** stream or session cancellation races with a full control queue, pending closure or writer shutdown
- **THEN** owned tasks and buffers are released without deadlock, double accounting or unbounded background work
- **AND** stream cancellation preserves a healthy shared channel while session cancellation closes it

### Requirement: Exact destination enforcement outside the agent
A trusted proxy outside agent control SHALL allow only normalized exact policy hostnames and approved ports, normally CONNECT on 443. It SHALL reject unapproved IP literals, wildcard/suffix matches, ambiguous authorities, unsafe ports, and unsupported proxy methods. TLS SHALL remain end-to-end without decryption or disabled certificate verification. Provider tunnels SHALL additionally satisfy mandatory initial TLS server-name binding before client bytes are forwarded upstream.

#### Scenario: Authority validation
- **WHEN** a client requests an approved exact hostname on its approved port
- **THEN** the proxy evaluates it for connection
- **AND** deceptive suffixes, userinfo, malformed authorities, unapproved ports, literals, and wildcard destinations are rejected

#### Scenario: Redirect or tunnel target changes
- **WHEN** an approved HTTPS response redirects the client to an unapproved hostname
- **THEN** a new connection to that hostname is denied
- **AND** a different initial TLS SNI inside an approved tunnel is rejected
- **AND** documentation makes no claim to inspect encrypted paths, payloads, HTTP Host or HTTP/2 authority, domain fronting using matching SNI, or provider-side forwarding

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
Provider mode SHALL require a named protected profile. `anthropic-api` SHALL allow only `api.anthropic.com:443` as its base destination; `anthropic-account` SHALL separately authorize only the measured account hosts needed inside the container. SSO, optional features, third-party clouds, and gateways SHALL require distinct explicit additions or profiles with dated inventories.

#### Scenario: API and account inventories
- **WHEN** API authentication is selected
- **THEN** account login and unrelated development/feature hosts are denied
- **AND** the account profile allows exactly `api.anthropic.com` and `platform.claude.com` on 443, with SSO destinations only for its selected login method

#### Scenario: Removed account hosts are denied
- **WHEN** an account-profile session opens a CONNECT tunnel to `claude.ai` or `claude.com`
- **THEN** the proxy denies it with a policy reason and records only the sanitized host, port and reason
- **AND** no policy is extended automatically

#### Scenario: Operator needs a removed host
- **WHEN** an operator needs `claude.ai` or `claude.com` in a session
- **THEN** that requires a separately named profile in an operator policy
- **AND** the exact base `anthropic-account` profile cannot be extended in place

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

### Requirement: Mandatory initial TLS server-name binding
Every provider tunnel SHALL validate the complete initial TLS ClientHello in the trusted proxy before forwarding any client bytes upstream. Exactly one unambiguous DNS server name SHALL normalize to the authorized CONNECT hostname. Inspection SHALL support TLS 1.2 and TLS 1.3 ClientHello encodings, preserve original bytes, and apply independently to every logical tunnel without agent-controlled bypasses.

#### Scenario: Matching names with certificate verification
- **WHEN** a valid supported ClientHello names the authorized CONNECT hostname, including permitted case and terminal-dot normalization
- **THEN** the original buffered bytes are forwarded once and the end-to-end TLS handshake can proceed
- **AND** the client still validates the upstream certificate using its configured trust store

#### Scenario: Shared-address server-name mismatch
- **WHEN** CONNECT authorizes one hostname but its ClientHello names a different hostname served at the same address
- **THEN** the trusted proxy rejects the tunnel before forwarding any client bytes upstream
- **AND** certificate validity for the different hostname does not authorize that tunnel

#### Scenario: Missing or ambiguous identity
- **WHEN** the ClientHello has missing, empty, duplicate, conflicting, malformed, non-DNS, or mismatched server-name information
- **THEN** the proxy rejects the tunnel without forwarding any client bytes upstream

#### Scenario: Non-TLS and unverifiable negotiation
- **WHEN** the initial payload is non-TLS, structurally invalid, offers only unsupported TLS versions, or contains an encrypted-client-hello extension including GREASE ECH
- **THEN** the proxy rejects the tunnel with no unchecked fallback or automatic interception
- **AND** an apparently matching outer SNI does not exempt ECH

#### Scenario: Agent bypasses the loopback relay
- **WHEN** agent-controlled code sends OPEN and DATA directly over the inherited multiplex channel
- **THEN** the trusted proxy applies the same ClientHello inspection and policy binding

### Requirement: Bounded TLS inspection across transport boundaries
TLS inspection SHALL reassemble the initial ClientHello across arbitrary supported TLS record and multiplex frame boundaries. The proxy SHALL enforce finite limits on wire bytes, decoded handshake size, record count, elapsed inspection time, and per-stream/session memory independently of untrusted lengths or progress. Failure SHALL release resources without unchecked forwarding or reconnecting.

#### Scenario: Fragmented and coalesced input
- **WHEN** a valid ClientHello is fragmented across records, frame headers, or DATA frames, or shares a transport chunk with subsequent TLS bytes
- **THEN** acceptance depends on the reconstructed ClientHello rather than delivery boundaries
- **AND** no client bytes are forwarded until validation succeeds, after which all consumed bytes retain their original order and contents

#### Scenario: Inspection exhaustion or premature end
- **WHEN** declared lengths are invalid, configured byte/record/memory limits are exceeded, input ends early, or the absolute inspection deadline expires despite incremental progress
- **THEN** the tunnel is rejected and buffered data is discarded
- **AND** unrelated valid streams continue within existing multiplex bounds

#### Scenario: Concurrent failures and channel death
- **WHEN** multiple tunnels await inspection and one tunnel fails or the channel closes
- **THEN** affected inspection tasks, buffers, and upstream connections are released within existing lifecycle bounds
- **AND** channel failure closes all affected tunnels without reconnecting or widening policy

### Requirement: Verified proxy destination-binding revision
Provider startup SHALL verify a protected expected destination-binding enforcement revision in addition to policy, bootstrap and multiplex identities. An old or incompatible proxy SHALL fail readiness before agent startup. The revision SHALL be mandatory for both bundled profiles and operator-defined provider profiles; writable settings SHALL NOT disable it.

#### Scenario: Old proxy image or mismatched readiness
- **WHEN** the selected immutable proxy image lacks the required destination-binding revision, reports another revision, or receives an incompatible protected manifest
- **THEN** provider preparation fails before agent execution and cleans up only owned resources
- **AND** no unchecked proxy or unrestricted network is substituted

### Requirement: Redacted TLS binding rejection diagnostics
Protected denial logs SHALL distinguish TLS identity rejection, malformed or unsupported negotiation, ECH rejection, inspection overflow, and inspection timeout using bounded reason codes and the authorized destination. They SHALL NOT record raw ClientHello data, rejected raw SNI, HTTP headers, credentials, URLs, payloads, or prompts.

#### Scenario: Malicious or sensitive ClientHello contents
- **WHEN** rejected TLS input contains secret-like strings, control characters, or excessive lengths
- **THEN** logs contain only the normalized authorized host/port, session identity, timestamp and bounded reason
- **AND** diagnostic processing does not allocate from unchecked lengths or inject log records

### Requirement: Accurate provider identity documentation
Provider help, setup guidance, security documentation and the network contract SHALL distinguish CONNECT authorization, SNI binding of the initial and retried TLS 1.3 ClientHellos, and encrypted application routing. They SHALL state that matching SNI does not prove exclusive Anthropic communication or prevent encrypted Host changes, shared-service routing, provider-side forwarding or sending data to allowed services. They SHALL name uninspected TLS 1.2 renegotiation as an accepted limitation.

#### Scenario: Operator reviews provider guarantees
- **WHEN** an operator chooses or reads about provider mode
- **THEN** the effective initial and retried ClientHello guarantee and remaining application-level limits are visible
- **AND** ECH/GREASE and unsupported-client failures require explicit compatibility guidance without automatic policy relaxation

#### Scenario: Renegotiation limitation
- **WHEN** an operator reads the network contract or provider security documentation
- **THEN** TLS 1.2 renegotiation is identified as uninspected, with the reason and the absence of TLS decryption stated

### Requirement: Destination-binding acceptance evidence
Closing N15–N17 SHALL require tracked documentation and controlled positive/negative destination-binding evidence through the production guard, relay and proxy on the supported WSL ABI-3 target. Parser tests and historical transport passes SHALL remain separate from production acceptance. Real authenticated checks SHALL require separate authorization, and unavailable checks SHALL be labeled unavailable.

#### Scenario: Controlled shared-address regression
- **WHEN** acceptance exercises two controlled TLS hostnames at one address with certificates valid for the respective names
- **THEN** matching CONNECT/SNI succeeds with certificate verification and the authorized-CONNECT/different-SNI case fails before client bytes reach the upstream
- **AND** a controlled unfiltered positive control demonstrates that the alternate hostname is otherwise reachable at that address

#### Scenario: Regression and compatibility matrix
- **WHEN** the change is assessed for completion
- **THEN** evidence covers malformed/missing/duplicate/conflicting SNI, non-TLS, ECH, fragmentation, inspection limits/deadlines, concurrency, direct multiplex use, channel/proxy failure, and old-proxy rejection
- **AND** controlled TLS/streaming tests cover both API and account inventories, bad-certificate rejection, CA off/on, and existing long-lived/WebSocket transport
- **AND** current real authentication results are distinguished from historical evidence and synthetic compatibility without accessing real credentials automatically

#### Scenario: Historical observation provenance
- **WHEN** documentation records the 2026-11-07 approved Anthropic CONNECT followed by Cloudflare SNI and HTTP 403
- **THEN** it identifies the observation as reported historical evidence and records available versions and reproduction details without inventing missing metadata
- **AND** it distinguishes that observation from new controlled regression results and makes no claim of arbitrary application-content access

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

#### Scenario: Host kernel without IPv6
- **WHEN** the engine host has no IPv6 support, observed as a missing `/proc/sys/net/ipv6` and `EAFNOSUPPORT` on `AF_INET6` socket creation
- **THEN** the gate uses an IPv4-only positive-control network and peer
- **AND** the IPv6 denial is evidenced by `EAFNOSUPPORT` on `AF_INET6` socket creation in both the unconfined control and the guarded probe
- **AND** every other required check, including the IPv4 positive controls and denials, runs unchanged

#### Scenario: Inconsistent IPv6 evidence
- **WHEN** the detected IPv6 state is neither clearly present nor clearly absent, or the fixture network, peer addresses, control or guarded probe contradict it
- **THEN** qualification fails without a report and without falling back to the other path

#### Scenario: IPv6 state is bound to the report
- **WHEN** a report was issued for one IPv6 state and the host later runs with the other state
- **THEN** the report is stale and restricted startup requires requalification

### Requirement: Session proxies have enforced resource budgets
Each Internet-facing session proxy SHALL have a limit of 128 processes and 256 MiB memory, enforced by the engine and host cgroups, for each budget whose cgroup v2 controller (`pids`, `memory`) the verified rootless engine reports as available. Startup SHALL fail before agent execution if an enforced limit is not applied, or if an unenforced limit is unexpectedly present. These budgets SHALL coexist with existing multiplex, TLS inspection and lifecycle bounds without broadening runtime access.

#### Scenario: Proxy readiness with applied limits
- **WHEN** a provider session prepares its proxy on an engine reporting the `pids` and `memory` controllers
- **THEN** both configured budgets are verified as effective before the agent starts
- **AND** matching-SNI TLS, streaming, concurrent tunnels, readiness and protected logs operate within the budgets

#### Scenario: Rootless resource control unavailable
- **WHEN** the engine rejects or silently ignores a limit whose controller it reports as available, or its effective value cannot be established
- **THEN** provider preparation fails and cleans up only owned resources
- **AND** it never substitutes an unrestricted connection

#### Scenario: Controller not delegated for the proxy
- **WHEN** the verified engine does not report the `memory` controller
- **THEN** the proxy is created without a memory limit, and its process limit is still applied and verified when `pids` is reported
- **AND** the session prints a notice naming the unenforced proxy budget

#### Scenario: Proxy exceeds a resource budget
- **WHEN** a proxy reaches its process or memory budget or is terminated because of exhaustion
- **THEN** affected outbound operations fail closed
- **AND** cleanup preserves the primary application/signal status and bounded shutdown contract
- **AND** other sessions retain their independent proxy resources and budgets

### Requirement: Single protected agent profile
All agent-specific values used by the shared network sandbox and setup components SHALL come from one data-only agent profile and its provider policy file. Examples are wrapper and variable names, images, labels, installation and state names, native configuration and credential variables, authentication assistance and policy profiles. The profile SHALL be schema-validated, trusted-path checked and outside agent-writable mounts.

#### Scenario: Invalid or unprotected profile
- **WHEN** the profile is missing, malformed, has duplicate or unknown keys, fails field validation, or is reachable through a writable workspace or state mount or an escaped symlink
- **THEN** setup, qualification and restricted startup fail before the agent runs, identify the profile, and do not fall back to built-in defaults

#### Scenario: Profile not taken from the workspace
- **WHEN** the current workspace contains a file with the profile's name or layout
- **THEN** the wrapper uses only the profile in its protected installation or checkout and ignores the workspace copy

### Requirement: Profile-bound restricted identity
The agent profile and its provider policy file SHALL be part of the protected code identity recorded in local qualification reports. Any change to either SHALL invalidate matching qualification evidence.

#### Scenario: Profile changed after qualification
- **WHEN** the installed profile or provider policy differs from the one recorded in the current qualification report
- **THEN** ordinary restricted launches are refused with setup or requalification guidance

### Requirement: Agent-neutral shared sandbox components
The shared network sandbox and setup components, including the compiled guard, SHALL contain no agent-specific identifiers. In-container paths, the guard binary name and the multiplex protocol marker SHALL be agent-neutral. Host-visible images, labels, variables and installation paths SHALL stay per-agent, as declared by the profile.

#### Scenario: Shared components contain an agent identifier
- **WHEN** a shared network or setup file contains an agent-specific identifier declared by the profile, outside the documented allow-list
- **THEN** the alignment test fails

#### Scenario: Two wrappers on the same host
- **WHEN** two wrappers using different profiles run restricted sessions or qualification concurrently
- **THEN** each creates, inspects and cleans up only resources carrying its own profile's labels and image names

#### Scenario: Unchanged operator interface
- **WHEN** an existing user runs the wrapper with the same environment variables, images and saved setup preferences after requalification
- **THEN** modes, profiles, hosts, defaults, hardening and diagnostics behave as before the change

### Requirement: Shared restricted session interface
Restricted-session preparation, proxy lifecycle, restricted container arguments and proxy cleanup SHALL be provided by one shared, profile-driven component. Wrappers SHALL invoke it through fixed operations with explicit inputs and outputs. They SHALL NOT re-implement these steps. Its cleanup SHALL use only the remaining launcher shutdown budget and SHALL NOT change the primary exit status.

#### Scenario: Wrapper integration
- **WHEN** a wrapper starts an offline or provider session
- **THEN** preflight, the guard probe, proxy creation, readiness, hardening verification, guard and relay arguments, and proxy cleanup come from the shared component
- **AND** the wrapper adds only agent-specific command, environment, state and credential options

#### Scenario: Interrupted proxy start
- **WHEN** a signal arrives while the shared component is creating or verifying the proxy
- **THEN** the wrapper terminates that operation, then recovers and removes only the proxy owned by this session within the remaining shutdown budget
- **AND** no agent container is created and the signal status is returned

#### Scenario: Stalled proxy cleanup
- **WHEN** proxy recovery or removal stalls during shutdown
- **THEN** each engine call is bounded by the remaining budget
- **AND** the unconfirmed resource is reported without replacing the primary exit status

#### Scenario: Arguments with special characters
- **WHEN** the agent command or its arguments contain spaces, quotes or newlines
- **THEN** the shared component returns them unchanged as separate arguments

### Requirement: Retried TLS 1.3 ClientHello binding
After a TLS 1.3 HelloRetryRequest, the trusted proxy SHALL validate the second ClientHello under the same rules as the initial one and SHALL require it to name the same authorized host before forwarding it. Client bytes after the initial ClientHello SHALL be held until the upstream's first handshake message shows whether a retry occurred. Without a retry, the tunnel SHALL continue opaquely.

#### Scenario: Retry with the same server name
- **WHEN** the upstream answers the initial ClientHello with a HelloRetryRequest and the client sends a second ClientHello naming the authorized host, optionally preceded by compatibility ChangeCipherSpec or early-data records
- **THEN** the held and validated bytes are forwarded once in their original order
- **AND** the TLS 1.3 handshake can complete with certificate verification

#### Scenario: Retry with a different server name
- **WHEN** the second ClientHello after a HelloRetryRequest names a different host, lacks a server name, carries ECH, or is malformed
- **THEN** the proxy rejects the tunnel before any byte of the second ClientHello reaches the upstream
- **AND** the protected denial log records a bounded reason and the authorized destination only

#### Scenario: Second ClientHello sent before the retry
- **WHEN** the client sends additional handshake bytes, including a second ClientHello, before the upstream's first handshake message has been observed
- **THEN** those bytes are held and are forwarded only after the proxy observes no HelloRetryRequest, or after they validate as the retried ClientHello

#### Scenario: No retry
- **WHEN** the upstream's first handshake message is an ordinary ServerHello, or the upstream sends non-handshake data
- **THEN** any held client bytes are forwarded unchanged and the tunnel continues opaquely, including TLS 1.2 flights and encrypted records

#### Scenario: Retry inspection exhaustion
- **WHEN** the held bytes exceed the inspection limits, the input ends early, or no upstream decision or valid second ClientHello arrives before the inspection deadline
- **THEN** the tunnel is rejected and the held data is discarded without unchecked forwarding
- **AND** unrelated streams continue within existing multiplex bounds

### Requirement: Single-source enforcement revisions
The guard revision, the required Landlock ABI and the destination-binding enforcement revision SHALL each be defined once for the protected Python components that write, validate or report them. Automated tests SHALL fail when the compiled guard's declared revision or its version output differs from that definition. A change to the destination-binding behavior SHALL change its enforcement revision, so that older proxies fail readiness.

#### Scenario: Revision drift
- **WHEN** the guard source, the session manifest writer, the proxy validator or the session readiness check would use different revision values
- **THEN** the test suites fail before release

#### Scenario: Old proxy after the retry binding
- **WHEN** a proxy image built before the retried ClientHello binding is used with an updated installation
- **THEN** provider readiness fails before agent execution and requires setup and requalification

### Requirement: Actionable host guard probe diagnostics
Host-side guard probes run by restricted-session preparation and qualification SHALL NOT depend on the caller's standard output or error being a terminal, file, pipe or null device. A failed probe SHALL report an actionable message that names the probe and its exit status, without weakening the guard's own descriptor validation inside the sandbox.

#### Scenario: Caller output is a socket
- **WHEN** preparation or qualification runs with standard output or error attached to a socket, for example under journald
- **THEN** the probe result is captured and relayed, and preparation proceeds as it would from a terminal

#### Scenario: Probe failure
- **WHEN** the guard probe exits with a nonzero status
- **THEN** the caller stops with a message that names the guard probe, its status and the Landlock ABI or standard I/O requirement, instead of failing without output

### Requirement: Residual exfiltration disclosure
Provider help, setup guidance, README and the network contract SHALL state that destination and SNI binding cannot distinguish the operator's credentials from attacker-supplied ones. Each allowed host can therefore receive workspace data sent with a foreign API key or account. The documentation SHALL name the hosts of each base profile and SHALL NOT present the disclosure or the host reduction as preventing this channel.

#### Scenario: Operator reads the provider limits
- **WHEN** an operator reads the provider help, README or network contract
- **THEN** the foreign-credential channel is described for `api.anthropic.com` and every other allowed host of the selected profile
- **AND** the text states that only offline mode removes the channel

### Requirement: Credential-injecting interception remains unimplemented
The network contract SHALL describe credential-injecting TLS interception as a separately evaluated option only. In that option the proxy holds the credentials and the agent never sees them. The contract SHALL state that it conflicts with the no-decryption guarantee, and that it requires an explicit operator decision and its own change before implementation. The proxy SHALL NOT decrypt, terminate or re-sign provider TLS.

#### Scenario: Interception is reviewed
- **WHEN** an operator reads the network contract
- **THEN** the option, its trade-offs (TLS termination, a local CA, credential custody and a larger trusted proxy) and its unimplemented status are stated
- **AND** provider tunnels still forward TLS end-to-end without decryption

### Requirement: Authenticated account-profile reduction evidence
An account-profile host reduction SHALL count as accepted only after operator-run checks pass through the restricted wrapper. These are a fresh isolated login, an ordinary request and a refresh after expiry, with the narrowed profile and no other change. The sanitized denial records SHALL be reviewed. Automated tests SHALL NOT use real credentials.

#### Scenario: Narrowed profile passes
- **WHEN** login, an ordinary request and a refresh succeed under the narrowed profile with no denial of an Anthropic host
- **THEN** the validation record stores the CLI version, policy revision, results and the absence of denials, without credentials, URLs or bodies

#### Scenario: Narrowed profile fails
- **WHEN** any check fails or a denial names a removed host
- **THEN** the measured denials are recorded
- **AND** the account profile is restored to its previous host set under a new revision instead of being broadened automatically at runtime

### Requirement: Provider upstream connection tolerates unsupported address families
When an approved name resolves to several validated addresses, the provider proxy SHALL skip any address whose family the kernel does not support and try the next one. It SHALL never connect to an unvalidated address or resolve the name a second time. When no address yields a connection, it SHALL reject the tunnel.

#### Scenario: AAAA records on a kernel without IPv6
- **WHEN** an approved host resolves to IPv6 and IPv4 public addresses and the proxy runs on a kernel without IPv6
- **THEN** the proxy connects through a validated IPv4 address
- **AND** the IPv6 addresses do not abort the tunnel

#### Scenario: Only unsupported families
- **WHEN** every validated address has a family the kernel does not support
- **THEN** the tunnel is rejected as upstream-unavailable before any client bytes are forwarded

### Requirement: Private runtime hierarchies admit only verified read-only masks
Before agent code runs, the restricted bootstrap SHALL reject every nested mount below `/tmp`, `/run` and `/var/tmp`, except the engine metadata file `/run/.containerenv`, the provider runtime `/run/sandbox-egress` and `/run/secrets` when it is a `tmpfs` whose per-mount options are read-only. A writable or non-tmpfs `/run/secrets` SHALL be rejected like any other nested mount.

#### Scenario: Read-only secrets mask
- **WHEN** a restricted session starts with the read-only tmpfs mask at `/run/secrets`
- **THEN** the bootstrap accepts the layout and the agent starts

#### Scenario: Writable secrets mount
- **WHEN** `/run/secrets` is a writable mount, for example the engine default without the mask
- **THEN** startup stops with the nested private IPC mount diagnostic before agent code runs

#### Scenario: Other nested mount
- **WHEN** any other host or tmpfs mount appears below `/tmp`, `/run` or `/var/tmp`, read-only or not
- **THEN** startup stops before agent code runs

### Requirement: Qualification containers do not depend on the image working directory
Every container that local enforcement qualification starts from the runtime image SHALL set its working directory to `/` explicitly. This covers the gate's certificate, control and peer containers and the security-identity probe. The engine SHALL therefore never create or change the ownership of an image working directory for these containers, whatever `WORKDIR` the runtime image declares.

#### Scenario: Runtime image with a WORKDIR missing from its layers
- **WHEN** a wrapper's runtime image declares `WORKDIR /workspace` without creating it in a build step, and qualification runs
- **THEN** the qualification containers start in `/` and the engine does not create `/workspace` in them

#### Scenario: Host with a domain UID under keep-id
- **WHEN** qualification runs as a caller whose UID cannot be used for an engine-side chown under `--userns=keep-id`
- **THEN** no qualification container fails on a working-directory chown

#### Scenario: Probe behavior unchanged
- **WHEN** the control probe, peer and security probe run in `/`
- **THEN** they reach their fixtures by absolute paths and produce the same evidence as before
