# Tasks

## 1. Shared module, test first

- [x] 1.1 On a branch `protect-xdg-toolchain-variables` from `main`, add the
  `xdg variable` rejected-recipe case (`XDG_DATA_HOME`) and a `launch_env`
  case with an index entry carrying `XDG_CONFIG_HOME` to
  `tests/test_toolchains.py` (design decision 2). Verify that both fail on
  the current module.
- [x] 1.2 Add `'xdg_'` to `PROTECTED_PREFIXES` in `setup/toolchains.py`
  (design decision 1). Verify that `python3 -m unittest tests.test_toolchains
  tests.test_alignment` passes on private temporary storage.

## 2. Documentation

- [x] 2.1 Name XDG variables in the README "Protected variables" bullet.
  Verify with `grep -n XDG README.md`.

## 3. Validation and publication

- [x] 3.1 Run the full unit discovery on executable, private, native
  temporary storage. Verify that there are no failures, apart from known
  timing-sensitive tests that pass on a rerun.
- [x] 3.2 Run `bash tests/run-runtime.sh` with `--setup`, `--setup-runtime`,
  `--qualification`, `--wrapper` and the default mode (design decision 4).
  Verify that each passes.
- [x] 3.3 Add a `docs/validation.md` section for `sandbox-ref-15` with the
  results of 1.1–3.2 and the requalification note, and update the parity
  cells in `docs/network-contract.md` to `sandbox-ref-15`. Verify that
  `git diff --check` is clean and
  `openspec validate protect-xdg-toolchain-variables --strict` passes.
- [x] 3.4 Commit with the co-author trailer, merge into `main` with `--no-ff`,
  and create the annotated tag `sandbox-ref-15`. Verify that
  `git cat-file -t sandbox-ref-15` prints `tag`, and that a dry run of
  `tools/propagate.py ../opencode-container sandbox-ref-12 sandbox-ref-15`
  lists the shared files with nothing "not adopted".

## Workflow follow-up

- The operator pushes `main` and `sandbox-ref-15` and reruns
  `--container-setup` on this host, the Rocky Linux 9 lab host and the newer
  WSL host.
- Sync the delta spec and archive this change.
- Propose `adopt-sandbox-ref-15` in OpenCode (from `sandbox-ref-12`, with the
  library port) and a small adoption in Codex (from `sandbox-ref-14`).
