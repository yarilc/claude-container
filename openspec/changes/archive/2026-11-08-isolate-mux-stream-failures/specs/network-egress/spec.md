# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
