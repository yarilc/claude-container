# Tasks

## 1. Shared module, test first

- [x] 1.1 On a branch `share-toolchain-env-across-profiles` from `main`, add
  to `tests/test_toolchains.py` (design decision 4):
  - the `bus variable` rejected-recipe case;
  - a `launch_env` case with a profile variable in the index;
  - a `launch_env` case with `DBUS_SESSION_BUS_ADDRESS` in the index.

  Verify that the new cases fail on the current module.
- [x] 1.2 Split the protected names and change `launch_env` in
  `setup/toolchains.py` (design decisions 1 and 2). Verify that
  `python3 -m unittest tests.test_toolchains tests.test_alignment
  tests.test_agent_profile` passes on private temporary storage.

## 2. Documentation

- [x] 2.1 Describe the neutral and profile groups and the bus variable in the
  README "Protected variables" bullet. Verify with
  `grep -n DBUS_SESSION_BUS_ADDRESS README.md`.

## 3. Validation and publication

- [x] 3.1 Run the full unit discovery on executable, private, native
  temporary storage. Verify that there are no failures, apart from known
  timing-sensitive tests that pass on a rerun.
- [x] 3.2 Run `bash tests/run-runtime.sh` with `--shared`, `--setup`,
  `--setup-runtime`, `--qualification`, `--wrapper` and the default mode
  (`docs/propagation.md` step 1; `setup/toolchains.py` is in
  `SHARED_CODE`). Verify that each passes.
- [x] 3.3 Add a `docs/validation.md` section for `sandbox-ref-17` with the
  results of 1.1–3.2, the Podman `--unsetenv` observation and the
  requalification note, and update the parity cells in
  `docs/network-contract.md` to `sandbox-ref-17`. Verify that
  `git diff --check` is clean and
  `openspec validate share-toolchain-env-across-profiles --strict` passes.
- [x] 3.4 Commit with the co-author trailer, merge into `main` with `--no-ff`,
  and create the annotated tag `sandbox-ref-17`. Verify that
  `git cat-file -t sandbox-ref-17` prints `tag`, and that a dry run of
  `tools/propagate.py ../codex-container sandbox-ref-16 sandbox-ref-17`
  lists only `setup/toolchains.py` and `tests/test_toolchains.py`, with
  nothing "not adopted".

## Workflow follow-up

- The operator pushes `main` and `sandbox-ref-17` and reruns
  `--container-setup` on this host, the Rocky Linux 9 lab host and the newer
  WSL host.
- Sync the delta spec and archive this change.
- Update Antigravity's `adopt-sandbox-ref-16` to target `sandbox-ref-17`, and
  propose `adopt-sandbox-ref-17` in Codex, OpenCode and Pi.
