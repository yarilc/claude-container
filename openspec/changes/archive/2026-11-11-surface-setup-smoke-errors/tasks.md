# Tasks

## 1. Profile field

- [x] 1.1 In `network/agent_profile.py`:
  - accept the optional `native.private_shared_dirs`; reject any value that is not a JSON boolean;
  - expose it as `PROFILE.private_shared_dirs` (default `False`).

  In `tests/test_agent_profile.py`:
  - the repository profile loads with the default;
  - `true` and `false` are accepted;
  - `1`, `"true"` and `null` fail validation.

  Verify with `python3 -m unittest tests.test_agent_profile tests.test_alignment`. The `test_alignment` check also confirms that no agent identifier was added to shared files. This repository's runner has no `--shared` mode.

## 2. Setup state checks and refusal message

- [x] 2.1 In `setup/common.py` `private()`, report the first failing reason: not a directory, owner, group/other mode (octal mode plus `chmod 700 <path>` or native Linux storage), or access. Keep `existing permissions were not changed.` at the end.

  In `tests/test_setup.py`, add one case per reason, asserting the message content and that the mode is unchanged (for example `755` stays `755`).
- [x] 2.2 In `prepare_state()`, call `private()` for every shared directory when `PROFILE.private_shared_dirs` is true, and keep the current accessibility check otherwise. Return which paths passed `private()`, so that the setup summary labels only those as `private`; the others are labeled `shared`.

  In `tests/test_setup.py`, with the profile attribute patched to true and to false:
  - a `755` shared directory is refused with its path under true, and accepted under false;
  - a refusal happens before any image operation (no engine call recorded);
  - the summary labels match.

  Verify with `bash tests/run-runtime.sh --setup`.

## 3. Smoke diagnostics

- [x] 3.1 In `setup/setup.py`:
  - add the bounded, sanitized stderr excerpt to `run()` behind an `excerpt` flag: last 5 non-empty lines, printable characters only, 2048 characters per line, prefixed `PREFIX + 'smoke: '`;
  - in `smoke_in()`, use it for the `--container-shell` launch, on a nonzero exit and when the readiness marker is missing.

  In `tests/test_setup.py`, using a fake command, assert:
  - a refusal line on stderr is printed before the `Setup command failed` message;
  - a missing marker prints the excerpt and the existing readiness error;
  - ANSI escapes, other control characters, more than 5 lines and over-long lines are stripped or bounded;
  - a successful smoke prints no excerpt.

  Verify with `bash tests/run-runtime.sh --setup`.

## 4. Documentation and release

- [x] 4.1 Update the documentation:
  - **`docs/setup.md`:** the smoke excerpt in the readiness section; the `private_shared_dirs` profile field and the actionable refusal in the state/paths section.
  - **`CHANGELOG.md`:** not applicable. This repository has no changelog; the validation record is the release note.
  - **`docs/validation.md`:** a section naming `sandbox-ref-10`, with the suite results.

  Verify with markdownlint (no new findings except MD013) and `git diff --check`.
- [x] 4.2 Final verification, all passing:
  - `python3 -m unittest tests.test_agent_profile tests.test_alignment`;
  - `bash tests/run-runtime.sh` with `--setup`, `--qualification` and `--setup-runtime`;
  - `bash -n` and ShellCheck on `claude-container.sh` (unchanged, regression only; its existing findings are recorded);
  - `openspec validate surface-setup-smoke-errors --strict`.

  Record the results in `docs/validation.md`.

## Workflow follow-up

- `/opsx:archive`, then commit and merge into `main`, and create the annotated tag `sandbox-ref-10` on the merge commit (`docs/propagation.md` step 1). The user pushes.
- For each wrapper, run `python3 -I tools/propagate.py ../<wrapper> sandbox-ref-9 sandbox-ref-10`: first the dry run, then `--apply`.
  - For Pi and OpenCode, also set `native.private_shared_dirs: true` in `agent/profile.json` on the adoption branch, and update their documentation of the setup refusal.
  - Run the runner modes that the tool lists, then merge each branch.
- Update the memory/parity notes. The operator then reruns Pi setup to confirm that the `~/.agents` case is refused early with the `chmod 700` fix.
