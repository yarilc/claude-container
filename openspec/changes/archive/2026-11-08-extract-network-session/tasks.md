# Tasks

## 1. Shared session helper

- [x] 1.1 Create `network/session.py` with the profile loader, fixed operation parsing and shared constants (relay port, guard and relay paths, readiness format, proxy variables). Verify that `python3 -I network/session.py` rejects unknown operations and arguments without side effects (unit test).
- [x] 1.2 Implement `prepare` (preflight, platform check, guard probe, digest, qualification input) by moving the current wrapper logic verbatim. Verify with `tests/test_session.py` cases for offline, provider and probe outputs, and refusal before any engine call on invalid inputs.
- [x] 1.3 Implement `start`: snapshot, interruptible proxy create and start, readiness deadline, bounded hardening verification, own process group and ownership markers for `stop`. Verify with fake-engine tests for success, readiness timeout, hardening mismatch, interruption after create, and refusal of foreign labels.
- [x] 1.4 Implement `agent-args` with NUL-delimited output for offline, provider, shell and probe modes. Verify that the argument lists match the current wrapper's for each mode and that special characters round-trip.
- [x] 1.5 Implement `stop` with deadline-bounded recovery by cid, stdout or label, ownership confirmation, removal, unconfirmed-cleanup warnings and the sanitized diagnostics tail. Verify with stalled-engine tests that it ends within the given deadline and never removes foreign containers.

## 2. Wrapper integration

- [x] 2.1 Replace the restricted blocks in `claude-container.sh` with `prepare`, `start`, `agent-args` and `stop` calls. Keep agent-specific env, state, credentials and command in the wrapper, and keep the fail-closed ordering (design D5). Verify with `bash -n` and the synthetic wrapper suite.
- [x] 2.2 Integrate cancellation and the shared deadline in `shutdown`: start process-group termination, then `stop --deadline` with the remaining budget, with order and statuses unchanged. Verify with `test_proxy_probe_timeout_and_interruption_clean_only_proxy`, `test_stalled_controls_and_repeated_signal_are_bounded` and the exit-status tests.
- [x] 2.3 Copy the real `session.py` into the `test_wrapper.py` restricted fixture, which keeps its synthetic `control.py`. Assert call order and arguments per mode. Verify that the full `test_wrapper.py` passes on the host.

## 3. Protection, identity and alignment

- [x] 3.1 Add `network/session.py` to `SHARED_CODE`, the setup `MANIFEST`, the control trusted-file list and the proxy image inputs only if needed. Verify with `test_qualification.py` and `test_setup.py` manifest tests.
- [x] 3.2 Extend `tests/test_alignment.py`: shared inventory includes `session.py` and `test_session.py`. Wrapper consistency requires the helper calls and the absence of in-line proxy lifecycle. Verify that it fails on a deliberately reintroduced in-line `control.py snapshot` call.

## 4. Documentation

- [x] 4.1 Update `network/README.md` (operation contracts), `docs/network-contract.md` (port checklist: copy `network/`, write `agent/`, integrate four calls), `AGENTS.md` and `README.md` where internal flow is described. Verify that the paths and commands mentioned exist.

## 5. Acceptance

- [x] 5.1 Run the synthetic suites here where possible, and on the host `test_setup.py` and `test_wrapper.py`. Record outcomes in `docs/validation.md`.
- [x] 5.2 On the host, run `--guard`, `--guard-idle`, `--network-policy`, `--network`, `--qualification` and `--setup-runtime`, then a managed `--container-setup` with offline and provider launches. Record the results, initial failures included, in `docs/validation.md`.
- [x] 5.3 Repeat the simulated port with a dummy profile, including `test_session.py`. Verify that the shared files are identical and the shared suites pass unchanged.

## Workflow follow-up

- Archive and commit; tag `sandbox-ref-2` after the remaining Wave 0 changes.
