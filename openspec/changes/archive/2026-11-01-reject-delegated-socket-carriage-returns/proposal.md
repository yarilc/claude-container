# Proposal

## Why

Delegated-socket verification currently accepts CRLF responses and embedded carriage returns, retaining CR bytes in the reported host socket path. The remaining task in `todo.md` requires rejecting these malformed responses before they can reach image operations or container creation.

## What Changes

- Reject any CR byte in a successfully captured delegation verification response before parsing its fields or using its reported host path.
- Preserve acceptance of a valid response with no terminator or exactly one final LF, including host socket paths containing spaces.
- Preserve rejection of additional records and query failures, with endpoint-specific diagnostics before image operations or launch.
- Extend synthetic wrapper regression coverage and document the CR rejection in README and wrapper help.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-podman-access`: Tighten the single-record delegation verification contract to reject CR anywhere in the response while preserving valid record and socket-path handling.

## Impact

The implementation will affect `claude-container.sh`, `tests/test_wrapper.py`, README, and the delegation-response OpenSpec contract. Validation results will be recorded in `docs/validation.md`, and `todo.md` will be reconciled after the task passes verification. No new dependencies, image changes, or additional host mounts are required. The main spec will receive this change's delta through the normal sync or archive workflow.
