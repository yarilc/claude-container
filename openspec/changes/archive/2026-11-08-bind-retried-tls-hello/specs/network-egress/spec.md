## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Accurate provider identity documentation
Provider help, setup guidance, security documentation and the network contract SHALL distinguish CONNECT authorization, SNI binding of the initial and retried TLS 1.3 ClientHellos, and encrypted application routing. They SHALL state that matching SNI does not prove exclusive Anthropic communication or prevent encrypted Host changes, shared-service routing, provider-side forwarding or sending data to allowed services. They SHALL name uninspected TLS 1.2 renegotiation as an accepted limitation.

#### Scenario: Operator reviews provider guarantees
- **WHEN** an operator chooses or reads about provider mode
- **THEN** the effective initial and retried ClientHello guarantee and remaining application-level limits are visible
- **AND** ECH/GREASE and unsupported-client failures require explicit compatibility guidance without automatic policy relaxation

#### Scenario: Renegotiation limitation
- **WHEN** an operator reads the network contract or provider security documentation
- **THEN** TLS 1.2 renegotiation is identified as uninspected, with the reason and the absence of TLS decryption stated
