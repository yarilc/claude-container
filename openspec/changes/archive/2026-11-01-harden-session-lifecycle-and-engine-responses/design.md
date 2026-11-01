# Design

## Context

See `proposal.md` for motivation. Both verification queries use ordinary command substitution, which removes every trailing LF before validation. Lifecycle traps are installed before creation, but a foreground command substitution assigns the container ID only after `podman create` returns. The attached client is already backgrounded with explicit stdin forwarding. Signal handling calls Podman and `wait` without bounds; EXIT cleanup hides removal failures.

Existing tests cover cooperative signals, collisions, concurrent sessions, and application exit 125, but the fake client always responds to termination. Host coreutils and Podman's `--cidfile` are available in the inspected environment. The current user edit to `.gitignore` is unrelated and must remain untouched.

## Goals / Non-Goals

**Goals:** Make shutdown finite, ownership recoverable during creation, error reporting truthful, and verification boundaries observable. Reuse Bash, host coreutils, and the existing synthetic/rootless runtime test layers.

**Non-Goals:** Do not impose a healthy-session/build timeout, change the endpoint trust model, introduce public timeout variables, or guarantee server-side cancellation after losing connectivity. No image package, privilege, mount, state-layout, or authentication change is required.

## Decisions

### 1. Use one shutdown deadline and preserve the primary status

Use one idempotent shutdown routine for signal and EXIT paths. Save the first terminal signal's status (TERM 143, INT 130, HUP 129), or the application's observed exit status on normal completion, before cleanup. Ignore or coalesce later signals so they cannot restart shutdown, recurse through traps, or overwrite the saved status. Neither `set -e` nor cleanup command failures may replace it.

Use internal constants: 20 seconds overall from shutdown entry, at most 5 seconds of graceful application wait after signal forwarding, and engine control calls limited to 2 seconds before TERM plus at most 1 second before KILL. Bound local client termination and reaping by the remaining overall budget. Cap every phase by time remaining, reserving time for forced removal and local client termination. Ordinary EXIT cleanup requires no graceful application wait. Do not begin retries that cannot fit the remaining budget.

Use Bash elapsed-time accounting for the common deadline instead of accumulating independent full timeouts. Test the externally observed bound with a small scheduler tolerance. Check GNU `timeout` support before session operations with an actionable error if unavailable; help must exit before prerequisite checks. Include a hard kill-after bound, since a TERM-ignoring control client defeats a soft timeout alone.

Alternative: time out only `podman kill` and `rm`. Rejected because `wait` and repeated signals could still hang or extend shutdown. A timeout on the entire running session would constrain ordinary work.

### 2. Separate remote cleanup from local client termination

On signal shutdown, attempt the original signal, allow a bounded graceful exit, and force-remove the owned container if it remains. Failed forwarding must not skip removal if budget remains. Bound ownership discovery, inspection, signal delivery, removal, and every other engine call made during shutdown with the same deadline. Retain already-absent `--ignore` behavior.

If an attached or creation client remains after remote cleanup, terminate that tracked child, escalate to KILL as needed, and reap only after completion is observed. Never perform a final unbounded `wait` on a running child. Target owned children, not the wrapper's ambient process group or unrelated processes. Killing a local Podman client is not proof that the remote application stopped.

Report failed/timed-out steps on stderr with the known container ID or session identity and guidance to inspect the engine. An already-absent container is not an error. Return the saved status even for a successful application followed by cleanup failure. An unreachable engine means cleanup is unconfirmed, not successful.

Alternative: hide failures to preserve status. Rejected because diagnostics and status preservation are compatible and users need the identity of potentially remaining resources.

### 3. Preserve ownership through interruptible creation

Create a private per-session temporary directory for create stdout/stderr and fresh per-attempt CID files, using a scoped private umask. Pass a nonexistent `--cidfile` path on each attempt and attach a unique per-session ownership label. Retain workspace-index names and the 20-attempt collision limit. Never reuse a previous attempt's CID file.

Run create as a supervised background child so the wrapper can handle signals during creation. Collect its status and ID through owned files rather than relying solely on assignment after a foreground command substitution. On normal success, use the confirmed ID; on interruption, immediately enter shutdown and never start the application. Track create and attach clients separately; remove temporary files after bounded identity recovery.

