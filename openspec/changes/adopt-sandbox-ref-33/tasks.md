# Tasks

## 1. Adopt `sandbox-ref-33`

- [ ] 1.1 Check that `sandbox-ref-33` exists in `sandbox-container`, then commit this change directory on `main`. From `sandbox-container`, run `python3 -I tools/propagate.py ../claude-container sandbox-ref-28 sandbox-ref-33` (dry run), then `--apply`.

  Verify:
  - the plan lists the files in design "Context";
  - the tool switched to `adopt-sandbox-ref-33`;
  - `claude-container.ps1` and `.gitattributes` need no copy, because the tag does not change them.

## 2. Claude's tests and documentation

- [ ] 2.1 Rewrite Claude's delegation cases (design decision 2):
  - `tests/test_wrapper.py`;
  - `tests/test_runtime.py`, with the reference's `SessionEngineTests`;
  - `tests/test_network_runtime.py`, with the reference's engine cases and the profile's engine image, and the reference's `/proc/net/dev` interface checks;
  - `tests/test_setup_wrapper.py` and `tests/test_setup_runtime.py`;
  - `tests/run-runtime.sh`.

  Verify:
  - the unit discovery passes in the spike engine, on a native copy of the checkout;
  - `grep -rn "_PODMAN_SOCKET\|podman.sock" tests/` finds only refusal or absence checks and the launch service endpoint.
- [ ] 2.2 Remove `docs/toolchains/`, which the release catalog replaces (design decision 3).
- [ ] 2.3 Adapt the documentation to the tag, with Claude's names:
  - `README.md`:
    - the container test section, with the host `/sys` view of sessions with an engine;
    - the toolchain section, with catalog names and images;
    - the removal of delegation, with migration;
    - the security statements on the Podman socket;
  - `AGENTS.md`: the delegation rules become the engine rules;
  - `docs/setup.md`: the removed delegation question, schema 3 preferences and the engine image.

  Verify:
  - `grep -n "PODMAN_SOCKET\|PODMAN=1" README.md AGENTS.md docs/setup.md` finds only the migration refusal;
  - no `SANDBOX_CONTAINER_` name appears in the new text;
  - `git diff --check` passes.
- [ ] 2.4 Run the repository checks from `sandbox-container`, with the spike engine:
  - `tools/shellcheck.sh ../claude-container`;
  - `tools/powershell.sh ../claude-container`.

  Verify: no finding, and every shim case passes. Then commit the adoption on `adopt-sandbox-ref-33`, without merging.

## 3. Validation from a Claude session with its engine

- [ ] 3.1 Have the operator run design decision 4:
  - setup from Windows on the branch;
  - the image toolchains;
  - a new Claude session.

  Verify:
  - in the new session, `CONTAINER_HOST=tcp://127.0.0.1:2375`;
  - `podman info` reports rootless operation;
  - `podman images` lists the library images.
- [ ] 3.2 From that session, run `bash tests/run-runtime.sh` with:
  - `--wrapper`, `--setup`, `--setup-runtime` and `--qualification`;
  - `--network`;
  - no mode, for the default runtime run.

  Verify:
  - every mode passes, apart from the `cgroupfs` budget failures recorded for this machine;
  - a nested level that runs out of subordinate IDs is recorded with its measured range.

  A failure in shared code pauses the change.
- [ ] 3.3 Have the operator run `.\tools\windows-validate.ps1 -Checkout C:\Work\yarilc-github\claude-container` from `sandbox-container`, on Windows PowerShell 5.1.

  Verify: no case fails, and "Session with library images" passes for Claude.

## 4. Record, merge and parity

- [ ] 4.1 Add the `sandbox-ref-33` adoption section to `docs/validation.md`, from the tool's template, with every result of tasks 2 and 3. Set Claude's parity row to "Adopted `sandbox-ref-33`", and copy the reference row from `sandbox-container`. Commit with the tool's message and merge into `main`.

  Verify: `tests/test_reference_copy.py` passes on `main`.
- [ ] 4.2 Copy Claude's parity row into `sandbox-container`, `codex-container`, `antigravity-container`, `opencode-container` and `pi-container`, one commit on `main` each.

  Verify: the reference and Claude rows are identical in the six repositories.

## Workflow follow-up

- The operator pushes `main` and the tags in every touched repository.
- From the new session, finish the reference change: its tasks 7.1 and 8.1 run the reference suites through the engine.
- Archive this change with spec sync, which retires `container-podman-access`.
