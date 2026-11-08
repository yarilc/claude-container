# Tasks

## 1. Agent profile and loader

- [x] 1.1 Create `agent/profile.json` with the Claude values from design D2, and move `network/policies/default.json` to `agent/policies/default.json` unchanged. Verify with `git diff -M --stat` that the policy move is a pure rename.
- [x] 1.2 Implement the closed-schema loader in `network/agent_profile.py` (D2): unique keys, schema version, field patterns, trusted-path checks, and derived variable/label/install names. Verify with new unit tests for valid, malformed, duplicate-key, unknown-key, invalid-pattern and unprotected-path profiles.
- [x] 1.3 Make `network/policy.py` load provider policies from `agent/policies/` and take the profile names and required hosts from policy data instead of literals. Verify that `test_network_policy.py` passes and that the effective policy is byte-identical to the pre-change output for both profiles.

## 2. Agent-neutral internals

- [x] 2.1 Rename the in-container paths, guard binary, header guards and multiplex marker to the neutral names in design D3, across `network/guard.c`, `guard_*.h`, `build-guard.sh`, `Containerfile`, `mux.py`, `relay.py`, `proxy.py`, `control.py`, the qualification modules, the root `Containerfile` and `claude-container.sh`. Verify that the guard builds and `test_guard.py`, `test_mux.py` and `test_tls_*.py` pass.
- [x] 2.2 Update the guard source identity and the qualification `CODE` list for the renamed guard, and add `agent/profile.json` and `agent/policies/default.json` to `CODE` but not to `GUARD_INPUTS` (D5). Verify with `test_qualification.py`, including a new case where a changed profile invalidates a matching report.

## 3. Shared code reads the profile

- [x] 3.1 Replace the per-agent host identities in `network/` (image names, labels, variable names, installation and state names) with profile-derived values. Verify that `test_network_runtime.py` and `test_qualification.py` pass.
- [x] 3.2 Replace the agent-native behaviour in `setup/` with profile-driven logic (D4): configuration directory variable, approval-bypass variable, shared/private state layout, credential variables, login assistance and the authentication-to-policy-profile mapping. Verify that `test_setup.py` passes and that setup prompts, saved `setup.json` and the generated managed launcher are unchanged for a recorded scripted session.
- [x] 3.3 Install the profile and policy with the protected installation, and restore them on rollback (container-setup delta). Verify with setup tests covering installation from a checkout, an unsafe profile path and rollback restoring a matching profile.
- [x] 3.4 Make the wrapper and qualification reject a profile taken from the workspace or current directory. Verify with a wrapper test that plants a decoy `agent/profile.json` in the workspace.

## 4. Copyability guard rails

- [x] 4.1 Make the shared network/guard/mux/TLS/qualification/setup tests and fixtures derive names from the loaded profile (D8). Keep `test_wrapper.py` and `test_runtime.py` agent-specific. Verify that the full synthetic suite passes.
- [x] 4.2 Add the literal-scan alignment test (D7) over `network/`, `setup/` and the shared tests, with a minimal documented allow-list. Verify that it passes, and that it fails when a temporary `claude` literal is introduced in `network/control.py`.
- [x] 4.3 Add the wrapper consistency test (D6) checking that `claude-container.sh` uses the variable names, images, labels and neutral paths that the profile and shared constants produce. Verify that it fails on a deliberate mismatch.

## 5. Documentation

- [x] 5.1 Update `network/README.md`, `docs/network-contract.md` and `README.md` for the neutral internal paths, the `agent/` variation point and the requalification needed after upgrade.
- [x] 5.2 Update `AGENTS.md` with the split between shared and agent-specific files (`network/`, `setup/` and shared tests are copied unchanged; `agent/`, the wrapper, the `Containerfile` and wrapper tests are per-agent) and with the rule that no agent-specific literal may enter shared code.
- [x] 5.3 Verify the docs by checking that every path, file and command they mention exists.

## 6. Integration acceptance

- [x] 6.1 Rebuild the guard, proxy and agent images. Run the full synthetic suites and the real WSL guard, network, qualification and setup-runtime acceptance, including concurrent TLS streams, idle sessions, CA off/on and owned cleanup. Record initial failures and final results in `docs/validation.md`.
- [x] 6.2 Run `--container-setup` against an existing protected installation. Verify that the stale qualification is refused with guidance, that requalification succeeds, that launches in offline and provider modes work, and that rollback restores the previous installation.
- [x] 6.3 Simulate a port by copying `network/`, `setup/` and the shared tests to a scratch checkout with a dummy profile (different prefix, images and labels). Verify that the literal scan and the profile/loader/policy unit tests pass there unchanged. Record the result in `docs/validation.md`.

## Workflow follow-up

- Archive the change once acceptance is recorded, then tag the reference baseline (for example `sandbox-ref-1`) to be ported in Wave 3.
- Update the four sibling `todo.md` files so their port tasks refer to the profile-based copy.
