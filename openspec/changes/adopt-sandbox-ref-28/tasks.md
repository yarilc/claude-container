# Tasks

## 1. Adopt `sandbox-ref-28`

- [x] 1.1 Check that `sandbox-ref-28` exists in `sandbox-container`, then commit this change directory on `main`. From `sandbox-container`:
  - run `python3 -I tools/propagate.py ../claude-container sandbox-ref-25 sandbox-ref-28` (dry run), then `--apply`.

  Verify:
  - the plan lists the files in design "Context";
  - the checklist includes `--guard`;
  - the tool switched to `adopt-sandbox-ref-28`.
- [x] 1.2 Copy `sandbox-container.ps1` to `claude-container.ps1` byte for byte. Copy `.gitattributes`, commit both, and rewrite the working files with LF (design decision 2). Verify:
  - `git status` is clean after the renormalization;
  - with host Python next to the `sandbox-container` checkout, the sibling check not skipped, `python3 -m unittest tests.test_reference_copy tests.test_alignment` passes, including the entry, ASCII and line-ending tests.
- [x] 1.3 Add the reference header to `agent/launcher.sh` (design decision 3). Verify: `bash tools/shellcheck.sh ../claude-container`, run from `sandbox-container`, reports no finding. `bash tools/powershell.sh ../claude-container` passes the shim cases with no finding.

## 2. Claude's tests and documentation

- [x] 2.1 Run the unit discovery in the disposable test container, then `bash tests/run-runtime.sh` with:
  - `--wrapper`, `--setup` and `--setup-runtime`;
  - `--qualification`, `--guard` and `--network`;
  - no mode, for the default runtime run.

  Use a matching `setup-*` image through `CLAUDE_CONTAINER_IMAGE` when `latest` is missing (design decision 6). Fix any failure in Claude's own tests caused by a shared behavior change (design decision 4). Verify: every mode passes, apart from failures already recorded for this runner. A failure in shared code pauses the change.
- [x] 2.2 Adapt the documentation (design decision 5):
  - `README.md`: the Windows section, the install as a command, host CA trust on Windows, the Windows limits with Bitdefender, the rlimit fallback and `cgroupfs` budgets, and the "Podman Machine" sentence;
  - `docs/setup.md`: the Windows setup, the authentication steps from Windows, the setup output and candidate tags, the service endpoint for restricted modes, and the budget plan;
  - `AGENTS.md`: `claude-container.ps1` and the Windows files.

  Verify:
  - the README names `claude-container.ps1`, `$env:ANTHROPIC_API_KEY`, `claude-container.ps1 auth login --claudeai` and `podman machine set --import-native-ca`;
  - no `SANDBOX_CONTAINER_` name or reference-only statement appears in the new text;
  - `git diff --check` passes.

## 3. Validation on Windows

- [x] 3.1 Prepare the operator bundle: snapshots of `claude-container` and `sandbox-container`, and a README with the steps of design decision 7. Verify: the README lists each step, the summary copies and the data to send back, and the checksums match.
- [x] 3.2 Have the operator run design decision 7. Verify that `docs/validation.md` records:
  - the setup with the declined login and its Windows next step;
  - the login;
  - the Claude session and Ctrl+C;
  - `windows-validate` on both editions, with `-Install -StopMachine` once;
  - the API key check, or that it is unavailable.

  No case fails. Otherwise the change pauses for a decision.

## 4. Record, merge and parity

- [x] 4.1 Add the `sandbox-ref-28` adoption section to `docs/validation.md`, from the tool's template, with every result of tasks 2.1 and 3.2. Set Claude's parity row to "Adopted `sandbox-ref-28`", and copy the reference row from `sandbox-container`. Commit with the tool's message and merge into `main`. Verify: `tests/test_reference_copy.py` passes on `main`.
- [ ] 4.2 Copy Claude's parity row into `sandbox-container`, `codex-container`, `antigravity-container`, `opencode-container` and `pi-container`, one commit on `main` each. Verify: the reference and Claude rows are identical in the six repositories.

## Workflow follow-up

- The operator pushes `main` in every touched repository and reruns `--container-setup` for Claude on the Linux hosts and on Windows.
- Archive this change with spec sync.
