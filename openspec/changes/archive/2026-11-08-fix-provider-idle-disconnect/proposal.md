# Proposal

## Why

Provider sessions can lose connectivity while Claude remains open: the shared multiplex receiver closes its sole preconnected channel after 300 seconds without a frame, causing the local relay to exit and subsequent requests to fail with `ECONNREFUSED`. Idle time at the prompt must not expire the session's only permitted outbound path.

## What Changes

- Keep an established multiplex channel available across arbitrary periods without incoming frames, including when no tunnels are open.
- Distinguish waiting for a new frame from receiving an incomplete frame; retain finite deadlines for incomplete frames, handshakes, writes, stream operations and tunnel lifetimes.
- Preserve fail-closed handling of EOF, invalid protocol, actual proxy loss and cancellation, without reconnecting or broadening network permissions.
- Add regression coverage for idle reuse, partial-frame deadlines, stream timeout isolation and relay lifecycle, plus credential-free production acceptance after more than 300 seconds of inactivity.
- Document timeout semantics, deployment prerequisites and measured validation separately from authenticated compatibility.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `network-egress`: Clarify that bounded multiplex transport permits an idle established session channel while incomplete frames and individual operations remain bounded.

## Impact

- Primary implementation: `network/mux.py`, shared by the runtime relay and trusted proxy; lifecycle verification in `network/relay.py` and `network/proxy.py`.
- Tests: multiplex component tests, relay lifecycle coverage and an opt-in production guard/relay/proxy idle acceptance fixture.
- Documentation: `network/README.md`, relevant network contract/setup guidance and `docs/validation.md`.
- Rollout requires rebuilding both images and installing matching protected code; existing qualification identities must be recomputed through the normal gate. Existing sessions need relaunching.
- No new dependencies, wire message types, policy exceptions, credentials or authenticated API calls are required.
