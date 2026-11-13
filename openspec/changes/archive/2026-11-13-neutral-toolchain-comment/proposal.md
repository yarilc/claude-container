# Proposal

## Why

`sandbox-ref-15` added a comment to the shared `setup/toolchains.py` that
names an agent:

```
# XDG base-directory variables can place a wrapper's state (OpenCode sets them).
```

Shared files must not contain agent identifiers. In OpenCode, whose profile
lists `opencode`, the scans in `tests/test_alignment.py` and
`tests/test_reference_copy.py` fail on this line. This repository scans only
its own identifiers, so the defect passed here. A scan of every `sandbox-ref-15`
shared file against the identifiers of all five profiles finds no other
occurrence.

## What Changes

- The comment becomes agent-neutral: `# XDG base-directory variables can
  place a wrapper's state (a wrapper may set them).` No code change.
- Tag `sandbox-ref-16`. `setup/toolchains.py` is qualified code, so its digest
  changes and installations rerun `--container-setup` after adopting the tag.
- No new cross-profile check (operator decision, 2026-11-13).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None: the behavior is unchanged. The change declares `skip_specs`.

## Impact

- `setup/toolchains.py`, `docs/validation.md`, `docs/network-contract.md`
  (parity cells).
- OpenCode's paused change `adopt-sandbox-ref-15` moves to `sandbox-ref-16`.
  Codex (`sandbox-ref-14`), Pi and Antigravity adopt `sandbox-ref-16`.
