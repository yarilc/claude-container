# Design

## Context

See `proposal.md` for motivation. `claude-container.sh` builds agent arguments in `container_args` and creates the provider proxy separately. Both use caller UID/GID and `--userns=keep-id`. Restricted agents already use a private network, PID/IPC namespaces and a static guard; the guard calls `PR_SET_NO_NEW_PRIVS` before Landlock/seccomp enforcement. The proxy is a separate Python asyncio process with existing application-level resource bounds, but no explicit container budgets.

## Goals / Non-Goals

**Goals:** Apply hardening before any container code, retain the production startup/lifecycle contract, and detect ineffective rootless resource controls before the agent starts.

**Non-Goals:** Change unrestricted behavior, add agent memory/process budgets, expand platform eligibility, alter TLS inspection or refactor multiplex failure handling. N19 consumes the final settings after this change.

## Decisions

### Apply explicit engine flags at both creation sites

Add `--cap-drop=all` and `--security-opt=no-new-privileges` in the restricted agent branch and unconditionally to the session proxy creation path. Preserve keep-id, caller identity, standard OCI seccomp, security labels and current mounts. The guard retains its own no-new-privileges assertion as defense in depth. Relying only on the guard would leave earlier container execution and the separate proxy uncovered; applying flags globally would unnecessarily change unrestricted sessions.

### Use fixed proxy budgets with runtime verification

Set `--pids-limit=128` and `--memory=256m` for each proxy, with no environment override. These are proposed budgets, not measured capacity claims: existing multiplex limits cap active streams at 64 and payload windows at 16 MiB per channel, but Python, TLS inspection, DNS workers and connection tasks need additional headroom. Validate the selected budgets at the active stream limit and during slow ClientHello inspection before completion. A failed capacity check requires an explicit revision of the proposed budget, never automatic relaxation.

Engine acceptance of the flags is insufficient. Verify configured limits through inspect and their effective cgroup limits through a fixed credential-free probe in the proxy's actual cgroup before agent launch. The probe must work in the read-only capability-free image and must not add host/cgroup mounts or expose an administration endpoint. If the engine/cgroup layout cannot establish either effective limit, fail before ordinary agent startup. Bound these calls and preserve ownership recovery if preparation is interrupted.

### Keep failure and cleanup semantics

Hardening rejection, readiness failure, OOM and proxy death use existing fail-closed and bounded-owned-cleanup paths. Do not recreate an unbounded proxy or reconnect the agent. Test exhaustion only in disposable session resources; never consume host-wide memory or process budgets. Use cgroup inspection for effective limits and a bounded disposable fixture for exhaustion behavior.

### Validate effects and compatibility

Synthetic wrapper tests assert both creation paths and unchanged unrestricted arguments. Real checks inspect `/proc/self/status` capability sets and NoNewPrivs, verify proxy cgroup budgets, caller ownership, socket/readiness creation and real guard/relay operation. Run both state modes, shell and Claude version paths without credentials, both TLS inventories, concurrency and cleanup. Use `tests/run-runtime.sh --guard`, `--network`, `--network-policy`, `--setup-runtime`, and parser/proxy suites; report any unavailable checks rather than treating skipped tests as acceptance.

## Risks / Trade-offs

- Rootless cgroup controllers can be unavailable even when Podman starts containers. Mitigation: verify applied controls and stop provider preparation with actionable guidance.
- A fixed memory budget may reject workloads previously limited only in Python. Mitigation: exercise maximum supported concurrency and slow TLS inspection before accepting the budget.
- Removing capabilities can reveal image startup assumptions. Mitigation: verify actual caller identity and production bootstrap/proxy paths; do not restore privileges to conceal failures.
- Extra verification calls can stall setup. Mitigation: bound calls and include cleanup in the existing ownership/deadline model.

## Migration Plan

Implement and validate on the currently measured WSL target first, with prepared images and synthetic state. Re-run managed setup to install the changed protected wrapper and retain the previous release until smoke succeeds. Existing running sessions are unaffected; new provider sessions require effective budgets. Roll back by selecting the previous complete working release, never by selectively stripping hardening flags. Record versions and results in `docs/validation.md` and mark N18 complete only after the required runtime gate passes. N19 must be applied against this implementation and qualify its final flags/budgets.
