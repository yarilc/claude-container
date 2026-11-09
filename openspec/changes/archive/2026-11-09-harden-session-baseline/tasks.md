# Tasks

## 1. B01: privilege dropping in every mode

- [x] 1.1 Record a pre-change baseline on the host for unrestricted Claude `--version`, shell, Git, OpenSpec, delegated `podman info`/child container and `bwrap` probe, so later failures can be attributed; verify the results are captured in the working notes for `docs/validation.md`
- [x] 1.2 Add `--cap-drop=all` and `--security-opt=no-new-privileges` to the common `container_args` in `claude-container.sh` for every mode (D2), leaving `network/session.py` flags unchanged; verify with a new `tests/test_wrapper.py` case that the recorded `podman create` arguments contain both flags for unrestricted, shell, delegation, offline and provider launches
- [x] 1.3 Extend `setup/smoke.py` to require zero capability sets and `NoNewPrivs: 1` in every mode; verify `tests/test_setup.py` passes and that the smoke script fails on a synthetic non-zero `CapEff`
- [x] 1.4 Replace the help sentence "Unrestricted sessions retain their existing container arguments" and update the README/`docs/network-contract.md` hardening text to state that every agent container drops capabilities; verify the wrapper help test and a grep for the old sentence find nothing

## 2. B02: resource budgets

- [x] 2.1 Add Bash validation and normalization for `CLAUDE_CONTAINER_MEMORY_LIMIT`, `CLAUDE_CONTAINER_CPU_LIMIT`, `CLAUDE_CONTAINER_PIDS_LIMIT` per D3, placed before engine queries, and append `--memory`, `--cpus`, `--pids-limit` to `container_args`; verify wrapper tests for defaults, overrides and each rejected form (status 1, variable named, no engine call)
- [x] 2.2 Add protected, identifier-free `network/agent_budgets.py` with the same normalization (variable names from the profile environment prefix), register it in the qualification code-file list and setup release copy; verify a table-driven test feeds identical accept/reject cases to both the Bash wrapper and the Python module, and `tests/test_alignment.py` passes
- [x] 2.3 Add the post-create `podman inspect` check of `Memory`/`NanoCpus`/`PidsLimit` before `podman start` (D4), with bounded timeout and owned-container removal on mismatch; verify wrapper tests with a fake engine that reports a missing and a different limit
- [x] 2.4 Extend `setup/smoke.py` to check effective cgroup v2 `memory.max`, `pids.max` and `cpu.max` against expected normalized budgets passed as arguments (the saved values are wired in group 5); verify `tests/test_setup.py` and a host `--setup-runtime` run on the WSL target, and stop and report if the `cpu` controller is unavailable
- [x] 2.5 Add host runtime checks in `tests/test_runtime.py` for default and overridden budgets in unrestricted mode, and in `tests/test_network_runtime.py` for offline/provider, reading the effective cgroup values in the agent container; verify the host suites pass
- [x] 2.6 Document the variables, defaults, formats, the "no disable" rule and the statement that budgets and tmpfs sizes do not bound workspace/state storage in help, README and `docs/setup.md`; verify the help test lists all three with defaults

## 3. B03: sensitive workspace roots

- [x] 3.1 Move workspace and worktree-parent resolution before engine checks and add the refused-path guard from the `workspace-mounts` spec (including physical `$HOME`, `/tmp` and `/mnt/<letter>`), with exact `CLAUDE_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1` override and warning; verify wrapper tests for home, worktree parent, symlink to `/etc`, `/mnt/d`, accepted `/mnt/d/project`, exact and non-exact override, and that refusal happens before any engine call
- [x] 3.2 Confirm setup smoke, setup login, qualification probes and all runtime test fixtures use non-refused workspaces; verify by running `tests/test_setup.py`, `tests/test_qualification.py` and the host runtime suites without the override
- [x] 3.3 Document the refused set and the override in help, README and `docs/setup.md`; verify the help test lists `CLAUDE_CONTAINER_ALLOW_UNSAFE_WORKSPACE`

## 4. B04: session lifetime