Recovery first considers the CID file and captured create result. If neither is available, query only containers carrying this session's unique ownership label within the remaining deadline, verifying session ownership before removal. Reconcile failed/interrupted creates using that evidence. A workspace name alone never authorizes deletion. Ordinary create failures preserve status and stderr; collisions never authorize removal of the colliding container.

Alternative: remove the attempted name on interruption. Rejected because another session may own it. A CID file alone narrows the race but cannot discover a server-created container when the client never receives the result; the label supplies a second recovery route. If the server completes creation after all bounded recovery attempts have ended, report the unresolved session identity rather than promising unlimited reconciliation.

### 4. Preserve verification boundaries and command failure status

Use one capture helper for both queries. Append a non-LF sentinel inside the capture after explicitly saving the query status, then return that saved status. Remove only the appended sentinel afterward, preserving the query's original LF bytes. The marker write must not turn query failure into success. Leave stderr attached so engine diagnostics remain visible.

After a successful query, remove at most one final LF as its permitted terminator. Reject any remaining LF, including leading, embedded, and trailing blank records; then apply existing field/rootless/path validation. Accept no terminator for compatibility with current clients. Preserve spaces in valid socket paths: do not trim all whitespace or split records in a way that discards empties. Query failure takes precedence over parsing valid-looking stdout.

Alternatives: ordinary substitution followed by a newline check, whitespace trimming, or reading only the first line. Rejected because they discard the boundaries being validated. Do not retry or normalize malformed data. Disabled delegation continues to skip its separate query.

### 5. Verify faults with deterministic test synchronization

Extend fake Podman with exact raw stdout, failure after output, per-command stalls/failures, ignored signals, delayed CID publication, and synchronization markers. Keep state synthetic and executables on native storage. Use readiness handshakes before delivering signals. Assert that invalid verification causes no image operation and unrelated identities are never removed.

For both queries, test valid data with zero/one final LF; extra blank records and multiple trailing LFs; leading/embedded blank records; additional nonblank records; empty output; and valid-looking output followed by query failure. The current fake uses `print`, so new controls must emit exact bytes without accidental added terminators. Retain existing engine and endpoint-negative coverage.

Lifecycle tests cover cooperative/ignored TERM, INT, and HUP; control clients that stall and ignore TERM; failed forwarding/removal; application exits 0, nonzero, and 125 followed by cleanup failure; repeated signals; and interruption before/after CID publication. Assert elapsed bounds, diagnostics, primary status, no start after interruption, no leaked fake children, private temporary-file cleanup, and untouched unrelated containers. A controlled timeout/clock seam can accelerate phase assertions, but include at least one wall-clock test with the actual timeout tool and production deadline.

Extend opt-in rootless tests with a ready-signaling application that ignores signals and a concurrent unrelated session. Verify signal statuses, bounded completion, owned-container disappearance, and continued unrelated-session operation in both state modes. Include a cooperative signal case and retain normal exit 125 and stdin/TTY regressions. Use harmless shell commands, synthetic state, uniquely owned resources, and the existing runner's preserved host paths. Do not disrupt the real service to simulate outages: fake tests cover engine stalls. Record unavailable prerequisites without marking acceptance complete.

## Risks / Trade-offs

- A loaded engine can exceed deadlines -> Report the failed phase and recoverable identity, using one documented budget and scheduler tolerance in tests without extending production deadlines.
- Remote creation can complete after local cancellation -> Attempt label-based recovery within the budget and report unresolved ownership; never remove by ambiguous name.
- More lifecycle state creates signal races -> Centralize shutdown, track child phases, and synchronize pre-ID/post-ID/repeated-signal tests.
- Capture files can outlive clients -> Keep them private, recover identity before removal, and check every terminal cleanup path.
- Sentinel writes can mask failure -> Preserve query status explicitly and test failure after valid stdout at both sites.
- Minimal hosts may lack GNU timeout -> Check the prerequisite early with actionable help/README instructions; help remains independent and no image dependency is added.

## Migration Plan

No state migration or image rebuild is required. Deliver each behavior with tests and documentation, run the synthetic suite and targeted rootless acceptance, and record versions/results in `docs/validation.md`. Preserve historical validation and the unrelated `.gitignore` edit.

Rollback restores the previous wrapper and corresponding tests/docs together. State remains untouched, but unbounded shutdown and permissive trailing-blank handling return. Main-spec synchronization, archive, and commit are later explicit actions.
