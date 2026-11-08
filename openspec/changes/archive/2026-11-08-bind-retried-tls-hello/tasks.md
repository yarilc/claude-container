# Tasks

## 1. Single-source revisions and cleanup (N24)

- [x] 1.1 Add `network/revisions.py` with `GUARD_REVISION`, `GUARD_REQUIRED_ABI` and `TLS_ENFORCEMENT`, and import it in `control.py`, `proxy.py`, `session.py` and `tls_client_hello.py` in place of literals (design D5). Add it to the proxy `Containerfile` COPY line, the `setup/common.py` installation list and the shared lists in `tests/test_alignment.py`. Verify that `grep -rn "abi3-seccomp-mux-v1\|tls-clienthello-sni" network/*.py` matches only `revisions.py` and that the setup manifest tests pass.
- [x] 1.2 Add a `tests/test_guard.py` check that parses `GUARD_REVISION` and `GUARD_REQUIRED_ABI` from `network/guard.c` and compares them, and the built `--version` line when the guard is available, with `revisions.py`. Verify that it fails on a deliberately edited `guard.c` define and passes after reverting the edit.
- [x] 1.3 Remove the per-session `resolv.conf` write from `network/control.py`, keeping `network/resolv.conf` in the trusted inputs. Verify with a control/session test that the prepared session directory does not contain `resolv.conf`, and that the restricted launch still mounts `network/resolv.conf`.
- [x] 1.4 Run the host guard probe in `session.py prepare` with piped stdout/stderr, relayed to stderr, and fail with the actionable probe message and the original status (design D6). Verify in `tests/test_session.py` that the probe output is relayed when the caller's stderr is a socket, and that a stub probe exiting 78 silently produces the message and status 78.
- [x] 1.5 Make `tests/test_tls_proxy.py` add `tests/` to `sys.path` before importing `test_tls_client_hello`. Verify that `python3 -m unittest tests.test_tls_proxy` from the repository root and `discover -s tests` both import and run it.

## 2. Retried ClientHello parser and observer (N22)

- [x] 2.1 Extend `tls_client_hello.ClientHello` to start from already-buffered bytes, skip leading ChangeCipherSpec (exact payload `0x01`) and type-23 records in retry mode, and reject any other record type before the handshake, while keeping the existing limits and reason codes (design D3). Verify with unit tests for CCS/early-data prefixes, invalid CCS payloads, other content types, fragmentation and overflow.
- [x] 2.2 Add a bounded upstream observer that classifies the first handshake message as HelloRetryRequest, ordinary ServerHello or non-TLS, across arbitrary record and chunk boundaries and with fixed storage (design D1). Verify with unit tests using the RFC 8446 HelloRetryRequest random, an ordinary TLS 1.2/1.3 ServerHello, an alert-first response, non-TLS bytes and byte-by-byte fragmentation.
- [x] 2.3 Add the `tls-retry-identity` reason and set `TLS_ENFORCEMENT` to `tls-clienthello-sni-v2` (design D3/D4). Verify that the redaction tests show only fixed reason codes and the authorized host/port, and that a v1 manifest or readiness line is rejected.

## 3. Proxy retry gate (N22)

- [x] 3.1 In `network/proxy.py`, add the retry gate between `inspect()` and `mux.bridge`, as specified in design D1 and D2:
  - it holds client bytes in the existing reservation until the upstream decision;
  - it forwards upstream bytes only after each chunk is classified;
  - it validates the retried ClientHello against the CONNECT host and forwards the original bytes once;
  - it hands off without data loss or reordering.

  Verify with `tests/test_tls_proxy.py` cases for each of the following:
  - a retry with matching SNI, with CCS and early-data prefixes;
  - a retry with a different, missing or ECH-bearing SNI: rejection, with an upstream byte counter proving that no byte of the second hello was forwarded;
  - a second hello sent before the retry is observed;
  - no retry, with TLS 1.2 flights and encrypted records passing unchanged;
  - deadline expiry, premature EOF and overflow;
  - concurrent tunnels, where one tunnel's failure leaves the others working.
- [x] 3.2 Confirm that the reservation is released on every gate exit path and that `inspection_storage` returns to zero. Verify with a proxy test that runs failing and successful retry gates and asserts the counter afterwards.
- [x] 3.3 Add a controlled real-TLS regression to the TLS binding fixture. The Python `ssl` server is restricted to a group the client does not offer first, so that it sends a real HelloRetryRequest:
  - matching SNI completes with certificate verification;
  - an SNI switch on the retried hello is rejected through the production guard, relay and proxy.

  Verify through the existing `--network`/TLS binding runtime target. If the local OpenSSL cannot force a HelloRetryRequest, record that as unavailable.

## 4. Documentation

- [x] 4.1 Update `docs/network-contract.md`, `network/README.md`, `README.md` and the provider help/setup limitations text:
  - the initial and retried TLS 1.3 ClientHellos are bound;
  - TLS 1.2 renegotiation is an uninspected, accepted limitation, with its reason and the absence of decryption;
  - the enforcement revision is `tls-clienthello-sni-v2`, and the probe failure message is documented.

  Verify with `grep` that no `tls-clienthello-sni-v1` remains outside historical validation records, and that the help test strings match.
- [x] 4.2 Mark N22 and N24 complete in `todo.md` with a short completion note. Verify by reading `todo.md`.

## 5. Acceptance

- [x] 5.1 Run the synthetic suites available here, and on the host the full `test_wrapper.py`, `test_setup.py`, `test_session.py`, `test_tls_client_hello.py`, `test_tls_proxy.py` and `test_alignment.py`. Record the outcomes, initial failures included, in a new `docs/validation.md` section.
- [x] 5.2 On the host, run the `--guard`, `--network-policy`, `--network`, `--qualification` and `--setup-runtime` targets, then a managed `--container-setup` with an offline and a provider launch:
  - an old proxy image fails readiness before the rebuild;
  - the rebuilt installation passes.

  Record the results and, if observed, whether real Anthropic endpoints send a HelloRetryRequest, or record that as unavailable.

## Workflow follow-up

- Archive with spec sync and commit on a branch, then fast-forward `main` when asked. The user pushes.
- Continue Wave 0 with N21, then B01–B05, then tag `sandbox-ref-2`.
