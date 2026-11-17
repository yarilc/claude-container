# Design

## Context

Claude adopted `sandbox-ref-22` and `sandbox-ref-23` (change `adopt-sandbox-ref-22`, archived 2026-11-17). The `tools/propagate.py` dry run from `sandbox-ref-23` to `sandbox-ref-24` (2026-11-17) gives this plan:

- **Update:** `launcher/core.sh`, `tests/test_launcher.py`.
- **Rewrite:** two references in `docs/network-contract.md`.
- **Move:** the manifest to `sandbox-ref-24` (`dd5d82e`).

The core change only adds an access check before each state directory is resolved, plus a prefixed error when one cannot be created. Claude's agent part does not touch state directories. The shared case `test_inaccessible_state_and_ignored_permissions` covers the new diagnostics against the fixture agent parts.

Parity rows today:

| Repository | Reference row | Claude row | Codex row |
| --- | --- | --- | --- |
| `sandbox-container` | `sandbox-ref-23` | "Ported from `sandbox-ref-21`" (stale) | adopted `sandbox-ref-24` |
| `claude-container` | `sandbox-ref-23` | adopted `sandbox-ref-23` | adopted `sandbox-ref-24` |

## Goals / Non-Goals

**Goals:**
- Claude runs on the `sandbox-ref-24` core with no Claude-specific change.
- Both parity tables state the same rows for the reference, Claude and Codex.

**Non-Goals:**
- Antigravity, OpenCode and Pi adoptions.
- Any change to the reference code or a new tag: the `sandbox-container` edit is documentation only.

## Decisions

1. **Adopt with the tool on the change's branch.** Commit this change directory on `main`, then run `--apply`, which creates `adopt-sandbox-ref-24`. The tool rewrites the tag references in `docs/network-contract.md`, including the reference and Claude rows; check each row by hand afterwards.

2. **No old-test gate.** The old-test gate exists for a launcher replacement. Here the core gains one diagnostic, and the shared test that covers it arrives with the tag. The Claude wrapper tests run unchanged; a failure there is a lost behavior and pauses the change.

3. **Parity rows.**
   - Reference row (both repositories): "Reference (`sandbox-ref-24`, shared launcher core)", with the rest of the row unchanged.
   - Claude row (both repositories): "Adopted `sandbox-ref-24`: shared launcher core", with this adoption's runner result and date.
   - Codex row in `claude-container`: copied from `codex-container`.

   The `sandbox-container` edit is the last implementation step, after the Claude row is final. It is committed on `sandbox-container` `main` with the Claude row copied byte for byte from `claude-container`. It changes no shared file, so it needs no tag, and no wrapper's `tests/test_reference_copy.py` is affected.

4. **Validation scope.** The installed core changes, so validation covers what the core touches:
   - `python3 -m unittest tests.test_reference_copy tests.test_alignment` with host Python next to the `sandbox-container` checkout, with the sibling check not skipped (the tool's suggested check);
   - the unit discovery in the disposable test container;
   - `bash tests/run-runtime.sh --wrapper`, `--setup` and the default runtime run;
   - `git diff --check`.

   Restricted, qualification and network suites are not rerun: they do not depend on the state-directory checks, and the operator's `--container-setup` on the three hosts requalifies the installations.

## Risks / Trade-offs

- **[Installed qualification reports no longer match, because `launcher/core.sh` is part of the identity]** → The operator reruns `--container-setup` on the three reference hosts after the merge.
- **[The `sandbox-container` edit lands in another repository from this change]** → It is documentation only and is recorded in this change's tasks and validation, as earlier adoptions did for their parity rows.
