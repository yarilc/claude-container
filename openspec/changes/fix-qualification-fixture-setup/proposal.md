# Proposal

## Why

`sandbox-ref-13` (change `add-toolchain-library`) added `setup/toolchains.py`
to `SHARED_CODE` in `network/qualification_records.py`, so qualification now
digests it as part of every installation. The shared runtime fixture
`QualificationRuntime` in `tests/test_qualification.py` builds a synthetic
installation without `setup/`. Since `sandbox-ref-13`, six of its real-engine
tests fail with `No such file or directory: …/installed/setup`:

- `test_cancelled_gate_has_no_report_and_cleans_only_its_resources`
- `test_cancelled_tls_gate_is_bounded_and_cleans_owned_resources`
- `test_concurrent_gates_publish_complete_atomic_reports`
- `test_installed_offline_qualification_missing_stale_and_unsafe_reports`
- `test_installed_provider_qualification_and_fixed_probe_cannot_run_application`
- `test_ordinary_report_check_interruption_preserves_shutdown_budget`

The failure was found while Codex adopted `sandbox-ref-13`, and it reproduces
here with `bash tests/run-runtime.sh --qualification`. The reference
validation of `sandbox-ref-13` never ran that mode, although the change
touched qualification code. `docs/propagation.md` asks for `--qualification`
"for setup or qualification code", but nothing ties that list to what
`tools/propagate.py` asks the wrappers to run.

Production code is correct: setup installs `setup/toolchains.py` and
`setup/common.py` (`setup/common.py` `MANIFEST`). Only the shared test is
broken. Because it is shared, the fix needs a new tag, and the wrappers adopt
it instead of `sandbox-ref-13`.

## What Changes

- **Shared test fix.** The `QualificationRuntime` fixture copies
  `setup/common.py` and `setup/toolchains.py` into its synthetic installation,
  like the other installation fixtures since `sandbox-ref-13`. Ordinary
  launches in the fixture also need them, because the launcher runs
  `setup/toolchains.py launch-env`.
- **Tagging rule.** Before a new tag, the reference runs every runner mode
  that `tools/propagate.py` lists for a dry run of that tag against a wrapper,
  in this repository. `docs/propagation.md` step 1 says so, and the
  `reference-propagation` spec gains the requirement.
- **Tag `sandbox-ref-14`** on the merge, with a validation record.
- No production code change. The qualification identity does not change for
  this reason, but `tests/test_qualification.py` is not a qualification input,
  so installations qualified on `sandbox-ref-13` stay valid.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `reference-propagation`: the reference runs, before tagging, the runner
  modes that the propagation tool lists for the wrappers.

## Impact

- `tests/test_qualification.py` (shared), `docs/propagation.md`,
  `docs/validation.md`.
- Tag `sandbox-ref-14`. The Codex change `adopt-sandbox-ref-13`, paused on its
  branch, is updated to adopt `sandbox-ref-14` in its place. OpenCode, Pi and
  Antigravity adopt `sandbox-ref-14` directly.
- `main` is one commit ahead of `origin/main` (the archive of
  `add-toolchain-library`); that stays as it is.
