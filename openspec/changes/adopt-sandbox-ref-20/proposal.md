# Proposal

## Why

`sandbox-container` is now the reference for the shared sandbox components (`sandbox-ref-19` moved the role, `sandbox-ref-20` fixed two adoption blockers). `claude-container` still holds its own copy at `sandbox-ref-18` together with the reference-only tooling, and it has never had a reference manifest. This change makes Claude an ordinary adopting wrapper, like Codex, OpenCode, Pi and Antigravity.

## What Changes

- Add `tests/test_reference_copy.py`, pinned to `sandbox-ref-18` (the files Claude holds today), then adopt `sandbox-ref-20` with `tools/propagate.py` run from `sandbox-container`. That run copies the changed shared files, among them:
  - the fixture profiles in `tests/fixtures/`;
  - shared tests that use the fixture profile;
  - support for profiles without authentication methods;
  - the wrapper-independent guard test.

  It also points the manifest at `sandbox-container` and moves the tag references in current-state documents.
- Move the eight shared setup tests that launch this wrapper (from the `sandbox-ref-18` `tests/test_setup.py`) into the per-agent `tests/test_setup_wrapper.py`, keeping Claude's semantics: an explicit mode is required, and provider mode and login are available.
- Adapt the per-agent tests to the shared profile view: `tests/test_wrapper.py` loads the checkout profile by path.
- **BREAKING (maintainers only)**: remove the reference-only files: `tools/propagate.py`, `tests/test_propagate.py`, `docs/propagation.md`, and the `reference-propagation` capability. Propagation now runs from `sandbox-container`.
- Fix the session lifetime notice in `claude-container.sh`, as in the reference. Bash `SECONDS` counts whole seconds, so a short failing session that crossed a second boundary was reported as a reached lifetime limit. The existing requirement already forbids the notice in that case, and the defect makes `--wrapper` runs flaky.
- Documentation:
  - README and `AGENTS.md`: Claude adopts tags from `sandbox-container` and shared defects are fixed there.
  - Parity table in `docs/network-contract.md`: the reference row is `sandbox-container` at `sandbox-ref-20` and the Claude row reads `Ported from sandbox-ref-20`. The other four rows are unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `network-egress`: the shared components stay byte-identical to the `sandbox-container` reference copy at the pinned tag, checked by the manifest and the sibling checkout.
- `reference-propagation`: retired in this repository; the capability lives in `sandbox-container`.

## Impact

- Shared files from `sandbox-ref-20` (`network/`, `setup/`, shared tests and fixtures). Installed code changes, so installations rerun `--container-setup`.
- Per-agent files: `claude-container.sh` (lifetime notice), `tests/test_reference_copy.py`, `tests/test_setup_wrapper.py` and `tests/test_wrapper.py`, plus the documents above.
- Removed: `tools/propagate.py`, `tests/test_propagate.py`, `docs/propagation.md` and `openspec/specs/reference-propagation/`.
- Operator: push, then setups on the three hosts. The newer WSL host needs host CA trust because of its TLS-inspecting VPN. Authenticated checks remain operator-run.
