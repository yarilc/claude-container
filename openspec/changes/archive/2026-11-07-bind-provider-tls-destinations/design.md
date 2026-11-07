# Design

## Context

See `proposal.md` for motivation and `specs/network-egress/spec.md` for the contract. `Proxy.tunnel` currently calls `connect`, sends `OPEN_OK`, then calls the opaque `mux.bridge`. `Relay.handle` waits for `OPEN_OK` before returning HTTP 200; clients normally send ClientHello only after that response. Requiring ClientHello before OPEN_OK would deadlock ordinary clients.

The guard confines the agent and relay, while the external proxy alone controls upstream resolution and forwarding. DATA frames are at most 16 KiB, the active-stream limit is 64, and credit bounds queued data to 256 KiB per stream / 16 MiB per channel. These limits do not themselves validate TLS or bound a new reassembly buffer.

`control.py` snapshots a protected manifest and the wrapper validates proxy readiness against policy, guard digest and mux version. An immutable image reference prevents mutation but does not prove that the image implements this change. Setup explicitly inventories release files in `setup/common.py`, and `network/Containerfile` explicitly copies proxy modules.

## Goals / Non-Goals

**Goals:** Add a small auditable parser, enforce it on every proxy-side logical tunnel, and establish a reproducible acceptance gate for the initial plaintext ClientHello identity. Preserve supported end-to-end TLS, streaming, isolation, and failure closure.

**Non-Goals:** Authenticate the upstream on behalf of an untrusted client, terminate TLS, parse encrypted application traffic, or continuously prove application identity after the initial handshake. The client retains certificate validation. Later encrypted routing, TLS renegotiation, and service forwarding are outside the initial-ClientHello guarantee. This change does not turn SNI into application isolation.

## Decisions

### 1. Inspect in the trusted proxy after OPEN_OK, before upstream writes

Retain the current authority/policy/DNS/address checks and upstream TCP connection before OPEN_OK. Return OPEN_OK and HTTP 200 to permit the client to send TLS, but hold all client bytes in an inspection phase. No upstream application reader/bridge starts until validation succeeds. On success, flush the original buffered bytes exactly once, then enter the existing bridge. On rejection, discard buffers and close the affected stream and upstream. OPEN_OK means permission to submit inspectable bytes, not completed TLS authorization.

The upstream may observe a TCP connection with no application bytes for rejected attempts. Tests must distinguish TCP accept from receiving ClientHello or completing TLS. Delaying TCP connect until inspection is a possible future optimization, not required for the no-client-bytes guarantee.

Alternative rejected: inspection in the relay alone, because agent-controlled code can bypass it using the inherited channel. Alternative rejected: waiting for ClientHello before OPEN_OK, because it blocks normal CONNECT clients. The mux v1 frame format need not change; use CLOSE for a post-OPEN_OK rejection, not a second OPEN response. Protocol faults still close the channel; TLS input rejection closes only the affected stream.

### 2. Use a focused incremental parser with explicit supported encodings

Add `network/tls_client_hello.py`, using standard-library binary parsing and the existing `policy.hostname` normalization. The parser handles arbitrary byte splits, reconstructs handshake bytes across TLS records, and validates all enclosing lengths before slicing. Require handshake record framing and a first handshake message of ClientHello; reject invalid/empty records, premature non-handshake records, truncation and inconsistent lengths. Validate legacy version, session ID, cipher-suite and compression vectors, extension boundaries, and TLS 1.2/1.3 negotiation representation. Do not infer TLS 1.3 solely from the legacy record version. Unknown ordinary extension types and GREASE version/cipher values must not by themselves invalidate otherwise supported negotiation; duplicate extension types or ambiguous SNI do.

Require exactly one server_name extension containing exactly one nonempty DNS host_name, ASCII-valid under the existing hostname grammar. Reject IP literals, unknown name types, trailing bytes, multiple names, duplicate extensions, malformed lengths, missing SNI, and mismatch after normalization. Support TLS 1.2 legacy ClientHello and TLS 1.3 supported_versions encoding. Reject SSLv2-style framing and negotiations that cannot offer TLS 1.2 or TLS 1.3.

Preserve the wire representation; normalized identity is used only for comparison. Bytes consumed beyond the ClientHello within the bounded final chunk must remain buffered and ordered, including following records or early data. No prefix is forwarded during inspection. Once the initial hello passes, subsequent encrypted traffic remains opaque. Explicitly test normal TLS 1.3 retry/resumption behavior as compatibility rather than claiming inspection of all later handshake identities.

Alternative rejected: a substring/regex search for SNI, which can match unrelated extensions or payloads. Alternative rejected: a terminating TLS library endpoint, which would change trust and certificate handling. A narrowly scoped parser avoids a new runtime dependency but requires substantial malformed-input coverage.

### 3. Reject ECH conservatively and publish the compatibility cost

Reject the encrypted_client_hello extension, including GREASE ECH, even when outer SNI matches. Also reject known retired encrypted-name extensions: ESNI `0xffce` and early ECH `0xff02`, `0xff03`, `0xff04`; these are unverifiable negotiation rather than ordinary unknown extensions. A passive parser cannot reliably treat a GREASE-looking offer as proof that the effective name is visible. Do not strip extensions or retry through an unchecked tunnel. Unsupported clients must use a separately documented supported client configuration or remain incompatible.

