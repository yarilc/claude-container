# Design

## Context

See proposal.md (Why).

The relevant shared code paths:

- **Failure path:** `setup/setup.py` `run()` captures stdout and stderr when `capture=True`. On a nonzero exit it prints only the `PREFIX + 'status='` lines of a `--container-qualify` command, then raises `SetupError('Setup command failed (exit N): ...')`. `smoke_in()` calls `run()` for `--container-shell` with `capture=True`, then checks the `SANDBOX_SETUP_SMOKE_OK` marker.
- **State checks:** `setup/common.py` `prepare_state()` calls `private()` for the configuration directory, or for the isolated state root. Shared directories (`PROFILE.shared_dirs`) only need to exist and be accessible.
- **Summary wording:** `setup/setup.py` labels every path returned by `prepare_state()` as `Prepared or reused private state directory`.
- **Refusal message:** `private()` raises `Private caller-owned directory required: <path>; existing permissions were not changed.` for every failure: owner, mode, access or not a directory.
- **Wrapper behavior per agent:**

  | Wrapper | Shared directories | Wrapper requires privacy |
  | --- | --- | --- |
  | Claude | `~/.config/openspec` | No; it is created privately when missing |
  | OpenCode | `~/.local/share/opencode`, `~/.cache/opencode`, `~/.local/state/opencode` | Yes |
  | Pi | `~/.agents` | Yes |
  | Codex, Antigravity | none | Not applicable |

- **Profile validation:** `network/agent_profile.py` validates `native` with `fields(..., required, optional=())`, so an optional key can be added without breaking existing profiles.

## Goals / Non-Goals

**Goals:**

- A failing smoke launch shows the cause in the setup output.
- Setup refuses, before image work, exactly the shared directories the wrapper would refuse.
- Refusals say what is wrong and how to fix it.

**Non-Goals:**

- Changing any wrapper's own privacy rules.
- Surfacing stderr for other captured commands, such as builds, which already stream, or qualification, whose status line is already shown.
- Bun or other build variables during qualification.
- Repairing permissions automatically.

## Decisions

1. **Excerpt only on failure, from the captured stderr.**
   - `run()` gains an `excerpt=False` parameter. With it, a nonzero exit prints the excerpt before raising. `smoke_in()` passes it, and also prints the excerpt when the marker check fails.
   - To make that possible, `run()` returns stderr through a small helper. The alternative, a separate stderr return value, would change every caller.
   - Rejected: streaming stderr live. Smoke runs a non-interactive heredoc, and the wrapper also prints routine notices, such as the gitconfig notice. Showing those on every run adds noise to a successful setup.
2. **Sanitization.**
   - Decode as UTF-8 with replacement, split into lines and drop empty lines.
   - Keep the last 5 lines, remove every character for which `str.isprintable()` is false, and truncate each line to 2048 characters.
   - Print with the `PREFIX + 'smoke: '` label so that the excerpt is distinguishable from setup's own output.
   - The stderr comes from a container that mounts writable shared state. Stripping control characters prevents terminal escape injection. The line and length limits bound the volume.
   - Smoke runs without credentials, so the excerpt cannot contain a key that setup itself supplied.
3. **Boolean profile field, not a per-directory list.** Every current wrapper treats all of its shared directories the same way. A boolean keeps the schema small. A list can replace it later if an agent mixes both kinds; that would need a profile schema change and a new tag either way.
4. **Default `false`.** Claude's behavior and profile stay unchanged. Pi and OpenCode opt in when they adopt the tag. Their setups were already failing later, in the smoke launch, so opting in only moves the failure earlier and makes it clearer.
5. **Summary wording follows the check.** Shared directories that did not go through `private()` are labeled `Prepared or reused shared state directory`. The `private` label is used only for paths that passed `private()`.
6. **Refusal reasons in `private()`**, checked in this order, first match wins:
   1. not a directory;
   2. owner;
   3. group/other bits (observed octal mode, `chmod 700 <path>` or native Linux storage);
   4. missing access.

   The existing sentence `existing permissions were not changed.` stays at the end.
7. **Tag and adoption.**
   - The change modifies `network/` and `setup/` files and shared tests, so it publishes `sandbox-ref-10` under `docs/propagation.md`.
   - Adoption runs as one `adopt-sandbox-ref-10` branch per wrapper.
   - In Pi and OpenCode, that branch also sets `native.private_shared_dirs: true` and updates their per-agent `tests/test_setup_runtime.py` expectations if needed.
   - Adoption happens after this change is archived and tagged. It is listed as workflow follow-up, not as tasks here, because each wrapper is its own repository.

## Risks / Trade-offs

- [The excerpt may show the wrapper's routine notices instead of the error] → The last 5 lines are taken. The fatal message is the wrapper's final output before exit. The test fixture checks that the refusal line appears.
- [A wrapper line could contain a host path] → Paths are already shown in setup's own messages. No secrets are present in smoke runs.
- [Operators with existing non-private Pi or OpenCode shared directories now fail at the state step] → Those setups already failed at the smoke step. The message now names the fix.

## Migration Plan

- After merge, tag `sandbox-ref-10` and propagate to Codex, OpenCode, Pi and Antigravity, following `docs/propagation.md`.
- Existing Claude installations are unaffected until setup reruns, and behave the same afterwards.
- Rollback: re-adopt `sandbox-ref-9` with `tools/propagate.py` (`sandbox-ref-10` to `sandbox-ref-9`).
