# Design

## Context

`claude-container` `main` (`094ec39`) holds exactly the shared files of `sandbox-ref-18`: it was the reference when that tag was cut, and `sandbox-container` imported its history with the same commits. It has no `tests/test_reference_copy.py`. `tools/propagate.py` (in `sandbox-container`) refuses a target without one, checks every manifest file against the old tag, and on `--apply`:
- copies the changed shared files;
- rewrites the manifest's tag, commit and hashes, and since `sandbox-ref-20` its `SIBLING`, docstring and skip message;
- replaces the old tag with the new one in current-state documents.

`sandbox-ref-20` changes the shared test ownership:
- module-level shared tests use the fixture profiles;
- the setup tests that launch the wrapper are per-agent;
- the qualification gate uses the real profile and wrapper.

## Goals / Non-Goals

**Goals:**
- Claude adopts `sandbox-ref-20` through the normal tool path, and every runner mode passes.
- After this change, nothing in this repository implies that it is the reference.

**Non-Goals:**
- Adoption in Codex, OpenCode, Pi and Antigravity. Each needs its own change.
- Changes to Claude's provider policies, profile or authentication behavior.

## Decisions

1. **The first manifest is copied from Codex.** Codex's `tests/test_reference_copy.py` already pins `sandbox-ref-18` (`958465b`) with the hashes of the complete shared set, which Claude holds unchanged. Claude copies it byte for byte: its `SIBLING = ROOT.parent / 'claude-container'` is renamed by the tool on apply. Before the tool runs, the copied manifest must pass in Claude, as proof that no fork exists.
   - Alternative considered: generating a manifest by hand. Rejected, because the copy is already verified in four wrappers.
2. **The eight wrapper-launching setup tests come from `sandbox-ref-18`.** They are taken from `tests/test_setup.py` at that tag into `tests/test_setup_wrapper.py`, together with their helpers (`pty_run`, the fake engine, setUp, release and answers). They use the real profile and wrapper and keep Claude's semantics: missing-mode refusal, provider and login prompts.
   - The real setup modules run in a subprocess, as in the reference's version, because the test process has already imported the fixture modules.
   - The reference's `tests/test_setup_wrapper.py` is the template for that structure. Its shell-specific assertions are replaced by the `sandbox-ref-18` assertions.
3. **The parity table is fixed by hand after `--apply`.** The tool replaces every `sandbox-ref-18` in `docs/network-contract.md`, so the Codex, OpenCode, Pi and Antigravity rows would wrongly read `sandbox-ref-20`. Those rows are restored, a `Sandbox (reference)` row is added as in `sandbox-container`, and the Claude row becomes `Ported from sandbox-ref-20`. This repeats in each adoption until all wrappers are on the same tag.
4. **The lifetime notice is ported from the reference.** Elapsed time is measured with `EPOCHREALTIME`, and a boundary test is added to `tests/test_wrapper.py`. It is a per-agent launcher fix with no tag; the existing requirement ("prints no lifetime notice" before the limit) already covers it, so there is no spec delta.
5. **Reference-only removals.**
   - `tools/propagate.py`, `tests/test_propagate.py` and `docs/propagation.md` are deleted.
   - `reference-propagation` is retired with `retire_capabilities: true`, so archive deletes its main spec.
   - README, `AGENTS.md` and `docs/network-contract.md` point to `sandbox-container` for propagation.

## Risks / Trade-offs

- [The shared tests read the real profile somewhere Claude-specific] → `test_alignment` forbids reads of the checkout profile outside the documented readers; the full runner set exercises the rest.
- [`--container-setup` changes] → Shared setup code changed, so the qualification identity changes and every Claude installation must rerun setup. The newer WSL host needs host CA trust.

## Migration Plan

1. Branch.
2. Add the manifest and commit it on `main`'s state; the tool requires a clean tree with the manifest committed.
3. Run the tool's dry run from `sandbox-container`, then `--apply`.
4. Make the per-agent adjustments.
5. Run all runner modes.
6. Merge.
7. The operator pushes and reruns setup on the three hosts.
8. Archive with sync.

Rollback: discard the branch; `main` stays on `sandbox-ref-18`.