Protocol references: [TLS 1.3, RFC 8446](https://www.rfc-editor.org/rfc/rfc8446.html), [SNI, RFC 6066 section 3](https://www.rfc-editor.org/rfc/rfc6066.html#section-3), and [ECH / GREASE ECH, RFC 9849 sections 6.1–6.2](https://www.rfc-editor.org/rfc/rfc9849.html#section-6.2). These define parsing and compatibility considerations; they do not establish sandbox acceptance.

### 4. Bound inspection independently of mux credit

Use protected implementation constants, not agent-configurable settings:

| Resource | Proposed bound |
| --- | --- |
| Reassembled ClientHello including handshake header | 64 KiB |
| Retained wire input including record headers and final-chunk surplus | 96 KiB |
| TLS records consumed during inspection | 128 |
| TLS plaintext record payload | 16 KiB |
| Absolute inspection deadline after OPEN_OK | 10 seconds |
| Additional retained wire + handshake storage | 160 KiB per inspecting stream, 10 MiB per 64-stream session |

Do not allocate based on declared lengths. Incremental reads and retained buffers must stay within these limits, including transient copies; enforce a separate global reservation/counter for parser storage and retain existing mux queue/credit bounds. Small fixed parser metadata is bounded by the 64-stream limit. The deadline is absolute and cannot be refreshed by slow input. Timeout, EOF, cancellation or channel death releases buffer reservations and closes the upstream; no retry path bypasses inspection.

These are conservative compatibility limits below the mux credit window. Limits may be reduced during implementation if measured resource accounting requires it; any increase requires revisiting memory accounting and boundary tests rather than silently accepting larger allocations.

### 5. Version the enforcement separately from the guard and mux ABI

Introduce a required `tls-clienthello-sni-v1` proxy enforcement identity in the protected session manifest, proxy validation, readiness record and wrapper comparison. Preserve the existing guard revision and mux wire version when their semantics do not change. An old image must fail readiness, and a new proxy must reject a manifest without the required field. Test old/new mixed installations before agent execution.

Include the parser and any identity module in image COPY inputs, `.containerignore` rules as needed, and setup's explicit release inventory. Candidate setup builds and smoke-checks the compatible immutable image before switching the managed launcher. This prevents claiming the stronger guarantee while launching an older image.

### 6. Make zero forwarded bytes and usable positive controls the acceptance oracle

Extend the controlled TLS fixture to serve approved and alternate test hostnames at the same address, using a synthetic CA and certificates valid for each. A test-only explicit-address policy/resolver fixture isolates local test routing without weakening production address checks. An unfiltered control must complete alternate-name TLS with verification; through the production proxy the same alternate-name ClientHello under the approved CONNECT must fail with zero upstream client bytes. A matching-name tunnel must succeed with verification. Record raw accepted-byte counts on the controlled server, not production logs.

Layer evidence into parser tests, proxy/mux integration, production guard/relay acceptance, and production wrapper/setup acceptance. Feed malformed and fragmented hellos through direct mux calls as well as CONNECT. Run valid and rejected streams concurrently; assert valid-stream progress, queue/memory bounds, slot reuse, timeout cancellation and channel-death cleanup. Keep routine fixtures independent of public CDN routing, real credentials and model requests.

Exercise matching TLS for both API and account profile inventories using controlled resolution and test certificates, preserving their host/port restrictions. Repeat certificate denial, host-CA off/on, streaming, long-lived and WebSocket transport fixtures. Historical authenticated login/refresh evidence does not certify the new proxy. Repeating real authentication requires separate approval; record unavailable current flows honestly and do not infer them from synthetic tests.

### 7. Track provenance and completion independently

Copy the reported 2026-11-07 Cloudflare observation from the ignored local TODO into `docs/validation.md` during implementation, explicitly preserving its reported status and missing metadata. The exploration's in-memory upstream-stub check only demonstrated transparent byte forwarding; it did not perform certificate validation or execute the production guard. New controlled acceptance must have its own dated environment, CLI, policy/image/guard identities and results.

Update README, network README/contract, wrapper help, setup guidance and AGENTS.md to describe the effective boundary. Record the N15–N17 mapping in tracked docs; update the local TODO only when its corresponding work is verified, without changing its tracked/ignored status. N01 remains separate.

## Risks / Trade-offs

- Parser disagreement or incomplete length checks -> Validate full enclosing vectors, reject ambiguity, and test mutated real ClientHellos plus deterministic adversarial inputs and every split boundary.
- ECH/GREASE or larger future ClientHellos become incompatible -> Fail with bounded reason codes and document tested versions; do not weaken enforcement to restore compatibility.
- Buffer copies or slow clients consume extra memory -> Enforce independent inspection reservations, absolute deadlines, stream caps and concurrency tests.
- OPEN_OK may be mistaken for final authorization -> Document the inspection phase and verify client bytes never reach upstream on rejection.
- Matching SNI is mistaken for provider exclusivity -> Keep encrypted Host, shared-service routing and provider forwarding limits visible in operator-facing guidance.
- Mixed protected release and proxy image silently reduce protection -> Mandatory enforcement identity, old-image negative tests, candidate smoke gate and atomic managed release activation.

## Migration Plan

1. Implement and validate the parser, proxy gate, enforcement identity and fixtures before changing operator-facing completion claims.
2. Build the new immutable proxy image and a protected candidate release containing all parser/identity inputs; retain existing exact maintenance consent.
3. Run synthetic suites and the controlled WSL ABI-3 production acceptance gate, then setup smoke tests. Keep the candidate inactive when mandatory evidence fails or is unavailable.
4. Activate through the existing managed setup release switch after candidate verification. Manual installations must deploy the matching protected code and image together. No policy hostname expansion or guard relaxation is needed.
5. Roll back a failed candidate before activation using existing last-working-release behavior. Rolling back an activated release to a historical proxy also rolls back the stronger guarantee and must be reported explicitly; if that guarantee is required, use offline mode until a compatible release passes. Never advertise the new guarantee for an old release.
