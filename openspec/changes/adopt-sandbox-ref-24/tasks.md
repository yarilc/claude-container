# Tasks

## 1. Adopt `sandbox-ref-24`

- [x] 1.1 Commit this change directory on `main`. From `sandbox-container`, run `python3 -I tools/propagate.py ../claude-container sandbox-ref-23 sandbox-ref-24` (dry run), then `--apply`. Verify that:
  - the plan lists exactly the files in design "Context";
  - the tool switched to `adopt-sandbox-ref-24`.
- [x] 1.2 Fix the parity table in `docs/network-contract.md` by hand (design decision 3): the reference row names `sandbox-ref-24` and the Codex row equals the one in `codex-container`. Leave the Claude row for task 2.2. Verify that `python3 -m unittest tests.test_reference_copy tests.test_alignment` passes with host Python next to the `sandbox-container` checkout, with the sibling check not skipped.

## 2. Validation and integration

- [ ] 2.1 In the disposable test container, run the unit discovery. Then run `bash tests/run-runtime.sh` with `--wrapper` and `--setup`, the default runtime run, and `git diff --check` (design decision 4). Verify that all pass. If a Claude wrapper test fails, pause the change (design decision 2).
- [ ] 2.2 Set the Claude row to "Adopted `sandbox-ref-24`" with the runner result of task 2.1. Add the `sandbox-ref-24` adoption section to `docs/validation.md`, starting from the tool's template, with every result of task 2.1. Commit with the tool's message and merge into `main`. Verify that `tests/test_reference_copy.py` passes on `main` with host Python.
- [ ] 2.3 In `sandbox-container`, set the reference row to `sandbox-ref-24` and copy the Claude row byte for byte from `claude-container` (design decision 3). Commit on `main`. Verify that the reference, Claude and Codex rows are identical in `sandbox-container`, `claude-container` and `codex-container`.

## Workflow follow-up

- The operator pushes `main` in `claude-container` and `sandbox-container`, then runs `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host.
- Archive this change with spec sync.
- The reference and Claude rows in `codex-container` are refreshed at Codex's next change.
- Antigravity and Pi adopt `sandbox-ref-24` in their own changes, and OpenCode after them.
