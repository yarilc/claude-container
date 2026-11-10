# Tasks

## 1. Wrapper

- [x] 1.1 In `claude-container.sh`, remove `--read-only-tmpfs=false` from
  `container_args` and add
  `--tmpfs '/dev:rw,nosuid,noexec,mode=755,size=65536k'`,
  `--mount type=devpts,destination=/dev/pts` and
  `--mount type=tmpfs,destination=/dev/shm,ro=true`, with a comment naming
  the crun `/dev/console` constraint. Verify with `bash -n` and by updating
  `tests/test_wrapper.py`: the `--read-only-tmpfs=false` assertion becomes
  its absence, and the new test asserts the three mounts in every mode
  (default, shell, worktree, delegated, provider), with and without a TTY.

## 2. Runtime verification

- [x] 2.1 On this host, start the runtime image with the wrapper's arguments
  and a TTY (`script -qec`). Verify that `tty` reports a pts, `/dev/shm` is
  read-only, a copied executable cannot run from `/dev`, and `/tmp`, `/run`
  and `/var/tmp` keep `nosuid,nodev,noexec`.
- [x] 2.2 Run `test_wrapper.py`, `test_session.py` and `test_alignment.py`
  against `main`, plus `bash tests/run-runtime.sh --qualification`. Verify
  that there are no new failures.

## 3. Documentation

- [x] 3.1 Update `README.md` (temporary storage section) and `AGENTS.md`
  (security rule on `noexec` tmpfs) to describe the explicit `/dev`,
  `/dev/pts` and `/dev/shm` mounts and the Podman 5 writable `/dev`
  relaxation. Add a `docs/validation.md` entry with the lab-host probe matrix
  and a Pending row for interactive login. Verify with `git diff --check`.

## 4. Lab host

- [x] 4.1 Have the operator rerun `--container-setup` and accept login.
  Verify that the login session attaches a terminal and that the launch
  reaches the agent. Record the result in `docs/validation.md`.

## Workflow follow-up

- Apply the same launcher adaptation in the sibling wrappers.
