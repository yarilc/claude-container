# Tasks

## 1. Ordinary launch admission and first-run guidance

- [x] 1.1 Add the missing-mode guard to `claude-container.sh` after dedicated dispatch and ordinary parsing but before runtime validation; verify unset and empty modes return status 1, English setup guidance on stderr, empty stdout, no fake-Podman calls and no state creation using `tests/test_wrapper.py`.
- [x] 1.2 Extend wrapper admission tests across Claude/shell/build/worktree combinations, maintenance-only requests, missing Podman/Python/timeout, unrelated invalid controls and misleading workspace configuration files; verify each missing-mode case stops before prerequisites or mutations, while explicit invalid and whitespace modes retain the invalid-mode diagnostic.
- [x] 1.3 Make the diagnostic command usable from another workspace and through a symlink with spaces in its path; verify the displayed safely quoted command identifies the invoked wrapper and includes `--container-setup`, without executing user-controlled pathname contents.
- [x] 1.4 Update wrapper help and README onboarding/migration examples; verify they identify mandatory first-user setup, managed launch, explicit manual modes, offline API limitations, separate maintenance consent and the behavior before/after `c777b73`, and that side-effect-free help still succeeds without runtime prerequisites.

## 2. Managed launch and dedicated entry-point compatibility

- [x] 2.1 Add actual-wrapper managed-launch integration coverage in `tests/test_setup.py` with synthetic protected preferences and fake Podman: saved offline/provider/unrestricted modes supply configuration, explicit nonempty overrides retain precedence, and an explicit empty override receives missing-setup guidance before engine/state operations; verify adapter stand-in tests still preserve arguments, stdin, cwd, status and empty overrides.
- [x] 2.2 Verify existing setup/qualification dispatch and add focused regression cases where needed: missing/empty ordinary mode must not block help precedence, setup terminal/argument checks or standalone qualification diagnosis; internal probes retain fixed protected-input checks and qualification supplies explicit modes. Verify no supplied application command can use these entry points to bypass admission or confinement.
- [x] 2.3 Update `docs/setup.md`, `docs/network-contract.md` and `AGENTS.md` to match managed/manual admission and qualification behavior; verify no ordinary unset/empty offline-default claim remains in current guidance, while historical evidence and the standalone qualification default remain accurately labeled.

## 3. Integration validation and N20 evidence

- [x] 3.1 Run `python3 -m unittest discover -s tests -p test_wrapper.py -v` and `python3 -m unittest discover -s tests -p test_setup.py -v`, using executable native temporary storage as required; run `bash -n` on changed shell scripts, `git diff --check` and `openspec validate clarify-missing-setup-startup --strict`, and resolve failures attributable to this change.
- [x] 3.2 With prepared images and protected native storage, run the existing credential-free `bash tests/run-runtime.sh --qualification` and `bash tests/run-runtime.sh --setup-runtime` acceptance paths, confirming candidate qualification and activation remain reachable after the wrapper identity changes; record actual passed, failed or unavailable outcomes and versions without enabling real user services, importing credentials or making authenticated/model calls.
- [x] 3.3 Record N20 behavior, synthetic results, available installed-path evidence and any unavailable checks in `docs/validation.md`; verify stale reports still require requalification and the documented last-working-release rollback remains applicable, then update only N20 in `todo.md` to reflect the achieved acceptance status. Keep unrelated TODO findings and baseline main-spec strict warnings separate.
