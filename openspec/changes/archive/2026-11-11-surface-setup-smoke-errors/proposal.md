# Proposal

## Why

On 2026-11-11 an operator ran guided setup for the Pi wrapper, which uses the shared `setup/` code. Setup failed three times, and the last two failures showed only `Setup command failed (exit 1): bash .../pi-container.sh`. The cause was visible only after a debug wrapper captured the smoke check's stderr: `State must be private: /home/<user>/.agents`. Two shared-setup defects combined:

1. **Smoke errors are hidden.** `setup/setup.py` `run()` captures the smoke command's stderr and prints none of it. Only `--container-qualify` status lines are surfaced.
2. **Setup and wrappers disagree on shared-directory privacy.**
   - `setup/common.py` `prepare_state` requires privacy only for the configuration directory. It treats the profile's `shared_dirs` as ordinary writable state, which matches Claude (`~/.config/openspec`).
   - The Pi and OpenCode wrappers require every shared directory to be caller-owned and private.
   - As a result, setup passes its own checks and reports `Prepared or reused private state directory` for a directory that is not private, and then fails later in the smoke launch.

The same session, and an earlier OpenCode one, showed a third, smaller defect: the privacy refusal (`Private caller-owned directory required: <path>; existing permissions were not changed.`) names neither the problem found nor the fix.

## What Changes

- **Smoke diagnostics:** when the smoke launch fails, or does not confirm readiness, setup prints a bounded, sanitized excerpt of the wrapper's stderr before the existing failure message. Only printable characters are kept; the excerpt is limited to the last 5 non-empty lines, each of at most 2048 characters.
- **Profile-declared privacy:** a new optional agent-profile field `native.private_shared_dirs` (boolean, default `false`) declares that the wrapper requires the shared directories to be private.
  - When the field is `true`, `prepare_state` applies the same private, caller-owned check to every shared directory as to the configuration directory. Setup then fails before image preparation and names the path.
  - Claude keeps the default `false`. Pi and OpenCode set `true` when they adopt the new reference.
- **Actionable refusal:** the private-directory refusal states:
  - whether the problem is the owner, group/other permissions or access;
  - the observed mode;
  - that `chmod 700 <path>` (or native Linux storage) fixes the permission case.

  Setup still never changes permissions itself.
- A new reference tag (`sandbox-ref-10`) and propagation to the four sibling wrappers with `tools/propagate.py`.
  - Pi and OpenCode also set `private_shared_dirs: true` in their own profiles when they adopt the tag.
  - Codex and Antigravity have no shared directories and keep the default.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-setup`: three added requirements, without changing the existing ones:
  - smoke failure diagnostics;
  - profile-declared shared-directory privacy;
  - an actionable private-directory refusal.

## Impact

- **Shared files**, which need a new reference tag:
  - `setup/setup.py` (smoke error excerpt);
  - `setup/common.py` (`prepare_state`, `private` message);
  - `network/agent_profile.py` (optional field and its validation);
  - shared tests: `tests/test_setup.py`, `tests/test_agent_profile.py`.
- **Claude-specific files:** documentation only (`docs/setup.md`, `docs/validation.md`, `CHANGELOG.md`). `agent/profile.json` is unchanged, because the default keeps today's behavior.
- **Siblings**, after the tag:
  - Pi and OpenCode profiles set the field, and their per-agent tests and documents are updated;
  - Codex and Antigravity adopt the tag unchanged.
- **Users:** a failing smoke check now shows its cause. A Pi or OpenCode setup with non-private shared directories fails earlier, with the path and the fix. No permission is changed automatically.
- **Out of scope:** Bun images and qualification (`PI_ENABLE_BUN` is not visible to `network/qualify.py`). That needs a separate decision.
