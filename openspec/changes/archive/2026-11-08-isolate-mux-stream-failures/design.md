# Design

## Context

See `proposal.md` for motivation. `network/mux.py` is shared by the confined relay and trusted proxy and is copied into both images. The current v1 protocol supports 64 active streams, 16 KiB DATA frames, a 256 KiB per-stream receive window and a 64-entry control queue. The receiver tolerates only CLOSE and WINDOW_UPDATE for known fully retired IDs. Quiet channels have no inactivity expiry; partial frames have an absolute ten-second completion deadline.

`Stream.close()` currently closes the channel when its ten-second acknowledgement wait expires. Receiving CLOSE uses immediate control enqueue and translates queue saturation into `ProtocolError`. The relay listener runs only while the original channel survives. Existing tests cover normal closure, idle expiry with acknowledgement, stream backpressure and malformed traffic, but not these two escalation paths.

Exploration on 2026-11-08 reproduced a missing acknowledgement closing an unrelated working stream after 10.02 seconds. A separate socket-pair experiment held the control writer and sent 66 sequential OPEN/CLOSE pairs; one control was in flight and 64 queued when the channel closed. These are instrumented component observations, not production-frequency measurements or completed acceptance evidence.

## Goals / Non-Goals

**Goals:**
- Make application-facing stream teardown finite and independent of acknowledgement latency.
- Preserve enough bounded state to validate in-flight frames after local cancellation.
- Absorb temporary control pressure without queue growth, task proliferation or immediate channel failure.
- Distinguish recoverable stream failures from shared transport failure using observable progress and existing finite deadlines.

**Non-Goals:**
- Recover a dead channel, open another external socket, relax TLS/policy checks or guarantee availability against a malicious peer.
- Change destination inventories, TLS inspection scope, container budgets, platform eligibility or the v1 frame format.
- Add authenticated traffic, model requests or production fault-injection switches.

## Decisions

### 1. Separate caller completion from wire retirement

Use explicit logical phases: active, locally closing, abandoned waiting for acknowledgement, and fully retired. A close sends or schedules exactly one required CLOSE, releases payload buffers and application/upstream ownership, wakes local waiters, and waits at most the existing ten seconds for acknowledgement. Expiry completes the caller's close without calling channel teardown. Concurrent close calls and cancellation share the same terminal transition rather than starting independent close tasks.

Retain compact validation state until remote CLOSE or channel teardown. It includes identity, whether an open response is outstanding, EOF/response flags and remaining send/receive credit; it retains no application payload or running tunnel worker. Count locally closing and abandoned entries against the existing 64-stream admission budget. A permanently missing acknowledgement therefore consumes a bounded slot. When that budget is exhausted, reject further local opens promptly while preserving established streams. Peer OPEN beyond the protocol's outstanding-stream limit remains invalid. No timer evicts a still-needed validation record merely to admit another stream.

Alternative: deleting the stream immediately makes legitimate in-flight DATA appear to reference an unknown ID. An unlimited tombstone history leaks resources; reusing IDs risks cross-stream delivery. Keeping compact bounded state preserves validation at the cost of reduced capacity when a peer never acknowledges.

### 2. Validate crossing frames, then discard closed-stream payload

For a retained closing entry, accept an otherwise legal outstanding OPEN response, DATA, HALF_CLOSE, WINDOW_UPDATE or CLOSE only according to the existing direction/state/credit rules. Discard valid DATA and debit its remaining receive credit without returning new receive credit. Record response/EOF transitions, reject duplicates and over-credit traffic, and never deliver data to another stream. A remote CLOSE releases the retained entry exactly once.

After full retirement, keep the existing monotonic-ID rule and narrowly permitted idempotent CLOSE/WINDOW_UPDATE behavior; arbitrary retired DATA, reused IDs and never-issued IDs remain errors. Channel-wide byte accounting must subtract cleared buffers exactly once, including close/cancel/remote-close races.

Alternative: ignoring every frame for a closed identifier would conceal actual protocol violations and permit unbounded sender credit.

