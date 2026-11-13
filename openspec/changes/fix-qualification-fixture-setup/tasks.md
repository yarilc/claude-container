# Tasks

## 1. Shared qualification fixture

- [x] 1.1 On a branch `fix-qualification-fixture-setup` from `main`, add the
  unit check of design decision 2: a module-level tuple of setup files used by
  the fixture, and a non-runtime test asserting that it contains every
  `setup/` entry of `SHARED_CODE`. Verify that the check fails while the tuple
  is empty or missing `setup/toolchains.py`.
- [x] 1.2 Make `QualificationRuntime.setUp` create `installed/setup` with mode
  `0700` and copy the tuple's files (`setup/common.py`,
  `setup/toolchains.py`) (design decision 1). Verify that
  `python3 -m unittest tests.test_qualification tests.test_alignment` passes
  and that `bash tests/run-runtime.sh --qualification` passes, with the six
  previously failing tests among them.

## 2. Procedure

- [x] 2.1 Rewrite the suite list in `docs/propagation.md` step 1 as in design
  decision 3: the checklist modes for the changed shared files, with the
  mapping, the `SHARED_CODE` qualification rule, and the record requirement.
  Verify that the step names `tools/propagate.py` and `--qualification`.

- [x] 2.2 Give `tests/run-runtime.sh` a private executable tmpfs (mode
  `0700`, `U=true`) and pass it as `SANDBOX_TEST_TMPDIR` (design decision 5).
  Verify that `bash tests/run-runtime.sh --wrapper` passes; it fails on `main`
  since `sandbox-ref-13`.

## 3. Validation and publication

- [x] 3.1 Run the full unit discovery on executable, private, native
  temporary storage. Verify that there are no failures, apart from known
  timing-sensitive tests that pass on a rerun.
- [x] 3.2 Run `bash tests/run-runtime.sh` with `--shared`, `--setup`,
  `--setup-runtime`, `--qualification`, `--guard`, `--network`, `--wrapper`
  and the default mode, using the current runtime image. Verify that each
  passes, or record it as unavailable.
- [x] 3.3 Add a `docs/validation.md` section for `sandbox-ref-14` with the
  results of 1.1–3.2, the cause found during the Codex adoption, and the note
  that no requalification is needed. Update the `Reference (...)` and
  `Ported from ...` cells of the parity table in `docs/network-contract.md` to
  `sandbox-ref-14`. Verify that `git diff --check` is clean and
  `openspec validate fix-qualification-fixture-setup --strict` passes.
- [ ] 3.4 Commit with the co-author trailer, merge into `main` with `--no-ff`,
  and create the annotated tag `sandbox-ref-14` on the merge commit. Verify
  that `git cat-file -t sandbox-ref-14` prints `tag`, and that a dry run of
  `tools/propagate.py ../opencode-container sandbox-ref-12 sandbox-ref-14`
  lists the shared files, including `tests/test_qualification.py`, with
  nothing "not adopted".

## Workflow follow-up

- The operator pushes `main` and `sandbox-ref-14`.
- Sync the delta spec and archive this change.
- `/opsx:update` the Codex change `adopt-sandbox-ref-13` to target
  `sandbox-ref-14`, then apply it; adopt `sandbox-ref-14` in OpenCode, Pi and
  Antigravity through their own changes.
