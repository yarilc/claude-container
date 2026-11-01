# Tasks

## 1. Reject pathless Unix launch endpoints

- [x] 1.1 Tighten launch-context parsing in `claude-container.sh` before the first engine query; extend `tests/test_wrapper.py` for `unix://`, `unix:///`, slash-only variants, and relative Unix paths, verifying an actionable error and zero Podman calls with delegation off/on and with an override.
- [x] 1.2 Preserve valid local/absolute Unix operation and side-effect-free help; verify existing launch-context checks and a help invocation with an invalid endpoint pass, and update help/README to describe the required socket pathname.

## 2. Remove disabled delegation environment defaults

- [x] 2.1 Add container `--unsetenv CONTAINER_HOST` only when delegation is disabled; extend disabled-value and composition tests to verify its presence, enabled-mode absence, preserved enabled endpoint, and unchanged host launch endpoint.
- [x] 2.2 Add an opt-in runtime fixture image with a synthetic inherited `CONTAINER_HOST`, unique tagging, and owned cleanup; verify actual variable absence with delegation disabled and the fixed delegated value when enabled, in both state modes, while host Unix engine access still works.
- [x] 2.3 Update README delegation behavior and append targeted environment-check results to `docs/validation.md`; verify text distinguishes container variable removal from host launch configuration and records actual pass/fail/unavailable evidence.

## 3. Provision temporary mounts explicitly

- [x] 3.1 Add `--read-only-tmpfs=false` and explicit `/var/tmp` at 256 MiB with `rw,nosuid,nodev,noexec,mode=1777`; make `/tmp` mode `1777` explicit and preserve existing `/tmp` and `/run` limits and `/run` permission behavior; verify all three arguments across existing launch/state/delegation composition tests.
- [x] 3.2 Extend opt-in runtime checks for actual tmpfs mount types, flags and sizes, `/tmp` and `/var/tmp` modes/writes, copied-executable execution denial, and disappearance across sessions in both state modes; verify `/run` remains mounted correctly with delegation off/on without requiring arbitrary writes to its root.
- [x] 3.3 Update README temporary-storage limits and compatibility guidance, and record targeted runtime results in `docs/validation.md`; verify the text includes bounded ephemeral `/var/tmp`, retained `noexec`, and no automatic privilege or sandbox-policy relaxation.

## 4. Scope private state-directory creation umask

- [x] 4.1 Replace the process-wide `umask 077` with scoped private creation for every state `mkdir`; extend synthetic tests to verify private shared/isolated directories and unchanged caller umasks `0022`/`0002` at build, create, and lifecycle calls, retaining existing ownership/mode/symlink rejection checks.
- [x] 4.2 Extend runtime evidence to capture container umask and observed file/directory modes on native writable state in both state modes; verify private host state remains valid and report observations independently of host creation policy without adding a container `--umask` override.
- [x] 4.3 Update README state-permission guidance and append permission results to `docs/validation.md`; verify it distinguishes private host directory creation, caller umask inheritance, and measured container file modes without promising unverified runtime privacy.

## 5. Restrict image build context

- [x] 5.1 Add `.containerignore` with default exclusion and explicit exceptions for `Containerfile` and `.containerignore`; retain existing automatic/explicit physical-context build selection and verify fake-Podman build tests still pass from external working directories and symlink invocation.
- [x] 5.2 Add opt-in real-builder acceptance using a disposable synthetic context, the actual ignore policy, a local-base fixture Containerfile consuming the context, and sensitive/nested/unrelated sentinels; verify sentinels are unavailable, recipe inputs remain available, and uniquely owned images/fixtures are removed without reading real credentials.
- [x] 5.3 Document the build-input allowlist and future-input maintenance in README and record the context-probe result in `docs/validation.md`; verify the normal production image builds successfully with filtering and that build failures continue to block launch.

## 6. Verify integrated behavior

- [x] 6.1 Run `python3 -m unittest discover -s tests -p test_wrapper.py -v`, `bash -n` for all changed shell scripts, `git diff --check`, and `openspec validate harden-container-runtime-defaults --strict`; verify all applicable checks pass, including whitespace inspection of newly added files.
- [x] 6.2 Run the opt-in runtime suite through `bash tests/run-runtime.sh` or equivalent same-host native-state execution after the production build; verify existing startup/tool smoke, state, workspace, CA, delegation, and lifecycle coverage plus the new fixtures, recording client/server/image versions and pass/fail/unavailable results without overwriting historical records or marking unavailable acceptance complete.
