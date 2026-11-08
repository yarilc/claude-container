# Proposal

## Why

`network/` and `setup/` are now copied unchanged between wrappers (`sandbox-ref-1`). About 200 lines of restricted-network logic still live inside the per-agent `claude-container.sh`, spread over six places and coupled to the wrapper's globals, traps and shutdown budget:
- preflight;
- the qualification probe;
- proxy creation, readiness and hardening verification;
- guard and relay arguments;
- proxy recovery and cleanup.

Porting to Codex, Antigravity, OpenCode and Pi would mean re-implementing the most delicate part four times in four different wrapper structures. Moving that logic into one shared helper with a narrow process interface makes each port a small, reviewable integration and keeps the lifecycle testable in shared code.

## What Changes

- Add `network/session.py`, a shared, profile-driven restricted-session helper. It is invoked as a separate process with four fixed operations:
  - `prepare`: preflight, platform check, guard probe and fixed qualification input;
  - `start`: policy snapshot, proxy creation and start, readiness, effective hardening verification;
  - `agent-args`: the NUL-delimited restricted container arguments and guard/relay command prefix for a supplied agent command;
  - `stop`: bounded, ownership-confirmed proxy recovery and removal plus sanitized diagnostics.
- Reduce `claude-container.sh` to calling these operations. It keeps the CLI, engine verification, image operations, the agent state layout, agent-specific environment, name reservation and the agent container lifecycle.
- Share the existing 20-second shutdown budget. The wrapper passes its remaining deadline to `stop`, and interrupts an in-flight `start` by its process group before calling `stop`.
- Keep observable behavior unchanged:
  - messages, exit statuses and diagnostics;
  - proxy and agent container options;
  - identities, readiness checks and fail-closed ordering;
  - qualification-probe behavior.
- Add `session.py` to the protected installation, the qualification code identity and the shared-test inventory. Add shared unit tests with a fake engine. Run the real helper inside the synthetic wrapper fixture.
- Existing installations must rerun setup or qualification, as for any protected code change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `network-egress`: Add a requirement for a shared, wrapper-independent restricted-session interface with bounded, ownership-confirmed cleanup inside the launcher's shutdown budget.

## Impact

- Code: new `network/session.py`. `claude-container.sh` loses its in-line network blocks. `network/qualification_records.py` (`SHARED_CODE`) and `setup/common.py` (`MANIFEST`) change.
- Tests:
  - new shared `tests/test_session.py`;
  - `tests/test_wrapper.py` restricted fixture;
  - `tests/test_alignment.py` inventory and wrapper consistency (the wrapper must call the helper, not duplicate it).
- Docs: `network/README.md`, `docs/network-contract.md` (port checklist), `AGENTS.md`, `docs/validation.md`.
- Downstream: each port integrates the helper in its own wrapper with about 30-40 lines of Bash, instead of re-implementing the lifecycle.
