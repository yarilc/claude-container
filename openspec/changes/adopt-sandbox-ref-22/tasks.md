# Tasks

## 1. Adopt `sandbox-ref-22`

- [x] 1.1 Commit this change directory on `main` and create `prepare-adopt-sandbox-ref-22`. Then, from `sandbox-container`, run `python3 -I tools/propagate.py ../claude-container sandbox-ref-21 sandbox-ref-22` (dry run) and `--apply`. Verify that:
  - the plan lists exactly the files in design "Context";
  - the tool switched to `adopt-sandbox-ref-22`.
- [x] 1.2 Fix the parity table in `docs/network-contract.md` by hand (design decision 6). Verify that:
  - the reference row equals `sandbox-container`'s;
  - the Codex, Antigravity, OpenCode and Pi rows equal their own repositories'.

## 2. Launcher on the shared core

- [x] 2.1 Save the current `tests/test_wrapper.py` and `claude-container.sh` outside the repository as the old-test baseline. Write `agent/launcher.sh` (design decision 2) and replace `claude-container.sh` with the reference entry script. Verify that:
  - `python3 -m unittest tests.test_alignment tests.test_launcher` passes in the disposable test container;
  - `bash claude-container.sh --container-help` prints the provider disclosure with Claude's hosts;
  - `diff <(sed s/sandbox-container/claude-container/g ../sandbox-container/sandbox-container.sh) claude-container.sh` is empty.
- [x] 2.2 Run the saved `tests/test_wrapper.py` against the new entry script and core in the disposable test container. Classify every failing case as (a) visible change, (b) lost behavior or (c) Claude-only behavior (design decision 3), and resolve the six "to verify at adoption" cases by name. Record the table in a scratch note for task 4.2. Verify that every failing case has exactly one outcome.
- [x] 2.3 If task 2.2 found any (b), pause this change. Fix each behavior with a shared case in `sandbox-container` through its own reference change and tag, then rerun tasks 1.1 to 2.2 against the new tag. Update this change's artifacts to name that tag. Verify that a rerun of task 2.2 finds no (b). If task 2.2 found none, mark this task done with the note "no lost behavior".
  - Done: the old tests found no lost behavior; the reference defect found by task 2.1 (Claude identifiers in the shared `tests/test_launcher.py`) was fixed in `fix-shared-test-identifiers` and tagged `sandbox-ref-23`, adopted on `adopt-sandbox-ref-23`. `launcher/core.sh` is unchanged between the tags, so the task 2.2 classification stands. `tests/test_reference_copy.py` now treats `launcher/` as a closed directory.

## 3. Claude tests and documentation

- [x] 3.1 Rewrite `tests/test_wrapper.py` with the shared `tests/fake_podman.py` and the real agent part (design decision 4). It covers:
  - the three hook cases;
  - the provider-only settings in each mode;
  - `ANTHROPIC_API_KEY` with each policy profile, including a `CLAUDE_CONTAINER_ENV_VARS` attempt under `anthropic-account`;
  - the help disclosure;
  - every outcome (c) from task 2.2.

  Verify that `python3 -m unittest tests.test_wrapper` passes in the disposable test container.
- [x] 3.2 Update the wrapper-owned runtime tests (design decision 5): `tests/run-runtime.sh`, `tests/test_runtime.py`, `tests/test_network_runtime.py`, `tests/test_setup_runtime.py` and `tests/test_setup_wrapper.py`. Verify that `python3 -m unittest tests.test_setup_wrapper` passes in the disposable test container and that `bash -n tests/run-runtime.sh` succeeds.
- [ ] 3.3 Update the README, `docs/setup.md`, `docs/network-contract.md` and `AGENTS.md` (design decision 6). Cover:
  - the provider default, without the `c777b73` history;
  - temporary storage and the tmpfs home;
  - `CLAUDE_CONTAINER_ENV_VARS` and `CLAUDE_CONTAINER_READONLY_STATE`;
  - credentials;
  - build-only and stale images;
  - the launcher core.

  Verify that `grep -rn "c777b73\|256/16/256\|256 MiB\|refuses an ordinary launch" --exclude-dir=openspec --exclude=validation.md .` finds nothing stale.

## 4. Integration

- [ ] 4.1 Rebuild the Claude test image with `--container-build`. Then run:
  - the unit discovery in the disposable test container;
  - `bash tests/run-runtime.sh` with `--wrapper`, `--setup`, `--setup-runtime`, `--qualification`, `--network` and `--guard`, and the default mode;
  - `tests/image-smoke.sh`;
  - `git diff --check`.

  Verify that all pass.
- [ ] 4.2 Add the `sandbox-ref-22` and `sandbox-ref-23` adoption section to `docs/validation.md`, starting from the tool's template. It holds every result and the old-test classification table from task 2.2. Commit with the tool's message and merge into `main`. Verify that `tests/test_reference_copy.py` passes on `main` with host Python next to the `sandbox-container` checkout, with the sibling check not skipped.

## Workflow follow-up

- The operator pushes `main` and runs `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host, then checks a Claude session in provider mode.
- Archive this change with spec sync. This creates `openspec/specs/shared-launcher/spec.md` in this repository.
- Then Codex, Antigravity and Pi adopt `sandbox-ref-23` in their own changes, and OpenCode after them.
