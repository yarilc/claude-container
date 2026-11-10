# Proposal

## Why

Waves 1–3 are complete: Codex, OpenCode, Pi and Antigravity run the shared `network/`, `setup/` and shared tests from this repository's tag `sandbox-ref-9`, byte-identical, with an identical five-wrapper parity table. Wave 4 is propagation: every later change here produces a new `sandbox-ref-N` that the other wrappers must adopt.

During Wave 3 each adoption (`sandbox-ref-6` to `sandbox-ref-9`, three or four repositories each) was done with a new ad hoc script. Each script:
- copied the changed files;
- rewrote the `tests/test_reference_copy.py` tag, commit and hashes;
- replaced tag references in the current-state documents.

The same steps, done by hand, risk a missed file, a stale hash, or a historical record rewritten by a blind replace. The operator chose on 2026-11-10 to limit Wave 4 to a documented, reusable procedure.

## What Changes

- Add `tools/propagate.py`, a reference-only tool in this repository, never copied to the other wrappers. Given a target checkout and two tags, it:
  - checks the preconditions:
    - the target's git tree is clean;
    - its `tests/test_reference_copy.py` names the old tag and the old tag's commit;
    - both tags exist here;
    - the target's copied files equal the old tag;
  - computes the shared file changes between the tags (modified, added, removed) within the target's adopted scope;
  - in the default dry run, prints the plan;
  - with `--apply`, on a new `adopt-<tag>` branch:
    - copies the files from the new tag;
    - deletes the removed ones;
    - rewrites `REFERENCE_TAG`, `REFERENCE_COMMIT` and the manifest;
    - updates the tag and commit references in the current-state documents only, never in `docs/validation.md`, `CHANGELOG.md` or archived OpenSpec changes;
  - prints the suites to run, a validation-record section to fill in, and a commit message.
- Add `docs/propagation.md`, the Wave 4 procedure:
  1. when a change here needs a new tag;
  2. creating the tag;
  3. running the tool in each wrapper;
  4. running the listed suites;
  5. recording the results;
  6. committing and merging;
  7. updating the parity table;
  8. what to do when an adoption fails (fix here first, under a new tag).
- Link the procedure from the port checklist in `docs/network-contract.md`, the README and `AGENTS.md`.
- Add `tests/test_propagate.py`: credential-free unit tests on temporary git repositories, covering the plan, the preconditions, the apply step, the scope rules and the document rules.

Out of scope, as the operator decided:
- closing the current "Residual exfiltration" documentation drift in Codex, OpenCode and Pi;
- a cross-repository parity check;
- the final branch cleanup.

## Capabilities

### New Capabilities

- `reference-propagation`: the documented procedure and tool that propagate a new reference tag of the shared components to the other wrappers, with verified preconditions, exact copies, manifest and reference updates, and the verification checklist.

### Modified Capabilities

None. The shared components and their alignment checks are unchanged.

## Impact

- **New files:** `tools/propagate.py`, `docs/propagation.md`, `tests/test_propagate.py`.
- **Documentation:** the README, `AGENTS.md` and the port checklist in `docs/network-contract.md`.
- **No change** to `network/`, `setup/`, the shared tests, the wrapper or the image. No new tag is needed: the tool and procedure are not shared files.
- **Other repositories:** none in this change. The tool is exercised against copies of their checkouts in a dry run, as a smoke test.