### 3. Apply bounded backpressure to control production

Keep a fixed control queue and one channel-owned sender. When enqueue cannot complete immediately, apply bounded waiting rather than raising `ProtocolError` or creating a task per pending control. Move any wait outside the stream condition lock. Required CLOSE controls must survive cancellation of the initiating application task; distinguish scheduled and actually transmitted closure internally where necessary.

Cover queue admission, writer-lock acquisition and drain with finite shared-write progress budgets based on the existing 30-second write deadline. A temporary queue wait ends when the writer drains; sustained inability to write is a shared transport failure and closes the channel. Do not reset an absolute pending-write budget on repeated retries. The ten-second partial-frame deadline still covers only reading an incomplete frame, not waiting after a complete valid frame for bounded control capacity.

This can briefly delay receiver dispatch during heavy pressure. Acceptance must show recovery and continued unrelated traffic after pressure is released before the deadline. It does not promise independent progress over a physically blocked shared descriptor. Fair writer scheduling and bounded cancellation must prevent lock cycles between receiver, sender and stream workers.

Alternatives: enlarging the queue postpones the same failure; dropping CLOSE loses retirement correctness; unbounded enqueue tasks move exhaustion outside the queue. Permanent write stalls must still close the channel rather than pretending a failed transport is healthy.

### 4. Preserve channel-level enforcement failures

Invalid frames, impossible stream states, malformed credits, partial-frame expiry, EOF and actual write failure still close the channel and wake all waiters. All outbound frame paths must apply the same shared-write failure policy. Local operation expiry, ordinary cancellation and missing acknowledgement do not invoke that policy by themselves. Integration must always close local sockets and release relay active counts even if stream teardown is cancelled or fails.

No new frame types or wire-version change are planned: CLOSE remains the terminal handshake. Both images and protected installed code must be updated together; a wire-format revision would require revisiting readiness identities before implementation continues.

### 5. Separate deterministic fault evidence from production acceptance

Add component tests in `tests/test_mux.py` using raw peers and bounded transport gates to withhold/delay ACK, pause/resume control writes, and exercise both endpoint roles. Assert resource counts and successful traffic on the original channel, not merely absence of exceptions. Include at least one real ten-second close deadline; shortened component deadlines may cover the larger race matrix.

Extend the existing guard/network harness with controlled TLS endpoints and a test-owned transport fault boundary. Exercise the actual production guard, relay and proxy code without modifying shipped enforcement or adding application-command exceptions. Cover an unrelated live tunnel and a subsequent approved TLS connection, plus denied authority, mismatched-SNI zero-byte rejection and actual channel-loss controls. Keep component instrumentation results separate from acceptance with unmodified production code. Recheck protected installation qualification and setup rollback using newly built images.

## Risks / Trade-offs

- Permanent missing ACK reduces available capacity -> retain at most 64 outstanding stream records; reject new local opens at exhaustion and release slots on acknowledgement.
- Queue waits can expose lock/cancellation cycles -> no queue wait under a stream lock; finite total write budgets and cancellation-race tests.
- Discarding closed-stream bytes can hide credit errors -> validate before discard and grant no new receive credit.
- A test-only fault boundary can overstate evidence -> identify the injected condition and measured path; never describe shortened or patched component checks as unmodified runtime acceptance.
- Old installed images keep the original defect -> deploy both images and protected code together and require matching qualification.

## Migration Plan

1. Prepare candidate runtime and immutable proxy images with the revised shared transport under explicit maintenance authorization.
2. Run component, production-path and protected-installation acceptance; record versions, image/code identities, actual outcomes and unavailable checks in `docs/validation.md`.
3. Rerun setup or manual protected qualification. Existing code/image fingerprints must invalidate stale reports; retain the last working activation until candidate qualification succeeds.
4. Use the candidate for new sessions. Existing running sessions continue with their original code and need a restart to gain the fix.
5. Roll back through the last working protected release and its matching images/report, requalifying when current identities require it. No network-mode fallback is allowed.
