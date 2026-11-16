# Tasks

## 1. Reference manifest at `sandbox-ref-18`

- [x] 1.1 Create branch `prepare-adopt-sandbox-ref-20` from `main` in `claude-container` (the tool creates `adopt-sandbox-ref-20` itself); verify `git status` is clean apart from this change directory.
- [x] 1.2 Copy `codex-container/tests/test_reference_copy.py` byte for byte into `tests/` (design decision 1) and commit it with this change directory; verify `python3 -m unittest discover -s tests -p test_reference_copy.py` passes, proving that Claude's shared files equal `sandbox-ref-18`.

## 2. Adopt `sandbox-ref-20`

- [ ] 2.1 From `sandbox-container`, run `python3 -I tools/propagate.py ../claude-container sandbox-ref-18 sandbox-ref-20` (dry run), then `--apply`; verify the plan lists the shared and fixture files and `manifest: names sandbox-container`, and that the tool switched to its `adopt-sandbox-ref-20` branch.
- [ ] 2.2 Fix the parity table by hand (design decision 3): restore the Codex, Antigravity, OpenCode and Pi rows to `sandbox-ref-18`, add the `Sandbox (reference)` row as in `sandbox-container`, and set the Claude row to `Ported from sandbox-ref-20`; verify the four sibling rows equal those in the sibling repositories and the reference row equals `sandbox-container`'s.

## 3. Per-agent adjustments

- [ ] 3.1 Create `tests/test_setup_wrapper.py` from the eight wrapper-launching tests of `sandbox-ref-18`'s `tests/test_setup.py` (design decision 2: real profile and wrapper, subprocess harness for the real setup modules, Claude semantics); verify `discover -s tests -p test_setup_wrapper.py` passes in the disposable test container.
- [ ] 3.2 Make `tests/test_wrapper.py` load the checkout profile by path in `AccountInventoryTests`, and port the lifetime-notice fix (design decision 4) to `claude-container.sh` with the boundary test; verify the boundary test fails with the old launcher and `bash tests/run-runtime.sh --wrapper` passes.
- [ ] 3.3 Remove `tools/propagate.py`, `tests/test_propagate.py` and `docs/propagation.md`; update README ("Shared sandbox components"), `AGENTS.md` and `docs/network-contract.md` (the five wrappers and the reference, where propagation runs) so that `sandbox-container` is the reference; verify `grep -rn "propagate.py\|propagation.md" --exclude-dir=openspec .` shows only references to `sandbox-container`.

## 4. Integration

- [ ] 4.1 Run the unit discovery in the disposable test container and every runner mode (`--setup`, `--setup-runtime`, `--qualification`, `--guard`, `--network`, `--network-policy`, `--network-feasibility`, `--wrapper`, default) with the Claude setup image, plus `git diff --check`; verify all pass.
- [ ] 4.2 Add an `sandbox-ref-20` adoption section to `docs/validation.md` from the tool's template with every result, commit with the tool's message, and merge into `main`; verify `tests/test_reference_copy.py` passes on `main` next to the `sandbox-container` checkout (sibling check not skipped).

## Workflow follow-up

- The operator pushes `main` and reruns `--container-setup` on this host, the Rocky Linux 9 lab host and the newer WSL host (with host CA trust), then checks a Claude session.
- Archive with spec sync: `reference-propagation` is retired and its main spec deleted.
- Then Codex, OpenCode, Pi and Antigravity adopt `sandbox-ref-20` in their own changes. Each must also:
  - create its `tests/test_setup_wrapper.py`;
  - fix the parity table;
  - update its `network-egress` requirement that names `claude-container` as the reference copy.
