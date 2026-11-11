# Tasks

## 1. Merge and conflict resolution

- [x] 1.1 Create branch `integrate-lab-host-fixes` from `main` (`b633a2d`). Run
  `git merge --no-ff origin/test/podman5-socket-url` and check that the
  conflicts are exactly `setup/setup.py`,
  `openspec/specs/container-setup/spec.md` and `tests/test_setup.py`.
  Fetch first if possible, and verify that the merged head is `aa338f5` or
  a newer operator push.
- [x] 1.2 Resolve `openspec/specs/container-setup/spec.md`: keep the `main`
  requirements, then the branch's "Host CA trust covers setup package
  fetches". Verify with `openspec validate --specs` and confirm that no
  conflict markers remain.
- [x] 1.3 Resolve `setup/setup.py` by adding `ca_bundle` to
  `build_runtime()` (design decision 2):
  - the recipe path passes it to `build_image`;
  - the wrapper path keeps relying on the runtime environment;
  - `prepare_artifacts` passes the trusted bundle.

  Verify that `python3 -I -c 'import ast,sys; ast.parse(open("setup/setup.py").read())'`
  succeeds and that no conflict markers remain.
- [x] 1.4 Resolve `tests/test_setup.py` by keeping both tests, adapted as in
  design decision 4. Verify that the wrapper-path test asserts no setup-side
  `--secret`, and that `<PREFIX>_TRUST_HOST_CA` and `<PREFIX>_CA_BUNDLE`
  are present. Verify that the recipe-path test asserts the bundle. Then
  run `python3 -m unittest tests.test_setup -k runtime_build`.
- [x] 1.5 Fix the two smoke tests, `test_smoke_requires_confirmed_success_and_has_no_maintenance_or_key`
  and `test_restricted_smoke_requires_qualification_and_displays_its_status`.
  Patch the controller query and assert the enforced-controller argument
  (design decision 5), without changing `setup/`. The same applies to
  `test_failed_smoke_shows_a_bounded_sanitized_stderr_excerpt` from `main`,
  which meets the new controller query only after the merge. Verify that
  all three pass.
- [x] 1.6 Grep the merged tree for the callers of changed signatures:
  - `agent_hardening(`;
  - `build_image(`;
  - `build_runtime(`;
  - `proxy_hardening.py verify`;
  - the smoke arguments;
  - `fixed_qualification_input`.

  Verify that each one uses the branch signature, and confirm that
  `git diff --check` is clean.

## 2. Validation and documentation

- [x] 2.1 Run the full unit discovery,
  `python3 -m unittest discover -s tests`, with `SANDBOX_TEST_TMPDIR` on
  executable, private, native storage with a short path. Verify that there
  are no failures beyond the known timing-sensitive
  `test_ignored_signals_force_owned_removal`, which passes when rerun.
- [x] 2.2 Run `bash -n` on `claude-container.sh` and on the changed shell
  scripts, and run `tests/test_image_pins.py`. Verify that both pass.
- [x] 2.3 Run `bash tests/run-runtime.sh` with `--setup`, `--qualification`,
  `--network` and `--guard` where this host allows. Then run a
  `--container-setup` in provider mode with refresh approved. Verify the
  rebuild of the runtime and toolchain images, the new guard, qualification
  and smoke readiness. Record any mode this host cannot run as unavailable.
- [x] 2.4 Add a `docs/validation.md` section named `sandbox-ref-11` (integration
  of the lab-host fixes). It records:
  - the merged commits;
  - the conflict resolution;
  - the suite and runtime results from 2.1–2.3;
  - the new runtime image ID;
  - the requalification requirement;
  - the Rocky 9 and newer WSL host results as operator-reported or
    pending;
  - the deferred `/run/secrets` guard hardening as a known follow-up.

  Verify that every check is listed as passed, failed or unavailable.
- [x] 2.5 Update the five-wrapper parity table in `docs/network-contract.md`:
  set the `Reference (...)` cell and the `Ported from ...` cells to
  `sandbox-ref-11`, as `docs/propagation.md` requires. Verify that
  `python3 -m unittest tests.test_alignment` passes.

## 3. Publication

- [ ] 3.1 Commit the resolution on `integrate-lab-host-fixes`, merge it into
  `main` with `--no-ff`, and verify that `git log --oneline main` shows the
  branch commits under the merge.
- [ ] 3.2 Create the annotated tag `sandbox-ref-11` on the `main` merge commit:
  `git tag -a sandbox-ref-11 -m "Reference sandbox: lab-host fixes (Podman 5, delegated controllers, IPv6-less kernels, /run/secrets, HTTPS packages)"`.
  Verify with `git cat-file -t sandbox-ref-11`, which prints `tag`, and run
  the `tools/propagate.py` dry run against `../codex-container sandbox-ref-10 sandbox-ref-11`
  without `--apply`. Verify that it lists the expected shared files.

## Workflow follow-up

- The operator pushes `main` and `sandbox-ref-11`, then runs the host tests on
  Rocky 9 and the newer WSL host.
- Propagate `sandbox-ref-11` to Codex, OpenCode, Pi and Antigravity, one change
  per wrapper. Port the launcher adaptations:
  - stripping `unix://` from the socket path;
  - conditional budgets and their verification;
  - the `/run/secrets` mask;
  - the `/dev`, devpts and `/dev/shm` mounts;
  - the `build-ca` secret.

  Also port the HTTPS apt `Containerfile` recipe. In Pi, resolve the CA
  bundle before the `--container-build` build.
- After the host tests, evaluate hardening the guard's `/run/secrets`
  acceptance: require mountinfo root `/` and an empty directory.
- Sync the `container-setup` delta and archive this change after review.
