# Design

## Context

See `proposal.md` for motivation. `network/mux.py` is copied into both the Claude runtime and proxy images. Its receiver currently wraps the complete next-header read in `IDLE_TIMEOUT = 300`. On timeout it closes the channel; `relay.run()` then leaves its server context and the forked relay exits, while the parent has already executed Claude. The proxy deliberately rejects replacement channels.

A local component experiment using the actual relay and channel code, with the idle timeout reduced only in memory, reproduced listener availability followed by timeout-driven relay termination and `ConnectionRefusedError` (errno 111). This establishes the code defect, not the installed version or logs of the reported incident. Existing specs require bounded transport and fail-closed channel loss but do not explicitly distinguish quiet sessions from incomplete frames. The current network README groups idle operations under a 300-second limit; this change makes that distinction explicit.

## Goals / Non-Goals

**Goals:** Keep the original channel usable during quiet sessions while preserving bounded parsing, stream isolation, resource budgets and cancellation.

**Non-Goals:** Reconnection after actual channel loss, a relay supervisor, automatic restart, new liveness probes, new network permissions, broader authentication support, or changing the individual tunnel idle/lifetime policy. Authenticated model requests remain outside automated acceptance.

## Decisions

### Separate an idle frame boundary from an incomplete frame

After the existing bounded magic handshake, wait asynchronously for the first byte of the next frame without an idle deadline. Once that byte arrives, read the rest of the header and its validated payload under one absolute 10-second frame completion deadline. Validate kind and payload size before reading the payload. EOF before or during a frame remains channel loss; an incomplete frame timeout remains fail-closed. Partial progress must not reset the completion deadline.

This leaves one bounded read per channel while quiet, with no polling or accumulating tasks. It also prevents a peer from sending a partial header indefinitely. Existing payload reads already use 10 seconds; sharing that budget with header completion simplifies the incomplete-frame rule. The wire format and message types stay at mux v1.

Alternatives: raising the 300-second timeout merely delays failure; removing all receive deadlines permits stalled partial frames; heartbeat messages add protocol and scheduling complexity without a requirement for detecting a live but unresponsive local peer. The first-byte approach directly fixes idle expiration without those changes.

### Preserve operation bounds and lifecycle

Retain stream idle waits (300 seconds), write drains (30 seconds), magic handshake (10 seconds), OPEN replies (15 seconds), CLOSE acknowledgments (10 seconds), and tunnel lifetimes (12 hours). Name/document the frame completion budget separately so it cannot accidentally reuse the stream idle constant. Normal idle stream expiry must close only that stream; failure to acknowledge closure may still close the channel under the existing protocol rules.

Keep relay shutdown tied to genuine receiver termination. Preserve cancellation cleanup, pending-client wakeup, sanitized audit records and the proxy's single-channel admission rule. No automatic reconnect or unconfined supervisor is introduced. A peer that remains connected but stops responding is detected by finite request/write/close deadlines when work resumes, rather than by quiet time alone.

### Verify both transport semantics and the user-visible listener

Extend `tests/test_mux.py` with shortened test-only deadlines and generous outer watchdogs: idle before first OPEN and between sequential OPENs, stalled/fragmented headers and payloads, absolute deadlines despite trickled bytes, stream expiry followed by reuse, and EOF/cancellation during a quiet receive. Test both directions of the shared receiver. Add actual relay lifecycle coverage proving the loopback listener survives idle time and handles a new CONNECT; keep proxy authorization and TLS assertions in the appropriate existing fixtures.

Add a dedicated opt-in credential-free acceptance case using the production static guard, relay and proxy, controlled TLS endpoint and isolated policy. Complete a verified TLS request, close its tunnel, wait at least 305 seconds with no channel traffic, then complete another verified request in the same agent session. Include an initially idle case at component level. Keep production constants unmodified and assert that the session/channel was not replaced. Retain denied-destination, SNI mismatch/zero-byte and proxy-loss controls. Give only this slow case an explicit outer timeout sufficient for setup, idle and cleanup; do not add a five-minute wait to routine qualification or relax its bounded cancellation behavior.

## Risks / Trade-offs

- A connected but unresponsive idle peer is not proactively detected -> finite operation deadlines still bound work after resume; actual EOF/errors close the channel immediately.
- A stricter complete-frame budget can expose slow frame delivery -> test supported fragmentation and backpressure within the fixed 16 KiB data-frame cap and measure production acceptance; do not silently remove deadlines.
- Timing tests can be flaky -> coordinate readiness, use shortened test-only budgets with wide watchdog margins, and separate accelerated component evidence from the real 305-second production check.
- Updating only one image leaves an old receiver that still expires -> rebuild runtime and proxy together and install matching protected source before qualification.
- Existing tests may miss stream-close races revealed by idle expiry -> explicitly verify acknowledged stream closure, channel reuse and existing concurrency/backpressure suites.

## Migration Plan

1. Run component and wrapper regressions, then rebuild both images with the updated shared module using explicit maintenance consent.
2. Prepare a protected release through the existing setup workflow, resolve its immutable proxy image and rerun normal local qualification. Changed protected code/image identities invalidate prior reports; never bypass that check. The native guard ABI and mux wire identity do not change.
3. Run the opt-in idle acceptance case on an eligible rootless installation. Record environment, versions and passed/failed/unavailable results in `docs/validation.md`; distinguish production enforcement from component and authenticated evidence.
4. Relaunch sessions to adopt the fix. Existing sessions cannot repair their closed preconnected channel.
5. On regression, use the existing last-working-release rollback and qualification workflow; document that the prior release retains the idle defect.
