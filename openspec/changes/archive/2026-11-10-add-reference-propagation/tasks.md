# Tasks

## 1. Propagation tool

- [x] 1.1 Add `tools/propagate.py` (standard library and `git` only). It reads tags with `git ls-tree` and `git show`, and the shared set from each tag's `tests/test_alignment.py`. It parses the target's `tests/test_reference_copy.py` as text, without importing it. It computes the modified, added, removed and not-adopted sets with the scope rules of design.md.
- [x] 1.2 Implement the preconditions:
  - clean target tree;
  - manifest tag and commit equal to the old tag;
  - both tags present;
  - adopted files equal to the old tag;
  - no existing `adopt-<new>` branch.

  Each failure exits nonzero, names the condition and writes nothing.
- [x] 1.3 Implement the dry run (default) and `--apply`:
  - branch creation;
  - atomic file writes and deletions;
  - manifest rewrite (`REFERENCE_TAG`, `REFERENCE_COMMIT`, hashes), keeping every other line;
  - whole-word tag and full-commit replacement in `README.md`, `AGENTS.md`, `CONTRIBUTING.md`, `docs/setup.md` and `docs/network-contract.md` only.
- [x] 1.4 Implement the checklist: runner modes detected from the target's `tests/run-runtime.sh` and selected by the changed files, a validation-section template, and a commit message. Verify that the tool never commits, merges, tags or pushes.

## 2. Tests

- [x] 2.1 Add `tests/test_propagate.py` with temporary git repositories: a reference with two annotated tags and a target built from a real wrapper's `tests/test_reference_copy.py` format. Cover:
  - dry run without writes;
  - applied run, after which the target's reference copy check passes;
  - each precondition failure;
  - the partially adopted scope (an unadopted `setup/common.py`);
  - added and removed files;
  - history files unchanged;
  - whole-word tag matching (`sandbox-ref-1` vs `sandbox-ref-10`);
  - checklist selection for setup and network changes.
- [x] 2.2 Smoke the tool in a dry run against disposable clones of the four wrapper checkouts, using `sandbox-ref-8` to `sandbox-ref-9` with each clone reset to its pre-adoption commit. Compare the plan with the Wave 3 adoption commits. Then dry-run each clone at its current commit against a no-op pair (`sandbox-ref-9` to `sandbox-ref-9`), which must report no changes.

## 3. Documentation and verification

- [x] 3.1 Add `docs/propagation.md`:
  - when a change needs a new tag, and creating it as annotated;
  - running the tool per wrapper (dry run, review, apply);
  - running the listed suites;
  - recording the results with the template;
  - committing and merging per wrapper;
  - updating the parity rows;
  - the failure path (fix here under a new tag).

  Link it from the README, `AGENTS.md` and the port checklist in `docs/network-contract.md`.
- [x] 3.2 Final verification:
  - `tests/test_propagate.py`, `tests/test_alignment.py` and `tests/test_agent_profile.py`;
  - `bash tests/run-runtime.sh --setup` (unchanged);
  - `openspec validate add-reference-propagation --strict`;
  - markdownlint on the changed documents;
  - `git diff --check`.

  Record the results in `docs/validation.md`.

## Workflow follow-up

- `/opsx:archive`, then commit and merge into `main`; the user pushes.
- Possible later changes, outside this scope: the Residual exfiltration section in Codex, OpenCode and Pi; a cross-repository parity check; the final branch cleanup; then the operator-run authenticated checks.
