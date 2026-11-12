# Proposal

## Why

Adopting `sandbox-ref-11` in the wrappers exposed two defects in the shared
components:

- **Qualification containers depend on the runtime image's `WORKDIR`.** The
  shared qualification code starts runtime-image containers without
  `--workdir`: the gate's openssl, control and peer containers
  (`network/qualify.py`) and the security-identity probe
  (`network/qualification_records.py`). When the image declares a `WORKDIR`
  that is in no layer, Podman creates it and chowns it at every start. On
  the Rocky Linux 9 lab host that chown fails for the operator's domain UID
  (31600276) under `--userns=keep-id`, so Codex setup stopped in
  qualification. Codex now creates `/workspace` in its image. The shared
  code should still not depend on how each wrapper writes its recipe.
- **A shared setup test assumes a recipe-built runtime.**
  `tests/test_setup.py::test_runtime_build_receives_host_ca_only_when_trusted`
  patches `build_image` and expects the runtime build to call it. That holds
  only when the profile declares `install.runtime_build: recipe`. Pi
  declares `wrapper`, so the copied test fails there and blocks Pi's
  adoption.

## What Changes

- Every runtime-image container started by the shared qualification code
  passes `--workdir /`, so the engine never creates or chowns an image
  working directory for it:
  - the gate containers built from `Gate.common()`;
  - the security-identity probe.

  The probes use only absolute paths, so their behavior is unchanged.
- `test_runtime_build_receives_host_ca_only_when_trusted` pins
  `PROFILE.runtime_build` to `recipe` for its recipe assertions.
  Wrapper-mode coverage stays in `test_runtime_build_follows_the_profile`.
  The test now passes under either profile setting.
- Unit tests assert `--workdir /` for the gate containers and the probe.
- The change is published as annotated tag `sandbox-ref-12`. The wrappers
  adopt it in their own changes. Pi adopts `sandbox-ref-10` → `sandbox-ref-12`
  directly.
- The code digests in the qualification identity change, so restricted
  installations rerun qualification after adopting the tag.
- **Unchanged:**
  - mounts, user, network and labels of the gate containers;
  - the proxy and toolchain containers, which use images without a
    `WORKDIR` or already pass `--workdir`;
  - every agent launch.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `network-egress`: qualification containers do not depend on the runtime
  image's working directory.

## Impact

- Shared code: `network/qualify.py`, `network/qualification_records.py`,
  `tests/test_qualification.py`, `tests/test_setup.py`.
- Docs: `docs/validation.md` (a `sandbox-ref-12` section) and the parity
  table in `docs/network-contract.md`, which moves to `sandbox-ref-12`.
- claude-container `main` is one commit ahead of `origin/main` (the archive
  of `integrate-lab-host-fixes`). That is unrelated and stays as it is.
- Codex and OpenCode, already on `sandbox-ref-11`, adopt `sandbox-ref-12` in
  follow-up changes. Pi's pending change is updated to target
  `sandbox-ref-12`.
