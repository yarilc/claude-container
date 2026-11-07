# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
Provider help, setup guidance, security documentation and the network contract SHALL distinguish CONNECT hostname/address authorization from initial TLS SNI binding and encrypted application routing. They SHALL state that matching SNI does not prove exclusive communication with Anthropic applications or prevent encrypted Host changes, shared-service routing, provider-side forwarding, or sending data to allowed services.

#### Scenario: Operator reviews provider guarantees
- **WHEN** an operator chooses or reads about provider mode
- **THEN** the effective initial ClientHello guarantee and remaining application-level limits are visible
- **AND** ECH/GREASE and unsupported-client failures require explicit compatibility guidance without automatic policy relaxation

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
