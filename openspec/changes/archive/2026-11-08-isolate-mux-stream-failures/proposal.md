# Proposal

## Why

N23 remains reproducible after the idle-session fix: one missing CLOSE acknowledgement closes the shared channel after ten seconds, and temporary control-writer congestion can turn a full queue into a protocol error. Either event removes networking from otherwise healthy provider tunnels until the session restarts.

## What Changes

- Isolate stream cancellation, operation expiry and missing close acknowledgements from unrelated tunnels on the original channel.
- Replace immediate channel failure on control-queue saturation with bounded pressure handling; retain finite deadlines for genuine shared-transport stalls.
- Define bounded closing-state retention and legal late-frame handling without weakening frame, state, identifier or credit validation.
- Add deterministic fault/concurrency regressions and controlled production-path acceptance, including continued traffic and new tunnels after recoverable failures.
- Document resource-exhaustion behavior, unchanged fail-closed boundaries, measured results and protected-installation migration.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `network-egress`: Extend bounded multiplexed transport to isolate stream failures and recoverable control congestion, with explicit closing-state bounds and continued fail-closed channel behavior.

## Impact

Primary implementation areas are `network/mux.py`, relay/proxy lifecycle integration, `tests/test_mux.py`, and existing guard/network acceptance fixtures and runners. Documentation includes `network/README.md`, `docs/network-contract.md`, and `docs/validation.md`.

Both runtime and proxy images embed the transport implementation. Deployment must prepare matching protected code and immutable images and rerun local qualification; existing reports cannot authorize changed identities. Preserve the v1 wire format if the defined semantics remain compatible. No new dependencies, credentials, model requests, destinations, reconnect path, privilege additions or changes to offline/unrestricted behavior are planned. N21, N22, N24 and broader container-hardening work remain separate.
