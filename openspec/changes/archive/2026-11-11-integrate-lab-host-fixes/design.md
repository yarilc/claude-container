# Design

## Context

`test/podman5-socket-url` (head `aa338f5`) forked from `main` at `56a6f03`
(`sandbox-ref-2`). `main` is at `b633a2d` (`sandbox-ref-10`). A trial merge
(`git merge-tree`) shows:

- auto-merged: `AGENTS.md`, `README.md`, `docs/network-contract.md`,
  `docs/setup.md`, `docs/validation.md`, `network/qualification_records.py`,
  `tests/test_guard.py`, `tests/test_qualification.py`;
- content conflicts: `setup/setup.py`,
  `openspec/specs/container-setup/spec.md`, `tests/test_setup.py`;
- no archive directory name collides.

The conflicts come from one change on each side. On `main`,
`build_runtime()` builds from the recipe (`build_image`) or runs the
wrapper's `--container-build`, depending on `install.runtime_build`. On the
branch, `prepare_artifacts()` calls `build_image(..., ca_bundle)` directly.
Image preparation runs with `host_env()` (the operator's environment plus the
selected endpoint), not with `setup/common.py runtime_environment()`, so the
wrapper's `--container-build` does not receive setup's trust selection today.
The branch's `claude-container.sh` turns a selected bundle
(`<PREFIX>_TRUST_HOST_CA=1` and `<PREFIX>_CA_BUNDLE`) into
`--secret id=build-ca,...` for its builds.

A test run in a disposable container, with executable private temporary
storage, gave these results:

- `main` passes all tests.
- The branch fails `test_smoke_requires_confirmed_success_and_has_no_maintenance_or_key`
  and `test_restricted_smoke_requires_qualification_and_displays_its_status`.
  `smoke_in()` now queries `podman info` for the controllers. These tests
  do not provide that query, and they still expect `' 512 <<'`, before the
  new controller argument.
- `test_ignored_signals_force_owned_removal` failed once on timing (3.43 s
  against 3.5 s) and passed on a rerun.

## Goals / Non-Goals

**Goals:**
- Keep the branch behavior exactly as it is, including the guard's
  `/run/secrets` acceptance.
- Keep every `main` behavior added since `sandbox-ref-2`:
  - interactive login;
  - the propagation tool;
  - the runtime-build dispatch;
  - smoke diagnostics;
  - profile-declared shared-directory privacy.
- Leave a `main` that passes its suites and can be tagged `sandbox-ref-11`.

**Non-Goals:**
- Hardening the guard's `/run/secrets` check: it is deferred until the
  operator has tested on the hosts.
- Porting the fixes to sibling wrappers, including Pi's
  `--container-build` ordering. In Pi the build runs before `ca_bundle`
  is resolved, which matters only because Pi uses `runtime_build: wrapper`.
- Fixing the timing-sensitive signal test.

## Decisions

1. **Merge, do not rebase.** Run `git merge --no-ff` of the branch into an
   integration branch `integrate-lab-host-fixes` created from `main`. This
   keeps the ten branch commits and their archived changes as the operator
   wrote and tested them. Alternative: rebase onto `main`. It would rewrite
   commits that were validated on the lab hosts, and the conflicts would
   recur across several commits.

2. **`build_runtime(release, tag, env, ca_bundle='')`.**
   - In the recipe path, the bundle goes to `build_image`, as on the branch.
   - In the wrapper path, setup sets `<PREFIX>_TRUST_HOST_CA` (`1` with a
     bundle, otherwise `0`) and `<PREFIX>_CA_BUNDLE` explicitly in the
     `--container-build` environment. The wrapper builds the secret itself.
     The setup selection overrides any value inherited from the operator's
     shell.
   - `prepare_artifacts` passes `value['ca_bundle'] if value['trust_ca'] else ''`.

   Alternatives:
   - Rely on the inherited environment. Rejected: it does not carry setup's
     selection.
   - Have setup add `--secret` for the wrapper. Rejected: the wrapper owns
     its build arguments.

   This decision was corrected during apply, after `host_env()` was found
   to be the preparation environment.

3. **Spec conflict: keep both sides.** The `main` requirements (smoke
   diagnostics, profile-declared shared-directory privacy, actionable
   private-directory refusal) and the branch requirement (host CA trust
   covers setup package fetches) are independent. They are kept in the
   order `main` first, then the branch.

4. **Test conflict: keep both sides.**
   - `test_runtime_build_follows_the_profile` (from `main`) is updated for
     the new parameter. It asserts that the bundle reaches `build_image`
     in recipe mode. It also asserts that wrapper mode passes no `--secret`
     from setup, but sets `<PREFIX>_TRUST_HOST_CA` and `<PREFIX>_CA_BUNDLE`
     in the wrapper environment, with and without trust.
   - `test_runtime_build_receives_host_ca_only_when_trusted` (from the
     branch) patches `build_runtime`'s recipe path. It keeps its
     assertions on the toolchain and proxy builds.

5. **Smoke tests: change the tests, not the code.** The two failing tests
   patch the controller query, `engine_enforced`, or set the fake engine's
   `SETUP_TEST_CONTROLLERS`. They assert that the smoke input ends with the
   enforced-controller argument, for example
   `' 4294967296 2000000000 512 cpu,memory,pids <<'`. This keeps the
   branch's runtime behavior unchanged.

6. **Tag after validation.** The annotated tag `sandbox-ref-11` goes on the
   merge commit in `main`, after the suites are recorded in
   `docs/validation.md`. The same merge moves this repository's parity table
   to `sandbox-ref-11`, as `docs/propagation.md` requires. Operator host
   checks (Rocky 9, the newer WSL host) are recorded as operator-reported or
   pending. They do not block the tag, so that the operator can test the
   tagged state.

## Risks / Trade-offs

- [Auto-merged files hide semantic conflicts] → Grep the callers of every
  changed signature:
  - `agent_hardening`;
  - `build_image`;
  - `proxy_hardening verify`;
  - smoke arguments;
  - the fixed qualification input.

  Then run the full unit discovery and the `--setup`, `--qualification`,
  `--network` and `--guard` runner modes.
- [Guard accepts any read-only tmpfs at `/run/secrets`; a read-only mount
  still allows `connect()` to an existing socket] → Accepted, and stated
  in the validation record as a known follow-up. The mount is created by
  the wrapper, and the operator tests first.
- [Weaker budgets on hosts without controller delegation] → This is the
  branch's documented policy. The notices and the qualification identity
  keep it visible.
- [Every installation becomes stale] → The validation record and the tag
  message tell operators to rebuild and rerun setup.

## Migration Plan

1. Merge on `integrate-lab-host-fixes`, validate, then merge into `main`
   with `--no-ff`.
2. Create `sandbox-ref-11` on that merge commit. The operator pushes
   `main` and the tag.
3. On each host, rebuild with refresh approved and rerun setup.
4. Roll back by resetting `main` to `b633a2d` before the push. After the
   push, revert the merge commit and keep `sandbox-ref-10` for the
   siblings.
