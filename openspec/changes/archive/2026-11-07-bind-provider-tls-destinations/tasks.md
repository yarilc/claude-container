# Tasks

N15–N17 refer to the local TLS follow-up. The tracked acceptance record belongs in `docs/validation.md` and `docs/network-contract.md`; the ignored `todo.md` is not the sole source of completion evidence. Implementation must not access real credentials or issue model requests without separate authorization.

## 1. Bounded ClientHello parser (N16, N17)

- [x] 1.1 Add `network/tls_client_hello.py` with incremental TLS record/handshake reconstruction and strict enclosing-vector validation; verify generated TLS 1.2/1.3 ClientHellos parse and every byte split preserves the same result in `tests/test_tls_client_hello.py`.
- [x] 1.2 Enforce one normalized DNS SNI matching CONNECT and reject missing/empty/multiple/duplicate/conflicting names, unknown name types, IP literals, invalid encoding, deceptive suffixes and malformed lengths; verify positive normalization cases and negative mutation cases with no accepted ambiguous input.
- [x] 1.3 Reject non-TLS, SSLv2 framing, unsupported-only negotiation, duplicate extensions and ECH including GREASE; verify real generated hello mutations and valid unknown ordinary extensions/GREASE version values behave according to the supported-encoding contract.
- [x] 1.4 Enforce the design's handshake/wire/record-count limits without allocating from untrusted lengths; verify exact-limit and over-limit vectors, record fragmentation, coalesced trailing data, early EOF, and deterministic malformed-input campaigns with bounded completion and storage.
- [x] 1.5 Document supported encodings, normalization, limits and parser failure semantics in `network/README.md`; verify examples agree with parser tests and distinguish the initial ClientHello guarantee from application identity.

## 2. Trusted proxy inspection gate (N16, N17)

- [x] 2.1 Integrate inspection after policy/DNS/address authorization and OPEN_OK but before any upstream client write or bridge; verify matching bytes are forwarded once, mismatches/non-TLS forward zero bytes, and ordinary CONNECT clients do not deadlock in proxy integration tests.
- [x] 2.2 Add the absolute inspection deadline and per-stream/session storage reservation accounting; verify slow incremental input cannot extend the deadline, concurrent inspections respect the additional 160 KiB/stream and 10 MiB/session storage budgets, and all exit paths release reservations.
- [x] 2.3 Close rejected post-OPEN_OK streams without sending a second OPEN response; verify slot reuse, valid-stream progress alongside rejected streams, cancellation, half-close, channel/proxy death, and existing mux credit/backpressure bounds in `tests/test_mux.py` and proxy integration tests.
- [x] 2.4 Emit bounded TLS identity/malformed/unsupported/ECH/overflow/timeout denial reasons using only the authorized host and existing audit fields; verify secret-like SNI, control characters and oversized inputs never appear in logs and log caps remain active.
- [x] 2.5 Document OPEN_OK/HTTP 200 inspection semantics, upstream TCP-only visibility on rejection, timeout behavior and redacted reason codes in `network/README.md`; verify documented states match the integration tests, including direct mux access without the relay.

## 3. Enforcement identity and protected release packaging (N16)

- [x] 3.1 Add mandatory `tls-clienthello-sni-v1` identity to protected manifest generation, proxy manifest validation, readiness output and wrapper comparison; verify missing/wrong/old identities fail before an agent sentinel runs using policy and wrapper regressions.
- [x] 3.2 Include parser and any enforcement identity module in `network/Containerfile`, applicable container ignore rules and `setup/common.py` release inputs; verify a clean image imports all modules and synthetic setup inventory tests confirm complete protected candidates without copied credentials.
- [x] 3.3 Extend candidate setup smoke/runtime checks to reject incompatible proxy images while preserving maintenance consent, last-working-release rollback and help independence; verify synthetic setup cases and disposable `--setup-runtime` acceptance without real service activation or credentials.
- [x] 3.4 Document matching image/release deployment, ECH/GREASE incompatibility, identity failures and rollback effects in README, `docs/setup.md` and `network/README.md`; verify operator steps retain exact policy inventories and do not advertise the new guarantee after rollback to an old proxy.

## 4. Controlled production-path regression evidence (N17)

- [x] 4.1 Extend the controlled TLS fixture with two hostnames sharing one address, synthetic CA/certificates and upstream byte counters; verify an unfiltered alternate-hostname TLS positive control and a matching-name proxy request both succeed with certificate verification.
- [x] 4.2 Add guarded regression coverage for approved CONNECT with different SNI, missing/malformed/duplicate/conflicting SNI, non-TLS and ECH; verify rejection and zero upstream client bytes through the production guard, relay and proxy using synthetic state and test-only explicit-address routing.
- [x] 4.3 Exercise valid and invalid hellos fragmented across records and multiplex DATA frames, coalesced trailing bytes, inspection size/count/deadline limits and direct inherited-channel use; verify valid byte preservation and rejected zero-byte forwarding through controlled integration fixtures.
- [x] 4.4 Exercise concurrent valid/rejected/stalled streams, repeated requests beyond active concurrency, channel/proxy failure and stream-slot/resource recovery; verify healthy progress, bounded buffers/tasks, owned cleanup and no unfiltered reconnect.
- [x] 4.5 Cover each bundled API/account hostname inventory with controlled TLS resolution/certificates and repeat TLS 1.2/1.3, retry/resumption where supported, streaming, long-lived/WebSocket, bad-certificate and CA off/on checks; verify original trust validation, exact CA mount/variables and profile destination restrictions remain effective.
- [x] 4.6 Record the reported 2026-11-07 Cloudflare observation and the exploration's upstream-stub result in `docs/validation.md` with separate provenance and limitations; verify neither is presented as the new controlled production acceptance or arbitrary application-content access.
- [x] 4.7 Run the new controlled production gate on WSL 6.6.87.2 x86_64 / usable ABI 3 / rootless Netavark server 4.9.3, including `bash tests/run-runtime.sh --guard`, `--network-policy` and `--network`; record actual commands, versions, protected image/policy/guard/enforcement identities, pass/fail/unavailable results and remaining authenticated gaps in `docs/validation.md`. Mandatory unavailable or failed production cases keep N16/N17 open.

## 5. Provider guarantee and completion review (N15–N17)

- [x] 5.1 Update wrapper help, README, `docs/setup.md`, network README/contract and AGENTS.md to distinguish CONNECT authority/address, initial SNI binding and encrypted application routing; verify help/setup guidance explicitly retain shared-service, encrypted Host, provider-forwarding and allowed-service data-transfer limits without claiming exclusive Anthropic application access.
- [x] 5.2 Add the N15–N17 implementation/evidence map to tracked documentation; verify every acceptance scenario links to a completed test or an explicit unavailable result, current authenticated evidence is separate from historical passes, and N01 sibling rollout remains pending.
- [x] 5.3 Run parser, network policy, mux, wrapper and setup unit suites, Bash syntax checks on changed scripts, `git diff --check`, and `openspec validate bind-provider-tls-destinations --strict`; verify all mandatory synthetic checks pass and protected-native checks use the supported Podman harness rather than weakened path validation.
- [x] 5.4 Review end-to-end evidence and update the local N15/N16/N17 checkboxes only for completed scope; verify zero-byte rejection, new-image readiness, both-profile controlled compatibility, resource/failure closure and measured production acceptance are documented before declaring the follow-up resolved. Real-key API checks remain optional, and no real login/refresh/model request is run without separate authorization.
