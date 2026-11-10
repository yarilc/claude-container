# Tasks

## 1. Mask

- [x] 1.1 In `claude-container.sh`, add
  `--mount type=tmpfs,destination=/run/secrets,ro=true` to the common agent
  container arguments. Verify with a `tests/test_wrapper.py` case asserting
  the mask in default, shell, worktree, delegated and provider launches,
  plus `bash -n`.
- [x] 1.2 In `network/session.py`, add the same mask to the proxy create
  arguments. Verify with `tests/test_session.py` that the proxy create
  includes it.

## 2. Guard

- [x] 2.1 In `network/guard.c` `verify_mount_layout()`, parse the per-mount
  options and the filesystem type, and accept `/run/secrets` only as a
  read-only tmpfs. Every other nested mount keeps failing. Verify by
  building the guard with `bash tests/run-runtime.sh --guard` (or the
  toolchain build) and running `tests/test_guard.py`. Add cases where the
  read-only tmpfs mask is accepted, while a writable tmpfs at `/run/secrets`,
  a read-only host bind at `/run/secrets` and the existing
  `/tmp/untrusted-nested` bind are all rejected before exec.

## 3. Documentation and regression

- [x] 3.1 Document the mask in `README.md` (mounts section) and
  `docs/network-contract.md` (bootstrap mount validation). Verify with
  `git diff --check`.
- [x] 3.2 Run `test_wrapper.py`, `test_session.py`, `test_alignment.py` and
  `test_guard.py` against `main`, plus
  `bash tests/run-runtime.sh --qualification` on this host. Verify that
  there are no new failures and that qualification passes with the mask.
- [ ] 3.3 On the lab host, have the operator rerun `--container-setup`
  (provider, refresh). Verify that the setup reaches `Sandbox: ready`, then
  record the results in `docs/validation.md` and close the pending operator
  tasks of the earlier changes.

## Workflow follow-up

- Propagate `network/guard.c` and `network/session.py` to the sibling
  wrappers.
