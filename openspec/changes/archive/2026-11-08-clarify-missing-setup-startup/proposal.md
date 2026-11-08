# Proposal

## Why

A new user invoking the wrapper directly currently enters implicit offline preparation and encounters engine, platform or guard errors instead of the required setup instructions. N20 needs an explicit first-run boundary while preserving managed launches and deliberately configured operator workflows.

## What Changes

- **BREAKING**: Ordinary Claude, shell, worktree and build-and-launch invocations with an unset or empty effective `CLAUDE_CONTAINER_NETWORK` stop with an actionable `--container-setup` message before runtime prerequisite checks, engine queries or state creation.
- Keep explicit `offline`, `provider` and `unrestricted` operator workflows available under all existing checks. Maintenance authorization alone does not select a runtime mode.
- Reuse the managed launcher's validated preferences and existing environment precedence; do not discover or execute configuration from the current workspace.
- Preserve independent help, interactive setup and fixed qualification entry points. An explicit empty managed network override requests no usable mode and receives setup guidance.
- Explain mandatory first-user setup, explicit manual operation, offline API limitations and migration from behavior before `c777b73` in help and documentation.
- Add synthetic admission and managed-launch regression coverage and record validation evidence.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-launcher`: Require actionable, side-effect-free refusal of ordinary launches without an effective runtime mode, before launch-engine verification.
- `container-setup`: Clarify managed preference and direct operator invocation behavior, including explicit empty overrides and first-user guidance.
- `network-egress`: Replace implicit offline selection for ordinary launches with required explicit or managed mode selection while retaining fail-closed enforcement.

## Impact

- Implementation: `claude-container.sh`; existing `setup/launch.py` and `setup/common.py` behavior is reused and verified, with changes only if needed to satisfy these contracts.
- Tests: `tests/test_wrapper.py`, `tests/test_setup.py`, and relevant existing runtime/qualification coverage.
- Documentation: `README.md`, wrapper help, `docs/setup.md`, `docs/network-contract.md`, `AGENTS.md`, `docs/validation.md`, and the N20 status in `todo.md` after implementation acceptance.
- No new dependencies, preference schema, policy destinations, image build inputs or authentication calls. Changed protected wrapper code requires normal restricted requalification.

## Non-goals

N21–N25, B01–B07 and sibling-wrapper rollout are outside this change. Setup is never started automatically; the change does not prove setup completion from an environment variable or relax manual restricted qualification.
