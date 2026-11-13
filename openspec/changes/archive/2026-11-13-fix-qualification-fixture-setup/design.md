# Design

## Context

- `network/qualification_records.py` `SHARED_CODE` includes
  `setup/toolchains.py` since `sandbox-ref-13`. Qualification digests every
  file in it, and fails when one is missing.
- `tests/test_qualification.py` `QualificationRuntime.setUp` builds
  `<base>/installed` from:
  - the wrapper;
  - `Containerfile`, `.containerignore` and `PROFILE.install_files`;
  - `agent/profile.json` and the policy;
  - `network/*.py`, `network/resolv.conf` and the guard binaries.

  It copies nothing from `setup/`.
- Some of its tests also start ordinary launches through the installed
  wrapper. Since `sandbox-ref-13` such a launch runs
  `python3 -I <installation>/setup/toolchains.py launch-env`, which imports
  `setup/common.py`. `common.py` imports `network/agent_budgets.py` and
  `network/agent_profile.py`, which the fixture already copies. The fixture's
  `HOME` is a private directory in the native test root, so the default
  library can be created there.
- `tests/test_network_runtime.py` (not shared) already copies
  `setup/common.py`, `setup/toolchains.py` and `Containerfile` since
  `sandbox-ref-13`, and passes.
- `tools/propagate.py` `checklist()` maps changed paths to runner modes.
  `network/qualif*` adds `--qualification`, `setup/` adds `--setup` and
  `--setup-runtime`. The `sandbox-ref-13` reference record shows the unit
  discovery, the default runtime mode and `--network`, but not
  `--qualification`, `--setup` or `--guard`.

## Goals / Non-Goals

**Goals:**
- `bash tests/run-runtime.sh --qualification` passes again here and in every
  wrapper that adopts the fix.
- The procedure prevents a tag whose reference validation skipped a mode
  the wrappers will run.

**Non-Goals:**
- Any production change in `network/` or `setup/`.
- A new `tools/propagate.py` option that prints the reference's own
  checklist. Considered: a `--reference <old tag>` mode would make the rule
  mechanical, but the documented rule is enough for now, and it keeps the
  tool and its tests unchanged.
- The Codex runner's world-writable `/tmp` for `--wrapper`. Codex fixes its
  own runner and `tests/test_wrapper.py` in its adoption change.

## Decisions

1. **Copy the two setup modules explicitly.** `QualificationRuntime.setUp`
   creates `installed/setup` (`0700`) and copies `setup/common.py` and
   `setup/toolchains.py`, next to the existing `network/*.py` loop.
   - Alternative: copy all of `setup/`. Rejected: the fixture lists exactly
     what an installation needs, like the rest of `setUp`. The interactive
     setup files are not used.
   - Alternative: derive the list from `SHARED_CODE`. Rejected: `SHARED_CODE`
     also names the guard binaries, which the fixture builds separately.
2. **Guard the fixture with a unit check.** A small non-runtime test in
   `tests/test_qualification.py` asserts that every `setup/` entry of
   `SHARED_CODE` is in the fixture's setup copy list (a module-level tuple
   used by `setUp`). A future shared module then fails the unit suite, not
   only the opt-in runtime mode.
3. **Tagging rule in the procedure.** `docs/propagation.md` step 1 replaces
   its three-item list:
   - Before tagging, run every mode that the checklist would print for the
     changed shared files. The step shows the mapping that `checklist()`
     implements.
   - Also run `--qualification` when a changed file is in `SHARED_CODE`.
   - Record every mode in the validation record.

   The `reference-propagation` delta adds this as a requirement.
4. **Tag and adoption.** After the merge, an annotated tag `sandbox-ref-14`
   marks it. Codex's paused change moves its target to `sandbox-ref-14`
   through `/opsx:update`. The other wrappers adopt `sandbox-ref-14` from
   `sandbox-ref-12`.

5. **Private temporary storage for the runner** (added during apply, chosen
   by the user). `bash tests/run-runtime.sh --wrapper` fails on `main` since
   `sandbox-ref-13`, with 190 failures. `tests/test_wrapper.py` creates its
   fixtures in `SANDBOX_TEST_TMPDIR`, which the runner does not set, so they
   land in the image's world-writable `/tmp`. The toolchain library then
   refuses that ancestor.
   - The runner mounts a private tmpfs at `/sandbox-test-tmp` (`0700`,
     `U=true`, 1 GiB, executable) and sets `SANDBOX_TEST_TMPDIR` to it in
     every mode. The wrapper, setup, session, qualification and toolchain
     suites read it, so every mode is rerun with the new runner.
   - `tests/run-runtime.sh` is not shared, so this needs no tag of its own.
     It still ships in the `sandbox-ref-14` merge.

## Risks / Trade-offs

- [Another shared runtime fixture lacks the new files] → The tagging rule
  runs all listed modes here first. The `sandbox-ref-14` record covers
  `--shared`, `--setup`, `--setup-runtime`, `--qualification`, `--guard`,
  `--network`, `--wrapper` and the default runtime mode.
- [`checklist()` does not add `--qualification` for a setup-only change that
  touches `SHARED_CODE`] → The documented rule covers the reference. Wrappers
  still get `--setup`. The shared test change in this tag adds
  `--qualification` to their checklist anyway.
- [Qualification identity] → Unchanged, because the test file is not
  digested. Existing reports stay valid, and no requalification is needed
  for this tag alone.

## Migration Plan

1. Merge into `main` and tag `sandbox-ref-14`. The operator pushes `main` and
   the tag.
2. Update and apply the Codex change; propose the OpenCode, Pi and
   Antigravity adoptions.
3. Rollback before the push: delete the local tag and reset `main` to
   `4ed9a22`.
