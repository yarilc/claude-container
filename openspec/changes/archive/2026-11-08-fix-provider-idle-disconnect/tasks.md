# Tasks

## 1. Multiplex receive semantics

- [x] 1.1 Separate unbounded asynchronous first-byte waiting from a named absolute 10-second frame completion budget in `network/mux.py`, preserving header validation, payload limits and existing operation deadlines; verify idle-before-first-OPEN and idle-between-OPEN regression tests fail against the old implementation and pass against the fix.
- [x] 1.2 Add component tests for both receiver directions covering stalled partial headers, stalled payloads, trickled bytes that cannot extend the deadline, and valid fragmentation; verify with `python3 -m unittest discover -s tests -p test_mux.py -v` and retain malformed-frame, concurrency and backpressure coverage.
- [x] 1.3 Document idle channel versus incomplete-frame and stream deadlines in `network/README.md` and the relevant network contract text; verify the documented values match the code and explicitly state that no heartbeat or reconnect is required for idle reuse.

## 2. Relay lifecycle and failure isolation

- [x] 2.1 Add actual relay lifecycle tests using controlled local peers and shortened test-only deadlines, proving the listener survives inactivity and a later CONNECT succeeds; verify no relay restart or replacement channel occurs and all test processes/sockets are cleaned up.
- [x] 2.2 Add tests for normal idle stream expiry followed by a new stream, EOF during quiet receive, and receiver/session cancellation; make only necessary cleanup corrections if tests expose defects, and verify prompt termination, pending-client wakeup, stream isolation and no reconnect using component tests plus `test_tls_proxy.py` and `test_network_policy.py`.

## 3. Production idle acceptance and rollout guidance

- [x] 3.1 Add a dedicated opt-in controlled TLS acceptance case through the production guard, relay and proxy: successful verified request, acknowledged tunnel close, at least 305 seconds without channel traffic, then another successful verified request in the same session with unchanged production deadlines; verify the old implementation fails and the fix passes, and scope extended harness timeouts to this case while retaining bounded cleanup.
- [x] 3.2 Document the slow acceptance invocation and matched runtime/proxy rebuild, protected installation, normal requalification, relaunch and rollback procedure in the relevant network/setup documentation; verify no new writable policy input, syscall mock, credential use or qualification exception is introduced.

## 4. Integration validation and evidence

- [x] 4.1 Run `python3 -m unittest discover -s tests -p test_wrapper.py -v`, the affected multiplex/policy/TLS parser/TLS proxy suites, `bash -n` on any changed shell scripts, and `git diff --check`; record outcomes and resolve failures attributable to this change.
- [x] 4.2 With prepared images and an eligible rootless service, run the opt-in production idle case and relevant guard, network and qualification acceptance, retaining denied destination, SNI mismatch/zero-byte and proxy-loss controls; record passed/failed/unavailable results, exact environment and image/code identities in `docs/validation.md`, distinguishing accelerated component tests, actual 305-second production evidence and unavailable authenticated compatibility.
