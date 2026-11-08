# Spec Delta

## MODIFIED Requirements

### Requirement: Bounded multiplexed proxy data transport
Provider mode SHALL carry concurrent independently authorized tunnels over its sole preconnected channel using a protected versioned protocol. Stream, frame, queue and flow-control resources SHALL be bounded. Invalid protocol/state or channel failure SHALL fail closed without policy changes or descriptor transfer. Sequential requests SHALL NOT be limited to a finite preopened socket pool. Absence of incoming frames SHALL NOT expire an established channel; incomplete frames and individual operations SHALL retain finite deadlines.

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
