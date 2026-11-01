# Tasks

## 1. Launch engine verification and regression harness

- [x] 1.1 Add a Python standard-library fake-Podman harness in `tests/test_wrapper.py` with synthetic HOME/configuration and executable stubs; verify it captures exact argv and cannot read real credentials or contact a real engine.
- [x] 1.2 Verify Linux/rootless launch-engine results and reject unsupported contexts before image operations; test local execution, explicit same-host Unix access, failed/empty/malformed queries, rootful/non-Linux output, named connections, and TCP/SSH contexts.
- [x] 1.3 Keep wrapper help independent of engine and state setup, validate YOLO/CA controls before image operations, and preserve exact socket opt-in; verify help with missing Podman and invalid configuration plus mixed-case boolean and invalid-value cases.
- [x] 1.4 Update help, README engine prerequisites, and AGENTS.md testing guidance to distinguish mandatory launch verification from optional delegation; verify documentation no longer promises zero service queries when an explicit Unix launch engine is selected.

## 2. Compatible and isolated persistent state

- [x] 2.1 Preserve shared `~/.claude`/`CLAUDE_CONFIG_DIR` and host OpenSpec mounts when `CLAUDE_CONTAINER_STATE_DIR` is unset/empty; add isolated home selection for a nonempty directory and fail on a simultaneous nonempty `CLAUDE_CONFIG_DIR`; verify exact mounts and in-container environment for both modes and absence of unused host directory creation.
- [x] 2.2 Resolve state sources, create private selected directories, validate credential ownership/access/modes, and reject isolated configuration symlinks escaping the home; test private creation, custom/shared paths, top-level aliases, insecure or inaccessible existing directories, wrong ownership, and escape attempts without recursive permission repair.
- [ ] 2.3 Add opt-in state/runtime checks and a disposable Podman test runner using native Linux temporary state at preserved host paths; verify state reuse, separate profiles, no implicit host imports, caller file ownership, and safe runner cleanup without touching real host state.
- [x] 2.4 Document shared defaults, `CLAUDE_CONTAINER_STATE_DIR`, the suggested dedicated path, conflicting controls, filesystem permission failures, manual migration, and rollback to shared mode; verify documented layouts against both mount assemblies and document that the agent can access its credentials.

## 3. Selected and remapped delegation sockets

- [x] 3.1 Add `CLAUDE_CONTAINER_PODMAN_SOCKET` precedence over explicit Unix `CONTAINER_HOST` and runtime-directory fallback; test override precedence, fixed-path fallback, custom `XDG_RUNTIME_DIR`, symlink resolution, absolute-path validation, and ignored invalid overrides when delegation is disabled.
- [x] 3.2 Verify the exact selected accessible endpoint before image operations and bind its absolute service-reported host socket path; test query failure, rootful/empty/unexpected results, missing/relative host paths, inaccessible/non-socket sources, remapped paths, and a distinct default client endpoint.
- [x] 3.3 Test every disabled socket value including unset, empty, `0`, `true`, `yes`, and `01`, plus enabled access across Claude/shell, shared/isolated state, build, and worktree modes; verify only exact `1` adds the socket and container `CONTAINER_HOST`, and failed enabled verification blocks explicit builds.
- [ ] 3.4 Add real same-host wrapper-in-container and child-bind checks; verify a child writes a caller-owned workspace file through preserved absolute paths and delegation-off sessions receive neither the socket nor `CONTAINER_HOST`.
- [x] 3.5 Update help/README socket setup, endpoint precedence, pinning/migration examples, remapped-host path requirements, and the authority to mount host paths beyond the project; verify examples match the selected endpoint and no longer describe `/run/user/<uid>` as unconditional.

## 4. Container boundaries and permission independence

- [x] 4.1 Preserve read-only root, caller identity, current tmpfs limits and `noexec`, existing workspace/worktree semantics, and opt-in CA behavior; remove automatic OpenSpec relabeling and add argv assertions excluding privilege, extra capability, custom seccomp, disabled labels, and relabel options.
- [x] 4.2 Add wrapper checks for all four YOLO/socket combinations in both state modes, native permission argument forwarding, and shell exclusion; verify YOLO never changes mounts, state, or socket selection.
- [ ] 4.3 Add runtime sentinel, `/usr` write-denial, ephemeral storage, worktree metadata/sibling access, and CA mount checks; verify both CA modes and fixed read-only bundle path/four variables without changing the host trust store.
- [x] 4.4 Document approvals, internal sandboxing, container filesystem boundaries, workspace-parent expansion, standard SELinux/seccomp policy, and lack of egress filtering; verify no claim treats Bubblewrap availability or a zero CLI status as proof of successful sandboxed tool execution.

## 5. Terminal-aware invocation and owned lifecycle

- [ ] 5.1 Allocate TTY only for terminal stdin/stdout, preserve redirected stdin and argument arrays, forward terminal `TERM` by name, and ignore Claude arguments in shell mode; verify pipeline input, spaces/empty arguments, pseudo-terminal sessions, and shell behavior with wrapper tests and credential-free CLI help/version startup.
- [x] 5.2 Resolve the physical wrapper location and distinguish image absence from inspection errors while preserving existing explicit-build behavior; test symlink invocation from an external workspace, successful/missing/error inspection outcomes, and build status propagation without unintended launch.
- [x] 5.3 Reserve names with container creation, parse suffixes as decimal, retry collisions up to the bounded limit, attach with preserved stdin, and clean up only the owned container ID; test stopped/running names, leading-zero suffixes, races, retry exhaustion, unrelated creation failures, and private diagnostic-file cleanup.
- [ ] 5.4 Forward INT/TERM/HUP and preserve application exit status including 125; test signals and cleanup through the fake engine and real concurrent shell sessions, ensuring another session remains alive and unrelated containers are untouched.
- [x] 5.5 Update README invocation/naming/termination behavior and test commands; verify documented interactive and headless usage against the completed tests.

## 6. Integrated acceptance and evidence

- [x] 6.1 Run `bash -n` on changed shell scripts, `git diff --check`, the wrapper suite, and the opt-in rootless runtime suite; verify integrated launch, identity, mounts, persistence, worktrees, and child binds, recording any unavailable checks explicitly rather than counting them as passed.
- [ ] 6.2 Build/inspect the runtime image and run credential-free startup/tool smoke checks in both state modes under the retained policies; record engine, kernel, architecture, CLI, and OpenSpec versions and confirm editor/runtime-image requirements still hold.
- [x] 6.3 Create `docs/validation.md` with reproducible commands and passed/failed/unavailable outcomes, including SELinux coverage and an actual Claude sandboxed tool/output check only if an appropriate authenticated session is available; verify no credentials or paid requests enter automated checks and do not infer Claude results from Antigravity's record.
- [x] 6.4 Reconcile README/help/AGENTS.md with delivered behavior and run `openspec validate align-container-sandboxing --strict`; verify every requirement has corresponding test evidence or an explicitly recorded environment-dependent limitation.
