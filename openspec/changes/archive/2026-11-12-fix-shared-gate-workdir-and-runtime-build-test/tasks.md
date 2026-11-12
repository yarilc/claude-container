# Tasks

## 1. Qualification working directory

- [x] 1.1 Create branch `fix-shared-gate-workdir-and-runtime-build-test` from
  `main`. Add `--workdir /` to `Gate.common()` in `network/qualify.py`
  (design decision 1). Extend `test_gate_containers_mask_engine_default_secrets`
  to assert `--workdir /`. Verify with
  `python3 -m unittest tests.test_qualification -k gate`.
- [x] 1.2 Add `--workdir /` to the security-identity probe in
  `network/qualification_records.py` (design decision 2), with a unit test
  asserting it (design decision 4). Verify that the new test passes.

## 2. Shared setup test

- [x] 2.1 Pin `PROFILE.runtime_build` to `recipe` inside
  `test_runtime_build_receives_host_ca_only_when_trusted` (design decision 3).
  Verify that it passes as is, and that it also passes with the profile
  patched to `wrapper` for the duration of a one-off run.

## 3. Validation and publication

- [x] 3.1 Run the full unit discovery on executable, private, native
  temporary storage. Verify that there are no failures, apart from known
  timing-sensitive tests that pass on a rerun.
- [x] 3.2 Run `bash tests/run-runtime.sh --qualification` and `--setup`.
  Verify that both pass.
- [x] 3.3 Show the effect of `--workdir /` on a runtime image whose `WORKDIR`
  is in no layer (design, risks). Use the gate's common arguments with
  `--workdir /`: the container starts in `/` and `/workspace` does not
  exist. Without the flag, `/workspace` exists with the start time.
- [x] 3.4 Add a `docs/validation.md` section for `sandbox-ref-12` with the
  results of 3.1–3.3 and the requalification note. Update the parity table
  in `docs/network-contract.md` to `sandbox-ref-12`. Verify that
  `python3 -m unittest tests.test_alignment` passes.
- [x] 3.5 Commit with the co-author trailer, merge into `main` with `--no-ff`,
  and create the annotated tag `sandbox-ref-12` on the merge commit. Verify
  that `git cat-file -t sandbox-ref-12` prints `tag`, and that
  `tools/propagate.py ../pi-container sandbox-ref-10 sandbox-ref-12` (dry run)
  lists the shared files with nothing "not adopted".

## Workflow follow-up

- The operator pushes `main` and `sandbox-ref-12`.
- Update Pi's `adopt-lab-host-fixes` to target `sandbox-ref-12`, then apply it.
- Codex and OpenCode adopt `sandbox-ref-12`, and Antigravity adopts it with
  its lab-host port.
- Sync the delta spec and archive this change after review.
