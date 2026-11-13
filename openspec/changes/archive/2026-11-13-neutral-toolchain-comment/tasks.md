# Tasks

## 1. Comment

- [x] 1.1 On a branch `neutral-toolchain-comment` from `main`, replace the
  comment in `setup/toolchains.py` as in the proposal. Verify that `git grep
  -n -i -E` with the identifiers of all five profiles finds nothing in
  `network/`, `setup/` and the shared tests (excluding `network/bin`).

## 2. Validation and publication

- [x] 2.1 Run the full unit discovery on private executable temporary storage,
  and `bash tests/run-runtime.sh --setup`, `--setup-runtime` and
  `--qualification` (the `docs/propagation.md` rule for `setup/` and a
  `SHARED_CODE` file). Verify that each passes.
- [x] 2.2 Add a `docs/validation.md` section for `sandbox-ref-16` with the
  results and the requalification note, and update the parity cells in
  `docs/network-contract.md` to `sandbox-ref-16`. Verify that
  `git diff --check` is clean and `openspec validate
  neutral-toolchain-comment --strict` passes.
- [x] 2.3 Commit with the co-author trailer, merge into `main` with `--no-ff`,
  and create the annotated tag `sandbox-ref-16`. Verify that
  `git cat-file -t sandbox-ref-16` prints `tag`, and that a dry run of
  `tools/propagate.py ../pi-container sandbox-ref-12 sandbox-ref-16` lists
  the shared files with nothing "not adopted". OpenCode's paused branch has
  uncommitted changes, so the tool refuses a dry run there; Pi has the same
  base tag.

## Workflow follow-up

- The operator pushes `main` and `sandbox-ref-16` and reruns
  `--container-setup` on the three hosts.
- Archive this change.
- `/opsx:update` OpenCode's `adopt-sandbox-ref-15` to target `sandbox-ref-16`.
