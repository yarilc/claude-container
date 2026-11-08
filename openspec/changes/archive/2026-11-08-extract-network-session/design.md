# Design

## Context

See proposal.md for motivation. Restricted-network logic currently sits in these places of `claude-container.sh`:

| Lines | Logic |
|---|---|
| 330-363 | preflight, platform check, guard probe, qualification input |
| 376-394 | proxy image presence, runtime image identity |
| 409-429 | qualification mounts, restricted container options |
| 577-597, 643-676 | proxy recovery and cleanup inside `shutdown` |
| 685-799 | snapshot, proxy lifecycle, hardening verification, relay/guard arguments |

It uses the wrapper's `control()`, `reap_client()`, `create_pid`, `proxy_check_pid`, `session_dir` and the 20-second `shutdown_deadline`. The other four wrappers have their own, differently structured lifecycle code. The specs that bound this behavior are `container-launcher` "Bounded session shutdown" and `network-egress` "Session-owned egress resource lifecycle".

## Goals / Non-Goals

**Goals:**
- Exactly one shared implementation of the restricted-session lifecycle, copied unchanged with `network/`.
- A wrapper integration small enough to review in each port: four process calls and one deadline hand-off.
- Unchanged observable behavior and test expectations, including messages, statuses, ordering and identities.

**Non-Goals:**
- A shared wrapper chassis (CLI, engine verification, image operations, name reservation, agent container lifecycle). That may be a later step once the five wrappers converge.
- Changing proxy, guard, relay, policy or qualification semantics.
- Porting to other wrappers.

## Decisions

### D1 — Separate process with fixed operations, not a sourced library

`python3 -I network/session.py <operation> ...` with `prepare`, `start`, `agent-args` and `stop`. There are no shared shell variables or traps. Inputs are explicit arguments. Outputs are fixed records on stdout. Diagnostics go to stderr with the profile's message prefix. Exit status 0 means success; any other status means the wrapper stops with that status.

**Alternatives considered:**
- *Bash library sourced by the wrapper.* Rejected: it couples to every wrapper's globals and traps.
- *Shared wrapper chassis.* Deferred: it would require rewriting four wrappers at once.

### D2 — Operation contracts

| Operation | Replaces | Input | Output |
|---|---|---|---|
| `prepare` | 330-363 | mode, installation, writable paths, mount targets, provider inputs, optional qualification input/workspace | `guard_digest`, then `token tls` in probe mode, one record per line |
| `start` | 703-766 | session dir, provider inputs, guard digest, optional qualification token/tls | `policy_identity` |
| `agent-args` | 421-429, 767-799 | mode, session dir, guard digest, probe flags, `--` agent command and arguments | NUL-delimited Podman options, then `--`, then the entrypoint arguments |
| `stop` | `recover_proxy` and proxy part of `shutdown` | session dir, `--deadline` seconds | nothing; warnings on stderr; status 0 or nonzero for incomplete cleanup |

The wrapper reads NUL-delimited output with `mapfile -d ''`, so arguments with spaces or newlines are never split.

The wrapper keeps everything agent-specific and adds it itself:
- the agent command (`/usr/local/bin/claude`) and its YOLO arguments;
- optional-traffic variables (`CLAUDE_CODE_DISABLE_*` and others);
- credential forwarding;
- the state layout and `/claude-home`.

### D3 — Session directory ownership

The wrapper still creates the session directory (`mktemp` in the provider runtime directory or the default temporary directory) and removes it at the end, because offline sessions use it too. The helper writes only inside it:
- `config/`, `transport/`, `logs/`;
- `proxy.cid`, `proxy.stdout`, `proxy.config`, `proxy.effective`;
- an `identity` record.

`stop` derives ownership only from files in that directory and from the profile's egress label carrying the session token. This is the same rule as the current `recover_proxy`.

### D4 — Cancellation and the shared shutdown budget

