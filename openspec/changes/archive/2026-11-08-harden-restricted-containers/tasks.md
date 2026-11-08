# Tasks

## 1. Restrict container authority

- [x] 1.1 Add capability-drop and no-new-privileges arguments to restricted agent and session proxy creation in `claude-container.sh`; verify synthetic wrapper assertions cover offline/provider, shell/Claude, both state modes and absence of new flags in unrestricted mode.
- [x] 1.2 Add real assertions for zero capability sets, NoNewPrivs, keep-id ownership, guard startup, relay and proxy socket/readiness creation; verify these through production network/guard fixtures without credentials.
- [x] 1.3 Document the effective restricted hardening and unchanged unrestricted contract in README, `network/README.md` and `docs/network-contract.md`; verify wording matches both creation paths and preserves seccomp/SELinux/mount constraints.

## 2. Enforce proxy resource budgets

- [x] 2.1 Add `--pids-limit=128` and `--memory=256m` to the proxy and bounded verification of inspect/effective cgroup values before agent startup; verify synthetic cases reject ignored, missing, malformed or mismatched limits without starting an agent or removing limits.
- [x] 2.2 Exercise effective limits, maximum active multiplex concurrency and concurrent slow TLS inspection in disposable real proxy cgroups; verify matching TLS/streaming stays functional within the selected budgets and record observed memory/process use.
- [x] 2.3 Add bounded disposable exhaustion/proxy-death cases and preparation interruption coverage; verify no unrestricted retry, unrelated-resource removal or primary exit-status changes and that cleanup honors the shared deadline.
- [x] 2.4 Document required rootless cgroup support, selected limits and actionable failure behavior in network/setup guidance; verify unavailable controllers are diagnosed without suggesting privilege additions or disabled host policy.

## 3. Integrated acceptance

- [x] 3.1 Run wrapper and setup synthetic suites, TLS parser/proxy and mux suites, Bash syntax checks and `git diff --check`; verify relevant regressions pass and no unrelated mode behavior changes.
- [x] 3.2 Run `bash tests/run-runtime.sh --guard`, `--network-policy`, `--network` and `--setup-runtime` with prepared images and disposable native state; verify CA off/on, both profile inventories, hardening, limits and owned cleanup through production paths, without real credentials or model requests.
- [x] 3.3 Record actual versions, budgets and passed/failed/unavailable checks in `docs/validation.md`, and update only the N18 implementation status in `todo.md`; verify N18 is not declared complete while mandatory runtime acceptance is unavailable or failed.

## Workflow follow-up

- Apply N19 only after these settings are implemented and validated; include their final values in its gate and report fingerprint.
- Synchronize and archive this change through the appropriate OpenSpec workflow after implementation review.
