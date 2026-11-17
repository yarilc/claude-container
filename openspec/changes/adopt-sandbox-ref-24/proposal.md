# Proposal

## Why

`sandbox-ref-24` fixes a lost behavior that Codex's adoption found in the shared launcher core: an inaccessible state directory stopped with Bash's raw `cd: ...: Permission denied` instead of the wrapper's diagnostic. Claude runs on `sandbox-ref-23`, so it still has the defect. The parity table in `sandbox-container` is also stale: the reference row names `sandbox-ref-23` and the Claude row still says "Ported from `sandbox-ref-21`".

## What Changes

- Adopt `sandbox-ref-24` from `sandbox-ref-23` with `tools/propagate.py`. This copies `launcher/core.sh` and `tests/test_launcher.py` and moves the `tests/test_reference_copy.py` manifest and the current-state references to the tag.
- Every state directory (shared configuration, shared directories, isolated home and its children, read-only state) is checked for read and search access before it is resolved. A directory the caller cannot enter stops with `claude-container: state directory is not accessible: <path> (...)`. A directory that cannot be created stops with `claude-container: cannot create state directory: <path> (...)`.
- Fix the parity table by hand in both repositories:
  - in `claude-container`, the reference row and the Codex row equal those in `sandbox-container` and `codex-container`, and the Claude row says it adopted `sandbox-ref-24`;
  - in `sandbox-container`, the reference row names `sandbox-ref-24` and the Claude row is copied from `claude-container`.
- No other Claude file changes: the agent part, the entry script and Claude's own tests stay as they are.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `persistent-state`: "Private credential directories" adds the wrapper prefix, the access check before resolving, and the inaccessible and uncreatable directory scenarios. "Read-only state" requires the directories to be accessible and adds the inaccessible read-only state scenario.

## Impact

- **Code:** `launcher/core.sh` and `tests/test_launcher.py` (shared, copied); `tests/test_reference_copy.py` manifest; tag references in `docs/network-contract.md`.
- **Docs:** parity tables in `claude-container` and `sandbox-container`; `docs/validation.md`.
- **Qualification:** the qualification identity includes `launcher/core.sh`, so every installation reruns `--container-setup`; the operator runs it on the three reference hosts.
- **Other wrappers:** Codex is already on `sandbox-ref-24`. Antigravity, Pi and OpenCode adopt `sandbox-ref-24` in their own changes.
