# Design

## Context

Runtime-image containers started by the shared qualification code:

- `network/qualify.py`, `Gate.common(image, network)` (line 119), shared by
  three containers:
  - the openssl certificate container (line 212), which writes
    `/qualification/*.pem`;
  - the unconfined control probe (line 223), which runs `/probe.py control`
    and uses only `/workspace/...` (a bind mount) and other absolute paths;
  - the positive-control peer (line 304), which runs `/peer.py`.
- `network/qualification_records.py`, `fingerprint()` (line 182): the
  security-identity probe, `python3 -I -c` with absolute `/qualification-*`
  and `/proc` paths. It does not use `Gate.common()`.

None of them passes `--workdir`, so the image's `WORKDIR` applies. The guarded
probe runs through the wrapper's own launch, which passes
`--workdir <workspace>`. The proxy (`network/Containerfile`, no `WORKDIR`)
and the guard compiler (`build-guard.sh`, `--workdir "$project_root"`) are
not affected.

Observed on 2026-11-12: the Codex image, before its `/workspace` fix, showed
`/workspace` with the container start time. Podman had created it at start.
On Rocky that path fails with "chowning container workdir to container
root" for UID 31600276.

`tests/test_setup.py::test_runtime_build_receives_host_ca_only_when_trusted`
calls `prepare_artifacts()` with `build_image` patched and reads
`build.call_args.args[4]`. With `PROFILE.runtime_build == 'wrapper'`,
`build_runtime()` runs the wrapper instead. `build_image` is then not called
for the runtime, and the test fails with `NoneType.args`.
`test_runtime_build_follows_the_profile` already patches
`PROFILE.runtime_build` for both modes.

## Goals / Non-Goals

**Goals:**
- Qualification never depends on a wrapper image's `WORKDIR`.
- Every shared test passes unchanged in every wrapper, whatever its
  `runtime_build`.

**Non-Goals:**
- Wrapper recipes: Codex and OpenCode already create `/workspace`, Pi has no
  `WORKDIR`, and Antigravity gets the recipe fix in its own adoption.
- Changing which containers qualification starts, or their mounts.

## Decisions

1. **`--workdir /` in `Gate.common()`.** Add it once, next to `--read-only`,
   so all three gate containers inherit it. Alternatives considered:
   - `--workdir /workspace` only for the control container. Rejected,
     because the certificate and peer containers would still depend on the
     image.
   - Requiring every wrapper image to create its `WORKDIR`. Kept only as a
     wrapper-level recommendation; the shared code must not rely on it.
2. **`--workdir /` in the security probe** of `fingerprint()`, in the same
   position. It does not use `Gate.common()`, and keeping its argument list
   independent avoids pulling the secrets mask into a probe that runs no
   guard.
3. **The test pins its assumption.** Wrap the `prepare_artifacts()` and
   `build_image()` calls of
   `test_runtime_build_receives_host_ca_only_when_trusted` in
   `patch.object(setup.PROFILE, 'runtime_build', 'recipe')`. The toolchain
   and proxy assertions do not depend on the profile, but stay under the
   same patch for clarity. Alternative considered: skip the test for
   wrapper profiles. Rejected, because the recipe path would then go
   untested in Pi.
4. **Tests for the workdir.**
   - `test_gate_containers_mask_engine_default_secrets` becomes a
     common-arguments test that also asserts `--workdir /`.
   - A new unit test runs `fingerprint()`'s probe argument construction
     through a recording `run` and asserts `--workdir /` before the image.
     If `fingerprint()` cannot reach that call without heavy fixtures,
     extract a module-level `security_probe_args()` helper and test that.
5. **Tag and propagation.** Record the validation, update this repository's
   parity table, then create `sandbox-ref-12` on the merge commit, as
   `docs/propagation.md` requires. A wrapper adopts it with
   `propagate.py <old> sandbox-ref-12`. Pi's adoption jumps from
   `sandbox-ref-10`.

## Risks / Trade-offs

- [A probe could rely on the image working directory in a way not found
  here] → The runtime `--qualification` suite runs every gate container
  for real, offline and provider.
- [The failure cannot be reproduced on this host, which has no domain UID]
  → Show directly that with `--workdir /` the engine does not create a
  missing image `WORKDIR`. Use a runtime image whose `WORKDIR` is in no
  layer, such as the pre-fix Codex image `8ae054805108` if still present,
  or a disposable two-line image otherwise. The operator's Rocky run is the
  final check.
- [Qualification reports become stale] → The code digests change, as for
  every shared tag. Setup requalifies.

## Migration Plan

1. Merge on `fix-shared-gate-workdir-and-runtime-build-test`, then merge into
   `main` with `--no-ff` and create `sandbox-ref-12`. The operator pushes
   `main` and the tag.
2. Adopt `sandbox-ref-12` in Pi (updated change), then in Codex, OpenCode and
   Antigravity.
3. Rollback before the push: reset `main` and delete the tag. After the push,
   revert, and the wrappers stay on `sandbox-ref-11`.
