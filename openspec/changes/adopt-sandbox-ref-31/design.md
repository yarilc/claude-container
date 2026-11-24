# Design

## Context

Claude adopted `sandbox-ref-28` on 2026-11-22. `sandbox-ref-31` holds:
- `simplify-toolchain-provisioning`: catalog names, several sources, archive
  downloads, no maintenance consent for `add`;
- `replace-podman-delegation-with-session-engine`: the session container
  engine, image toolchains and the removal of host Podman delegation, tagged
  `sandbox-ref-29`;
- two fixes found while adopting it:
  - `sandbox-ref-30`: the engine's chroot capability, without which the engine
    could not build images or extract new layers;
  - `sandbox-ref-31`: the engine base pinned to an `-immutable` tag, because
    quay.io had deleted the pinned manifest and a new installation could not
    build the engine.

  Claude skips `sandbox-ref-29` and `sandbox-ref-30`.

**Dry run, 2026-11-24.** `tools/propagate.py` from `sandbox-ref-28` to
`sandbox-ref-31` gave this plan:
- **Update:**
  - `launcher/core.sh`, `launcher/windows/bootstrap.sh`, `launcher/windows/core.ps1`;
  - `network/agent_profile.py`, `qualification_records.py` and `qualify.py`;
  - `setup/common.py`, `launch.py`, `setup.py` and `toolchains.py`;
  - `tests/fake_podman.py`, `test_alignment.py`, `test_launcher.py`,
    `test_qualification.py`, `test_setup.py`, `test_toolchains.py`,
    `test_windows_bootstrap.py` and `tests/windows/shim_tests.ps1`.
- **Add:** the six `launcher/engine/` files, `setup/engine.py`, the six
  `setup/toolchain-catalog/` recipes and `tests/test_engine.py`.
- **Rewrite:** 11 references in `docs/network-contract.md`.
- **Runner modes listed:**
  - the reference-copy and alignment tests;
  - `--setup`, `--setup-runtime`, `--qualification` and `--wrapper`.

**Claude's own files that name delegation:**
- `tests/test_wrapper.py`: the YOLO × delegation × state grid;
- `tests/test_runtime.py`: delegation grids, the delegated child container
  and the native help grid;
- `tests/test_network_runtime.py`: the restricted refusal;
- `tests/test_setup_wrapper.py` and `tests/test_setup_runtime.py`: the setup
  question;
- `README.md` and `AGENTS.md`: the delegation sections and the security
  statements;
- Claude's specs: `container-isolation`, `shared-launcher` and
  `container-podman-access`.

**Runner.** The development session is a Claude session on the Windows Podman
machine. The spike engine of the reference change runs beside it. Unit tests
run there on a native copy of the checkout. That engine has no Claude image:
`claude-code`, its guard toolchain and its egress image exist only in the
machine's engine.

## Goals / Non-Goals

**Goals:**
- Claude runs on the `sandbox-ref-31` shared files.
- Claude's tests, documentation and specs no longer describe delegation.
- Claude's runner modes pass from a Claude session with its own engine. That
  session is also the first real use of the feature by an agent wrapper.

**Non-Goals:**
- No change to Claude's runtime image, egress image or policies.
- No new shared behavior. A defect in shared code is fixed in
  `sandbox-container` under a new tag.
- No native Linux check: it stays with the reference change (its task 8.2).

## Decisions

1. **Spec deltas follow the reference deltas.**
   - Requirements whose Claude text equals the reference's take the reference
     delta, with Claude's variable names.
   - Requirements with Claude wording, such as the provider default or the
     agent session, take the same edits applied to Claude's text.
   - Where a scenario goes away, the requirement is removed and restated under
     a new name. Two cases, as in the reference:
     - "Independent approvals and delegation" becomes "Independent approvals";
     - "Every agent container drops capabilities…" becomes "Agent containers
       drop all capabilities and privilege gains".
   - `container-podman-access` is retired (`retire_capabilities: true`).
   - Alternative: a minimal adoption without spec deltas. Rejected: Claude's
     specs would keep describing delegation that the code refuses.

2. **Claude's tests mirror the reference's rewrite.**
   - The YOLO grid keeps its four combinations, YOLO × state mode, and checks
     that no socket is mounted.
   - The runtime and network suites take the reference's refusal and engine
     cases. The network cases read the engine image name from the profile
     (`<P>_ENGINE_IMAGE`, `localhost/claude-code-engine`), not a reference
     literal.
   - `tests/run-runtime.sh` is the reference's, with Claude's image names.
     Inside a session, it uses the engine's Unix socket, and it copies a
     checkout that group or other can write into a native volume.

3. **The release catalog replaces `docs/toolchains/`**, as in the reference.
   The README's toolchain section follows the reference's, with Claude's
   names.

4. **Validation runs from a Claude session with its engine, before the
   merge.**
   - The adoption is committed on `adopt-sandbox-ref-31` and not merged.
   - The operator reruns setup from Windows with that branch checked out.
     Setup builds `localhost/claude-code-engine` and migrates saved
     delegation.
   - The operator adds as image toolchains the images the modes need:
     - the pinned registry images of the tests;
     - Claude's local runtime, guard toolchain and egress images, by image ID;
     - the engine image itself, for the nested engine cases.
   - The runner modes then run from a new session, through
     `tests/run-runtime.sh` against the session's engine.
   - Alternative: load Claude's images into the spike engine and validate
     there. Rejected: it needs host commands from the operator for every
     image, and it does not exercise Claude's own engine.

## Risks / Trade-offs

- **[Risk] Nested engines run out of subordinate IDs.** The runner's test
  containers start sessions with their own engines, one level deeper than
  the spike measured. → Each nested level needs a full 65536-ID range. The
  spike measured three levels with 300001 IDs. If a level fails `newuidmap`,
  the mode is recorded as unavailable on this runner, with the measured range.
- **[Risk] `cgroupfs` on the Podman machine.** The budget subtests fail there,
  and explicit limits for nested containers are not applied. → Record them as
  for the reference. They are runner failures, not adoption failures.
- **[Risk] A shared defect appears only in Claude's session.** → The change
  pauses: fix in `sandbox-container`, tag `sandbox-ref-31`, and adopt that tag
  on a fresh branch.

## Migration Plan

1. The operator reruns `claude-container --container-setup` from Windows on the
   branch. Setup removes saved delegation and builds the engine image.
2. The operator adds image toolchains. Sessions started after that have an
   engine.
3. Rollback: point `current` back to the previous release, as
   `docs/setup.md` describes. That release keeps its schema 2 preferences;
   setup from `main` would refuse the schema 3 file of the new release. The
   previous release ignores the image store, and the library stays readable
   (reference validation, task 3.7).
