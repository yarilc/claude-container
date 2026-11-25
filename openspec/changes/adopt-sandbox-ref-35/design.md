# Design

## Context

Claude adopted `sandbox-ref-34` on 2026-11-25. `sandbox-ref-35` holds only
`fix-runtime-test-portability`: test code, the shared probe
`tests/guard_terminal_probe.py` and `AGENTS.md`. No product code changed (see
proposal.md, Why). The reference validated it on 2026-11-25 on two native hosts:
- **Rocky 9 lab host:** no IPv6, `systemd` with `[memory pids]`, Podman 5.8.0
  and crun 1.27, and the CA bundle at the RHEL path. Every mode passed. The
  three terminal cases were unavailable, skipped by the probe with
  `crun: unlink /dev/console: Read-only file system`.
- **WSL:** IPv6, `[cpu memory pids]`, Podman 4.9.3 and crun 1.14.1. Every mode
  passed, and the terminal cases ran.

**Claude's copies that differ from the reference:**
- `tests/test_network_runtime.py`:
  - the budget test is
    `test_agent_budgets_are_effective_and_lifetime_cleans_owned_proxy`. It
    checks offline and provider sessions, then the proxy's cleanup;
  - the terminal case starts the wrapper as `claude-container --tty-probe`,
    from an invocation image built `FROM` the runtime image;
  - `network/` is already on `sys.path`, and `tests/` is on it under the
    runner's discovery.
- `tests/test_setup_runtime.py` matches the reference's `clean_tags` and
  `answers()` apart from Claude's questions. It does not import
  `sandbox_profile` yet.
- Claude's runner runs in `localhost/claude-code:latest`. That image has the
  reference's pinned base, so the client is the same Podman 4.3.1.
- The profile derives the engine image as `localhost/claude-code-engine`, so
  `REAL_PROFILE.image('engine', …)` names Claude's tags.

## Goals / Non-Goals

**Goals:**
- Claude's runner suites pass on both native hosts, for the same reasons as
  the reference's. On Rocky, only the terminal cases are unavailable.
- Claude's per-wrapper fixes have the reference's structure, so later tags
  copy cleanly beside them.

**Non-Goals:**
- No product, image or installation change. Operators rerun nothing.
- No new Podman client in the runtime image (out of scope in the reference).
- No validation on the Windows Podman machine or from a session. The tag
  changes no code that runs there, and `sandbox-ref-34` was validated there.
- No fix for the intermittent readiness timeout of
  `test_toolchain_added_during_offline_session_without_network`. It is the
  reference's follow-up.

## Decisions

1. **The per-wrapper fixes are the reference's, on Claude's test shapes.**
   - **Budgets:** an `engine_budgets()` helper returns the delegated
     controllers and the process mechanism, through
     `agent_budgets.delegated()` and `process_mechanism()`. The budget test
     passes both to its in-container check, for each mode × budget subtest.
     The proxy test uses the same helper instead of its inline copy.
     The lifetime and proxy cleanup part is unchanged.
   - **Terminal case:** it runs in a `subTest(terminal=True, isolated=…)` and
     skips with `terminal_skip_reason(IMAGE)`. The probe takes the runtime
     image, as in the reference, not the invocation image. The invocation
     image changes only `/usr/local/bin/claude`, so `/dev` and terminal
     attach are the same.
   - **Setup test:** the CA copy goes to `self.base / 'ca-bundle.pem'`.
     `clean_tags` adds `REAL_PROFILE.image(kind, 'setup-' + release)` for
     `engine`, `toolchain` and `proxy`.
   - Alternative: change Claude's tests only where Rocky fails. Rejected: the
     shapes would drift from the reference's, and the next adoption would
     have to re-derive them.

2. **The spec delta takes the reference's text.** Both requirements are
   identical to the reference's apart from the two missing items, so the
   delta is the reference's current text (decision 1 of `adopt-sandbox-ref-34`).
   Claude's README already has the read-only `/sys` paragraph, and
   `test_offline_session_engine_has_no_external_path` already checks
   `/proc/net/dev`. No code or README change backs the delta.

3. **Validation runs on the reference's two native hosts.**
   - **Rocky** shows that Claude's fixes work where the assumptions fail.
   - **WSL** shows that the terminal cases still run and pass where a
     terminal attaches, so the probe does not hide them.
   - The modes are those the tool prints, plus `--network-feasibility`,
     `--setup-runtime` and the unit discovery (proposal.md, Impact). On
     Rocky, host Python 3.9 is too old for the discovery, so it runs in the
     runtime image, as for the reference.
   - **Manual terminal evidence on Rocky:** the operator opens an offline
     `claude-container --container-shell` session with the host's client,
     recorded with `script`. No model request is needed.
   - Alternative: Rocky only. Rejected: it cannot show that the probe lets
     the terminal cases run where they work.

4. **`AGENTS.md` takes the reference's paragraph, with Claude's runtime
   image.** The `/codex-home` path in the policy path rule becomes
   `/claude-home`, Claude's native home in `agent/profile.json`. The same
   section is being edited, and the wrong name points to another wrapper's
   path.

5. **Parity follows `adopt-sandbox-ref-34` task 4.**
   - The tool moves Claude's own cells to `sandbox-ref-35`. Claude's row
     records the results of decision 3.
   - The reference row is copied from `sandbox-container`, where it already
     names `sandbox-ref-35`.
   - Claude's row is then copied into the reference and the other four
     wrappers.

## Risks / Trade-offs

- **[Risk] A Claude-only test has another host assumption on Rocky.** Claude's
  network suite has cases that the reference lacks (provider subtests, the
  permission-mode grid). → A failure in shared code pauses the change for a
  fix in `sandbox-container` under a new tag. A Claude-only failure is
  recorded with its log, and its fix is proposed before the branch grows
  beyond the reference's fixes.
- **[Risk] Missing images or disk space on Rocky.** The lab host has about
  2 GB free in `/home`, and pruning has removed the guard toolchain before.
  → Before the suites, the operator checks for the images the runner uses:
  - `localhost/claude-code:latest` and `localhost/claude-code-engine:latest`;
  - `localhost/claude-guard-toolchain:development`;
  - the free space.

  Missing images are built from the branch, as the reference's were on WSL.
- **[Risk] The intermittent readiness timeout appears.** → The test is rerun
  alone. The failure is recorded as intermittent when the reruns pass, as in
  the reference record.
- **[Trade-off] The terminal cases stay unavailable on Podman 5 with
  crun 1.27.** Claude's runner client cannot attach there. → The manual
  session of decision 3 is the evidence, as in the reference.

## Migration Plan

None for installations: only tests and documents change. Rollback is a revert
of the merge. The manifest then names `sandbox-ref-34` again, and the next
adoption starts from it.
