# Design

## Context

Claude adopted `sandbox-ref-25` on 2026-11-18. Claude's runtime and egress
images are its own and stay as they are; the tag changes no build input.

**Dry run.** `tools/propagate.py` from `sandbox-ref-25` to `sandbox-ref-27`
(2026-11-22) gave this plan. `sandbox-ref-28` adds changes only to
`setup/setup.py` and `tests/test_setup.py`, which the plan already updates:
- **Update:**
  - `launcher/core.sh`;
  - `network/README.md`, `agent_budgets.py`, `control.py`, `guard.c`,
    `proxy_hardening.py`, `qualification_probe.py`,
    `qualification_records.py` and `session.py`;
  - `setup/common.py`, `launch.py`, `setup.py` and `smoke.py`;
  - `tests/fake_podman.py`;
  - both fixture `launcher.sh`;
  - `tests/test_alignment.py`, `test_guard.py`, `test_launcher.py`,
    `test_qualification.py`, `test_session.py` and `test_setup.py`.
- **Add:** the five `launcher/windows/` files, `tests/test_windows_bootstrap.py`,
  `tests/test_windows_enter.py` and `tests/windows/shim_tests.ps1`.
- **Rewrite:** 9 references in `docs/network-contract.md`.
- **Move:** the manifest to the tag's commit.
- **Runner modes listed:** the reference-copy and alignment tests, `--setup`,
  `--setup-runtime`, `--qualification` and `--network`.

**ShellCheck today.** On Claude's checkout, `tools/shellcheck.sh` reports
findings in:
- `launcher/core.sh` and both fixtures, which the tag replaces;
- `agent/launcher.sh`: 25 `SC2034` and 1 `SC2148`, because Claude's agent part
  has no `shell=bash` directive.

**Reference tools.** Claude forwards every non-`--container-*` argument to
`claude`. The `sandbox-ref-28` change `fix-windows-agent-guidance` fixes two
reference tools for this:
- `tools/windows-validate.ps1` uses `--container-shell -c` for an agent
  profile;
- `tools/propagate.py` finds Claude's `--guard`, which its form
  `"${1:-}" == --guard || …` hid from the 2026-11-22 dry run.

**Images.** The engine on this runner has no `localhost/claude-code:latest`,
only `setup-*` tags. The reference hit the same for its own image and
validated with an image whose `build-inputs-hash` matched.

## Goals / Non-Goals

**Goals:**

- Claude runs on the `sandbox-ref-28` shared files, with no Claude-specific
  code change beyond the ShellCheck header.
- Claude works from Windows on a Podman machine in provider mode, with the
  account login and the installer.
- The parity tables of the reference and the five wrappers state the same rows.

**Non-Goals:**

- Codex, Antigravity, OpenCode and Pi, which adopt the tag in their own
  changes.
- Delegation on Windows, macOS, and a real-key API check when no key is
  available.

## Decisions

1. **Adopt with the tool, from `sandbox-ref-25` directly, after
   `sandbox-ref-28` exists.** Commit this change directory on `main`, then run
   the dry run and `--apply`, which creates `adopt-sandbox-ref-28`.
   `sandbox-ref-26` and `sandbox-ref-27` are never adopted on their own: the
   tool works from the tags, and the validation covers all three.
2. **Hand-copied files on the same branch.**
   - `sandbox-container.ps1` becomes `claude-container.ps1` byte for byte.
   - `.gitattributes` is copied, then the working files are rewritten with
     `git rm -r -q --cached . && git reset --hard` on a clean tree.
   - The shared alignment tests then check the entry, ASCII and line endings.
3. **Claude's agent part.** Add the reference header to `agent/launcher.sh`:
   the comment that the core sources the file, and
   `# shellcheck shell=bash disable=SC2034,SC2154`. No hook changes. The
   requirement "Launcher files pass ShellCheck" then holds for Claude.
4. **Claude's tests.** Run them unchanged first. A failure from a shared
   behavior change, such as the setup output or the budget notices, is fixed
   in Claude's test on the same branch. A failure in shared code pauses the
   change for a reference fix and a new tag.
5. **Docs adapted, not copied.** Claude's README, `docs/setup.md` and
   `AGENTS.md` take the reference's text for the shared behavior, rewritten
   for Claude:
   - the provider default;
   - the account method's login, run by setup in the machine and stored in the
     machine user's `~/.claude`, separate from Claude Code on Windows;
   - `$env:ANTHROPIC_API_KEY` for the `api` method;
   - `claude-container.ps1`;
   - the `CLAUDE_CONTAINER_*` variables.

   The sentence "Podman Machine … unsupported" names the Windows entry. The
   rest of the README is unchanged.
6. **Validation scope.** These run on this runner, in Claude's checkout:
   - `python3 -m unittest tests.test_reference_copy tests.test_alignment` next
     to the `sandbox-container` checkout, with the sibling check not skipped;
   - the unit discovery in the disposable test container;
   - `bash tests/run-runtime.sh` with `--wrapper`, `--setup`,
     `--setup-runtime`, `--qualification`, `--guard` and `--network`, and the
     default runtime run;
   - `bash tools/shellcheck.sh ../claude-container` and
     `bash tools/powershell.sh ../claude-container` from `sandbox-container`;
   - `git diff --check`.

   If `localhost/claude-code:latest` is missing, use a `setup-*` image whose
   `build-inputs-hash` matches the current inputs, through
   `CLAUDE_CONTAINER_IMAGE`, and record it. If none matches, rebuild with
   `CLAUDE_CONTAINER_MAINTENANCE=1 --container-build`.
7. **Validation on Windows.** The operator gets a bundle with snapshots of
   `claude-container` and `sandbox-container` and these steps:
   1. `.\claude-container.ps1 --container-setup` in provider mode with the
      account method. The operator first declines the login, to see the
      Windows next step of `sandbox-ref-28`, then runs setup again and logs in.
   2. A Claude session from a project folder: one prompt that reads a file,
      and Ctrl+C.
   3. `sandbox-container\tools\windows-validate.ps1 -Checkout
      C:\Work\claude-container` on Windows PowerShell 5.1 and PowerShell 7,
      once with `-Install -StopMachine`.
   4. The API key with `$env:ANTHROPIC_API_KEY`, only if the operator has a
      key.

   Each summary is copied after its run.
8. **Parity rows.**
   - Claude's row names "Adopted `sandbox-ref-28`" with this adoption's
     results.
   - The reference row is copied from `sandbox-container`.
   - After the merge, Claude's row goes into `sandbox-container` and the four
     other wrappers, one commit on `main` each. The rows of the wrappers still
     on `sandbox-ref-25` stay as they are.

## Risks / Trade-offs

- [Three tags at once widen the validation surface.] → Every runner mode the
  tags need runs, including `--guard`.
- [Installed qualification reports no longer match.] → The operator reruns
  `--container-setup` on the Linux hosts and on Windows after the merge.
- [The account login flow may behave differently from a Windows terminal.] →
  Step 1 on Windows covers it. A problem in shared setup code pauses the
  change for the reference.
- [Docs drift from the reference.] → The adapted sections follow the
  reference's structure, so the next adoption can compare them section by
  section.
