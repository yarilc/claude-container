# Tasks

## 1. Agent variables in the profile (shared)

- [x] 1.1 On branch `harden-shared-session-boundaries`, move the neutral
  protected names and prefixes into `network/agent_profile.py`, and have
  `setup/toolchains.py` import them. Verify that
  `python3 -B -m unittest tests.test_toolchains tests.test_agent_profile`
  still passes unchanged.
- [x] 1.2 Add optional `native.protected_env` to the profile loader: names
  `[A-Z][A-Z0-9_]*`, prefixes ending in `_` with at least three characters, no
  duplicates, no neutral names or prefixes. Expose it on `Profile`. Add
  `tests/test_agent_profile.py` cases for a valid list, each invalid form and
  a missing list. Verify that they pass.
- [x] 1.3 Fold the declared names and prefixes into `PROFILE_PROTECTED` in
  `setup/toolchains.py`. Add `tests/test_toolchains.py` cases: `add` rejects an
  agent name and a name under an agent prefix; `launch-env` skips both from an
  existing index with one warning naming the toolchain. Verify that they pass.
- [x] 1.4 Declare Claude's values in `agent/profile.json` (`CLAUDE_CODE_`,
  `ANTHROPIC_`, `DISABLE_TELEMETRY`, `DISABLE_AUTOUPDATER`,
  `DISABLE_ERROR_REPORTING`, `ENABLE_CLAUDEAI_MCP_SERVERS`). Add a
  `tests/test_wrapper.py` case in which a default toolchain sets
  `ANTHROPIC_BASE_URL` and `CLAUDE_CODE_USE_BEDROCK` and the session receives
  neither. Verify that it passes.
- [x] 1.5 Update the README "Protected variables" bullet and the profile row
  of `docs/network-contract.md` with the agent variables. Verify with
  `grep -n 'protected_env\|CLAUDE_CODE_' README.md docs/network-contract.md`.

## 2. Working directory

- [x] 2.1 Add `'--workdir', '/'` to `toolchains.check()`, and extend the
  `tests/test_toolchains.py` case that inspects the check command to assert
  it. Verify that it passes.
- [x] 2.2 Create `/workspace` in the `Containerfile` package step, and port
  `workdir_violations` and its tests from Codex `tests/test_image_pins.py`.
  Verify that the test fails on the old recipe and passes on the new one.

## 3. State and workspace overlap

- [x] 3.1 In `setup/common.py` `writable_mounts()`, reject an isolated state
  directory that equals, contains or lies inside the workspace (resolved,
  parent in worktree mode). Add `tests/test_setup.py` cases for each relation,
  a symlinked state path and worktree mode. Verify that they pass.
- [x] 3.2 Add the same check to `claude-container.sh`, before engine
  operations, with the error `CLAUDE_CONTAINER_STATE_DIR must not overlap the
  workspace: <path>`. Add `tests/test_wrapper.py` cases (inside, containing,
  symlink) that assert no engine call. Verify that they pass.
- [x] 3.3 Document the rule in the README state section and in the usage
  text. Verify that `./claude-container.sh --help` shows it.

## 4. Signals and alignment tests

- [x] 4.1 Add `--sig-proxy=false` to both `podman start --attach` calls in
  `claude-container.sh`, and assert it in `tests/test_wrapper.py`. Verify that
  the signal-matrix tests still pass.
- [x] 4.2 In `tests/test_alignment.py`, replace the profile-variable check
  with a `missing_profile_names` helper that checks the code outside the
  `usage()` help text (except `SHARED_READ` names) and the help text for every
  prefix-derived variable (except `INTERNAL` names), as in design.md. Make the
  mismatch test call it on modified text (renamed, help-only and undocumented
  cases). Verify that the mismatch test fails when the helper always returns
  no names, and that the test passes here and on copies of the four adopters.

## 5. Validation, tag and publication

- [x] 5.1 Run the unit discovery on private executable temporary storage,
  then `bash tests/run-runtime.sh` with `--shared`, `--setup`,
  `--setup-runtime`, `--qualification`, `--wrapper` and the default mode.
  Verify that each passes; record a known timing-sensitive test that passes
  on a rerun as such. Do not tag while a mode fails.
- [x] 5.2 Add a `sandbox-ref-18` section to `docs/validation.md` with the
  modes, results, review findings covered (H1 shared part, M3, M4, the Claude
  part of M2, L2) and the requalification note. Update the parity table cells
  to `sandbox-ref-18`. Verify that `git diff --check` is clean and
  `openspec validate harden-shared-session-boundaries --strict` passes.
- [x] 5.3 Commit with the co-author trailer, merge into `main` with `--no-ff`,
  and create the annotated tag `sandbox-ref-18` on the merge. Verify with
  `git describe --tags` and `python3 -I tools/propagate.py ../codex-container
  sandbox-ref-17 sandbox-ref-18` (dry run only) listing the changed shared
  files.

## Workflow follow-up

- The operator pushes `main` and the tag, and reruns `--container-setup` on
  the restricted Claude installations.
- Sync the delta specs and archive this change.
- One adoption change per adopter: adopt `sandbox-ref-18`, declare its
  `protected_env`, and port the overlap check (Codex), the lifecycle recovery
  and ownership checks (Codex, Pi, Antigravity; collision check in OpenCode).