- [x] 4.1 Verify `podman create --timeout` on the measured Podman versions and record whether a timeout-stopped container exits 137 or 143; verify the observation is noted for `docs/validation.md`
- [x] 4.2 Add `CLAUDE_CONTAINER_RUN_TIMEOUT` validation before engine queries, `--timeout N` for N ≥ 1, and the elapsed-time notice after the client exits without altering the status (D6); verify wrapper tests for unset, `0`, valid, negative, fractional and non-numeric values
- [x] 4.3 Add a host runtime test with a short limit in unrestricted and provider modes that checks the notice, the propagated status and owned proxy cleanup, plus a test that an early exit prints no notice; verify the host suites pass
- [x] 4.4 Document the variable in help, README and `docs/setup.md`; verify the help test lists it with "disabled by default"

## 5. Setup-managed budgets and lifetime

- [x] 5.1 Bump managed preferences to schema 2 in `setup/common.py` with `memory_limit`, `cpu_limit`, `pids_limit`, `run_timeout` (canonical strings validated by `agent_budgets.py`), exact v1-field upgrade with defaults in `load()` and v2-only `save()`; verify `tests/test_setup.py` cases for v1 upgrade, v2 round-trip, invalid values, unknown field and unknown schema
- [x] 5.2 Add the four questions to the setup questionnaire (D9) with first-run defaults, saved values on rerun and re-ask on invalid input, and print them in the setup plan; update the `answers()` helpers in `tests/test_setup.py` and `tests/test_setup_runtime.py`; verify tests for defaults, invalid-then-valid answers and rerun proposals
- [x] 5.3 Supply the saved values from `runtime_environment()` under the profile-derived variable names, keeping explicit environment precedence and `overrides=False` removal, and pass the normalized saved values to the smoke check; verify launcher tests that saved values apply, explicit exports win, and smoke receives saved rather than ambient values
- [x] 5.4 Document the setup questions, how to change budgets by rerunning setup, and the requalification effect of explicit exports in `docs/setup.md` and README; verify the documented prompts match the questionnaire labels

## 6. Qualification binding

- [x] 6.1 Extend the qualification identity `hardening` with the `agent` entry from D5, computed from the effective environment (saved values for managed launches) in both `check` and `qualify`; verify `tests/test_qualification.py` cases where setup qualifies the saved values, and an explicitly exported budget or timeout that differs makes the check report mismatched evidence and matching settings are accepted
- [x] 6.2 Extend `network/qualification_probe.py` to compare the effective agent cgroup limits with the identity values; verify the host `--qualification` suite passes and a synthetic mismatch fails the probe
- [x] 6.3 Ensure the requalification message names the hardening settings as a possible cause; verify with a qualification test asserting the message text

## 7. B05: pinned image inputs

- [x] 7.1 Pin the `Containerfile` per D8 (`CLAUDE_CODE_VERSION=2.1.316`, `OPENSPEC_VERSION=1.16.0`, base by digest, `ENV DISABLE_AUTOUPDATER=1`), capturing the digest under `CLAUDE_CONTAINER_MAINTENANCE=1`; verify a maintenance rebuild succeeds and `claude --version`/`openspec --version` report the pinned versions
- [x] 7.2 Add `tests/test_image_pins.py` that rejects unpinned/`@latest`/tag-only inputs and requires the pinned CLI to match the policy `tested.cli` version; verify it passes and fails on a mutated copy
- [x] 7.3 Document the maintenance update procedure in README and `docs/validation.md` (update pins, rebuild under maintenance, revalidate endpoint inventory on CLI changes, rerun setup/qualification, dated record); verify the steps are present and consistent with `container-launcher` image-operation rules

## 8. Integration and evidence

- [x] 8.1 Run the full credential-free suites on the host (wrapper, setup, `--setup-runtime`, runtime, `--network-policy`, `--network`, `--guard`, `--qualification`, image pins) and record results, initial failures and reruns in a new dated `docs/validation.md` section covering B01–B05 and the 1.1 baseline comparison
- [x] 8.2 Rerun `--container-setup` on the host for a provider installation accepting default budgets, and confirm `locally-qualified` status with the new identity and schema 2 preferences; verify the setup output, `setup.json` and the report file
- [x] 8.3 Mark B01–B05 complete in `todo.md` with an implementation note and the requalification migration; verify `openspec validate harden-session-baseline --strict` passes

## Workflow follow-up

- Archive the change after review, then commit and merge as requested by the user.
- Tag `sandbox-ref-2` only when the user asks.
