# Tasks

## 1. Setup acknowledgement

- [x] 1.1 Add `choose_network(default)` in `setup/setup.py`, used by the first network question and by the delegation-conflict `change-network` path. In provider mode it prints the residual-exfiltration notice, built from `PROFILE.auth[*]['hosts']`, and requires `yes(..., False)`; declining asks for the mode again. Verify by reading that no other `ask('Network mode'` call remains.
- [x] 1.2 Update `tests/test_setup.py`:
  - **Helpers:** `answers()` and the patched-`input` sequences include the acknowledgement for provider mode.
  - **New tests:**
    - provider, decline, then offline ends with offline and no provider notice repeated after the switch;
    - the delegation conflict switching to provider asks for the acknowledgement;
    - offline and unrestricted show no notice;
    - `setup.json` has no acknowledgement field.
  - Verify the setup suite passes.
- [x] 1.3 Document the acknowledgement prompt in `docs/setup.md` and verify the prompt text quoted there matches `setup/setup.py`.

## 2. Narrowed account profile

- [x] 2.1 Set the account hosts in `agent/profile.json` to `["api.anthropic.com", "platform.claude.com"]`. In `agent/policies/default.json`:
  - set the matching account destinations;
  - set revision `anthropic-2026-11-08-v2` and `source_date` `2026-11-08`;
  - add the static inventory to `sources` and `tested`.

  Verify that `policy.validate` with the agent-profile rules accepts the policy and rejects a copy that re-adds `claude.ai` to `anthropic-account`.
- [x] 2.2 Add or extend policy tests in `tests/test_network_policy.py` or `tests/test_wrapper.py`:
  - the shipped account profile is exactly the two hosts;
  - re-adding a removed host to the base profile fails with the exact-base-profile error;
  - a separately named custom account profile with `claude.ai` is accepted.

  Verify the suites pass.
- [x] 2.3 Update `tests/test_network_runtime.py` (controlled account inventory and certificate SANs) and `tests/network_tls_fixture.py`. Add a controlled check that `claude.ai` is denied under the account inventory. Verify by inspection and by the host `--network` run in 4.2.
- [x] 2.4 Update the account inventory sentences in README, `docs/network-contract.md`, the `network-egress` scenario wording and AGENTS.md (if it lists hosts). Verify with `grep -rn "claude\.ai\|claude\.com" --exclude-dir=archive`: only intentional mentions remain (validation history, removed-host statements, user-facing links).

## 3. Disclosure documentation

- [x] 3.1 Add the short foreign-credential disclosure to the `claude-container.sh` help (provider mode section) and to the existing setup provider description lines. Verify `bash claude-container.sh --help` shows it and the wrapper help tests pass.
- [x] 3.2 Add a "Residual exfiltration to allowed services" section to README and `docs/network-contract.md`. It covers:
  - the channel;
  - the hosts of each base profile;
  - that only offline mode removes the channel;
  - that the disclosure and the host reduction do not prevent it.

  Verify it is linked from the provider identity section of each document.
- [x] 3.3 Add the credential-injecting interception evaluation to `docs/network-contract.md`: design, trade-offs, conflict with no-decryption, and unimplemented status that needs an explicit operator decision. Verify that no code path or option implies it exists (`grep -rn -i "intercept" network/ claude-container.sh setup/`).

## 4. Acceptance

- [x] 4.1 Run the credential-free suites available in the sandbox (policy, TLS, mux, session, setup/wrapper where the environment allows). Record initial failures and reruns.
- [x] 4.2 Ask the operator to run on the host:
  - the wrapper, setup, `--network-policy`, `--network`, `--guard`, `--qualification` and `--setup-runtime` suites;
  - a rebuild and rerun of `--container-setup` with the acknowledgement.

  Verify all pass via the supplied log.
- [x] 4.3 Ask the operator to run the authenticated checks through the restricted wrapper with the narrowed profile:
  - a fresh isolated login from `--container-setup`;
  - an ordinary request (`ACCOUNT_PROFILE_OK`);
  - a refresh after a forced expiry in the isolated state (`ACCOUNT_REFRESH_OK`).

  The operator reports exit codes and the exit denial records. Verify that no Anthropic host is denied.
- [x] 4.4 If 4.3 fails because of a removed host:
  - apply design D3: restore the four-host profile under `anthropic-2026-11-08-v3`;
  - record the denials;
  - revert the test and documentation host statements in 2.2–2.4;
  - leave a login-profile follow-up note in `todo.md`.

  Otherwise mark this task done as not needed. Verify that the policy matches the outcome recorded in `docs/validation.md`.
- [x] 4.5 Add a dated "Residual exfiltration disclosure and account profile reduction (N21)" section to `docs/validation.md`. It records:
  - the static inventory method;
  - the suite results;
  - the authenticated results (CLI version, policy revision, exit codes, denials), without credentials, URLs or bodies.

  Mark N21 done in `todo.md` with a summary. Verify that `openspec validate disclose-residual-exfiltration` passes.

## Workflow follow-up

- Archive the change after review and commit it on its own branch; the user pushes.
