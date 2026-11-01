# Design

## Context

See `proposal.md` for motivation. The wrapper's `capture_response` helper preserves final LF bytes and the Podman command's exit status. Delegation validation then removes one optional LF, rejects remaining LF bytes, and uses `read -r` to split the rootless result from the reported host path. CR is neither removed nor rejected, so a CRLF terminator or a CR embedded in the path can survive into the socket bind source.

The existing synthetic Podman fixture supports exact response bytes through `FAKE_SOCKET_RAW` and query failures through `FAKE_SOCKET_STATUS`. Its operation log already supports assertions that verification gates image inspection, explicit builds, and container creation. This design is included because the change hardens a security-sensitive verification boundary.

## Goals / Non-Goals

**Goals:**
- Validate the captured delegation response before interpreting any fields.
- Keep valid path bytes, including spaces, intact and retain the existing query-error precedence.
- Prove early rejection through observable Podman calls using the existing test fixture.

**Non-Goals:**
- Refactor response capture or change launch-engine verification.
- Normalize CRLF, broaden supported transports, or change endpoint precedence, state modes, mounts, or lifecycle behavior.

## Decisions

### Reject CR directly in the captured delegation response

Add a Bash pattern check immediately after successful socket-response capture and before optional final-LF handling and `read`. Reuse the existing invalid-socket-response diagnostic, which names the selected endpoint. Rejecting the full captured value catches CR in any position, including outside the eventual path field.

Stripping CR or converting CRLF would silently accept malformed protocol output and could change a reported path. Checking only the parsed path would miss CR elsewhere in the response. Changing the shared capture helper would unnecessarily affect launch-engine verification and obscure the distinction between query failure and invalid output.

### Preserve record parsing and failure precedence

Leave the capture helper, optional single-LF removal, extra-record rejection, and field splitting in place. A nonzero query must continue to take the existing query-failure branch even if stdout contains CR. Retaining the two-field `read -r` assignment and quoted mount argument preserves accepted host paths containing spaces.

### Extend behavior tests at the existing verification boundary

Use the current exact-response fixture to cover CRLF, a final CR without LF, leading CR, CR in the rootless field, between fields, and inside the path. Run rejection cases with both ordinary startup and `--container-build`; assert nonzero status, an endpoint-specific invalid-response diagnostic, and no `image`, `build`, or `create` calls. Retain positive checks for zero/one final LF and exact mount arguments for a path containing spaces, existing extra-record checks, and query-failure checks. Include malformed stdout with a nonzero query status to confirm query-error precedence, and confirm disabled delegation skips the separate query.

README and wrapper help will explicitly describe CR rejection for delegated responses. The change delta updates the existing delegation-response requirement; main-spec synchronization remains part of the normal sync or archive workflow.

## Risks / Trade-offs

- A service emitting CRLF will now fail startup → This is the intended compatibility tightening; the diagnostic identifies the endpoint, and documentation states the accepted format.
- A broad parsing change could damage paths containing spaces or hide query errors → Keep the parser and capture helper intact and retain exact-path and failure-precedence assertions.
- Synthetic tests do not exercise a live Podman service → They directly control the malformed bytes a normal service would not emit; run applicable rootless runtime checks when available and record unavailable checks honestly.

## Migration Plan

Ship the guard, regression tests, and documentation together. No state or image migration is required. After verification, record results in `docs/validation.md` and mark the remaining `todo.md` item complete. Reverting the guard restores prior response acceptance without changing persistent state.