- `start` puts itself in its own process group (`os.setpgrp()`). Bounds are the same as today:
  - create and start are unbounded but interruptible;
  - the inspect and exec hardening checks have 5 seconds each (TERM, then KILL 1 second later);
  - readiness has a 10-second deadline.

  It does not clean up on failure. A failed or interrupted `start` leaves `proxy.pending` or `proxy.id`, and the wrapper's shutdown always calls `stop`, exactly as the in-line code relied on the trap.
- The wrapper records the `start` PID like today's `proxy_check_pid`. During `shutdown` it sends TERM and then KILL to the group and reaps it, as it does now.
- The wrapper then calls `stop --deadline <remaining>`. `stop` bounds each engine call to `min(2s, remaining - 1)`, mirroring `control()`. It recovers the identity from cid, stdout or label, confirms the label, and removes the proxy. It prints the sanitized `denials.jsonl` tail with the same heading as today.
- `stop` never changes the wrapper's exit status. It warns, with the same identities as `cleanup_warning`, when removal is unconfirmed.

The order inside `shutdown` stays as it is: agent container, then proxy, then removal of the session directory.

### D5 — Fail-closed ordering is preserved

The wrapper keeps this sequence:
- before image operations: argument and mode checks, engine verification, then `prepare`;
- then image operations;
- then the qualification check (`qualify.py check`);
- then `start`;
- then `agent-args`;
- then agent container creation.

If any helper call fails, no agent container is created. The helper's messages are the current messages, so wrapper tests keep their assertions.

### D6 — Agent-neutral naming from the profile

The proxy container name is `<install.state_name>-<session token>`, which is `claude-egress-…` for Claude, the same as today. Labels come from `PROFILE.label('egress' | 'qualification')`. Proxy variables, relay port 18080, guard paths and the readiness record are fixed shared constants. The literal scan applies to `session.py`.

### D7 — Tests

- New shared `tests/test_session.py` with a fake engine on `PATH`. It covers:
  - each operation's output contract;
  - fail-closed `start` leaving markers that `stop` cleans up;
  - group termination of an interrupted `start`;
  - recovery by cid, stdout and label in `stop`;
  - refusal of foreign labels;
  - deadline bounding with stalled engine calls;
  - the diagnostics tail;
  - NUL-safe arguments.
- `test_wrapper.py` copies the real `session.py` into its restricted fixture, next to the existing synthetic `control.py`. The wrapper therefore exercises the actual helper with the fake engine, and existing restricted tests keep their expectations.
- `test_alignment.py` adds `session.py` and `test_session.py` to the shared inventory. It also checks that the wrapper calls `network/session.py` and no longer contains the proxy lifecycle: no `podman create … $proxy_label`, `proxy_hardening.py probe` or `control.py snapshot`.
- The runtime suites (`--guard`, `--network`, `--qualification`, `--setup-runtime`) are the acceptance gate, unchanged.

## Risks / Trade-offs

- [Shutdown budget split between Bash and Python drifts or double-counts] → One deadline is computed in the wrapper and passed down. `stop` takes only the remaining seconds. Existing tests already measure the bounds: stalled controls, repeated signals, probe interruption, concurrency.
- [A KILLed `start` leaves a proxy without a cid] → Recovery by label in `stop`, as today. A test interrupts `start` after create and before cid publication.
- [Text drift in diagnostics breaks wrapper tests and setup parsing] → Messages are moved verbatim, and the profile prefix replaces `claude-container:`. Synthetic wrapper tests and setup tests are rerun on the host.
- [Extra Python start-ups per launch] → Three or four short processes; negligible next to engine calls. Host Python is already mandatory in restricted modes.
- [Verification needs the host] → As for `extract-agent-profile`, guard, wrapper, setup and runtime suites run on the operator's WSL host. This session only runs the unit, alignment and diagnostic checks.

## Migration Plan

1. Implement the helper and wrapper integration. Run the shared unit tests here and the full synthetic and runtime suites on the host.
2. Users rerun `--container-setup` (code identity changes); the behavior is otherwise unchanged.
3. Tag `sandbox-ref-2` after archive, together with the other Wave 0 changes.
4. Rollback: revert the commit and rerun setup.
