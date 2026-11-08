# Design

## Context

- **Proxy flow.** `Proxy.tunnel` in `network/proxy.py`:
  1. Connects upstream.
  2. Sends `OPEN_OK`.
  3. Runs `inspect()`. This feeds client DATA into `tls_client_hello.ClientHello` until one ClientHello validates, then writes the original wire bytes upstream.
  4. Hands both directions to the generic `mux.bridge`.

  Nothing inspects later bytes. The parser stops at the first complete ClientHello. Any bytes coalesced after it are forwarded with it.
- **Inspection bounds.** Each inspection reserves `STORAGE` (`MAX_HELLO + MAX_WIRE`) against a session budget of `STORAGE * MAX_CONNECTIONS`. A 10-second deadline applies (`INSPECTION_TIMEOUT`).
- **Second ClientHello cases** (RFC 8446 §4.1.2, RFC 5746):
  - **TLS 1.3 HelloRetryRequest:**
    - The server answers with a ServerHello whose `random` is the fixed SHA-256 of `"HelloRetryRequest"`.
    - The client then sends an optional plaintext ChangeCipherSpec, followed by a second ClientHello in a plaintext handshake record. A client can provoke this by offering no acceptable key share.
    - Early-data records (content type 23) sent with the first flight may precede the second ClientHello; the server skips them.
  - **TLS 1.2 renegotiation:** the new ClientHello is protected by the current session keys and is invisible to a non-decrypting proxy. TLS 1.3 has no renegotiation.
- **Revision strings, current state:**
  - `abi3-seccomp-mux-v1` and required ABI `3` appear in `network/guard.c`, `network/control.py` (manifest writer) and `network/proxy.py` (manifest validator).
  - `tls-clienthello-sni-v1` appears in `tls_client_hello.py`, `control.py` and `session.py`.
- **Unused session file.** `control.py` writes `<session>/resolv.conf`, but nothing mounts or reads it. The wrapper mounts the protected `network/resolv.conf` instead.
- **Silent probe.** `session.py prepare` runs `<guard> --probe` with `stdout=sys.stderr` and an inherited stderr. The guard deliberately calls `_exit(78)` without writing when stderr is not an ordinary descriptor, so the probe fails silently under journald. `qualify.py` already captures through pipes.
- **Test import.** `tests/test_tls_proxy.py` imports `test_tls_client_hello` without adding `tests/` to `sys.path`.

## Goals / Non-Goals

**Goals:**
- Close the HelloRetryRequest SNI switch with the same fail-closed guarantees and bounds as the initial binding.
- Keep the tunnel opaque in every other case, with no per-record inspection after the handshake starts.
- Remove the duplicated revision literals, the dead session file and the silent probe failure without changing the guard binary.

**Non-Goals:**
- No TLS decryption, interception or credential handling. That is N21's separate evaluation.
- No enforcement against TLS 1.2 renegotiation. It is documented instead.
- No TLS 1.3-only requirement for provider tunnels; it would restrict operator-defined profiles.
- No inspection of a third ClientHello. RFC 8446 forbids a second HelloRetryRequest, and the proxy stops inspecting after the retried ClientHello.

## Decisions

**D1 — Decide from the upstream's first handshake message, and hold client bytes until then.**

After the initial ClientHello is forwarded, a retry gate runs both directions until a decision:

- **Upstream direction.** Bytes are fed to a small observer, which reassembles TLS records only until it has the first 4-byte handshake header plus 34 body bytes, that is `legacy_version` and `random`. It then classifies the result:
  - HelloRetryRequest: handshake type 2 and the RFC 8446 random constant;
  - ordinary ServerHello: any other handshake;
  - non-TLS: a non-handshake first record or an alert.

  Upstream bytes are forwarded to the client unchanged after each chunk is classified. The decision is therefore recorded before the client can see a HelloRetryRequest.
- **Client direction.** Bytes are appended, unparsed, to the reserved inspection buffer and not forwarded until the decision. Parsing them before a retry is known would reject harmless trailing bytes that the previous release forwarded, so they are parsed only after a HelloRetryRequest. On "no retry", the buffer is flushed and both directions go to `mux.bridge`. On HelloRetryRequest, the buffered and subsequent client bytes go through a second-hello parser:
  - it accepts any number of ChangeCipherSpec records (type 20, payload `0x01`) and early-data records (type 23) before the handshake;
  - it then requires a complete ClientHello reassembled from type-22 records and validated by the existing `validate(…, expected)`;
  - it forwards the original bytes once and hands off to the bridge.

*Alternative: track client records continuously without upstream knowledge.* Rejected. A TLS 1.2 encrypted Finished is also a type-22 record, so a ClientHello cannot be told apart from ciphertext without knowing what the server negotiated.

*Alternative: reject every HelloRetryRequest.* Rejected. It is simpler, but it breaks legitimate clients whose preferred key share the server does not accept, for example during the hybrid post-quantum key-exchange rollout.

**D2 — Reuse the reservation and deadline.**
- The `STORAGE` reservation taken for the initial inspection is kept until the retry gate ends, so memory stays bounded per tunnel and per session.
- The gate has its own deadline of `INSPECTION_TIMEOUT`, counted from the forwarding of the initial ClientHello. It fails closed when there is neither a decision nor, after a retry, a valid second ClientHello.
- On a stalled upstream, the gate also rejects: a real server answers a ClientHello promptly, and holding client bytes indefinitely would be unbounded.
- The record-count and byte limits of the first parser apply to the held and second-hello input.

**D3 — Generalize the ClientHello parser rather than duplicating it.**
- `ClientHello` gains an option to skip leading CCS and early-data records and to start from already-buffered bytes.
- The validation code and the reason codes stay shared:
  - `tls-identity`, `tls-ech`, `tls-malformed`, `tls-overflow` and `tls-timeout`;
  - one new code, `tls-retry-identity`, which the audit uses to distinguish a mismatch on the retried hello. It is still a fixed string.

**D4 — Enforcement revision `tls-clienthello-sni-v2`.**
- The manifest, the proxy readiness line and `session.py` require the new value, so an old proxy image fails readiness, under the existing "Verified proxy destination-binding revision" requirement.
- The guard revision stays `abi3-seccomp-mux-v1`, because the guard and multiplex protocol are unchanged.

**D5 — Single source in `network/revisions.py`.**
- The module defines `GUARD_REVISION`, `GUARD_REQUIRED_ABI` and `TLS_ENFORCEMENT`. `control.py`, `proxy.py`, `session.py` and `tls_client_hello.py` import it.
- It is added to the proxy image `COPY` line and to the installation file list in `setup/common.py`.
- The C guard keeps its `#define` so that its build stays self-contained and its digest is unchanged. `tests/test_guard.py` parses `GUARD_REVISION` and `GUARD_REQUIRED_ABI` from `guard.c` and compares them, and the built `--version` line, with the module.

*Alternative: generate the C define at build time.* Rejected, because it changes the reproducible guard build and its digest for no behavioral gain.

**D6 — Probe through pipes.**
- `session.py prepare` runs the probe with `stdout=PIPE` and `stderr=PIPE`, and relays its stdout and stderr to the helper's stderr.
- On a nonzero status, it exits with that status and the message `sandbox egress guard probe failed (status N): requires Landlock ABI >= 3 and ordinary standard I/O; rerun from a terminal or see network/README.md`.
- The guard's own descriptor rule is unchanged.

**D3a — Record boundary and buffer reuse.**
- An initial or retried ClientHello must end at a TLS record boundary. Further handshake bytes in the same record would be forwarded uninspected, so they are rejected as `tls-malformed`.
- Bytes in later records are surplus: they are held, not forwarded with the ClientHello.
- The retried parse reuses the same fixed buffers (`ClientHello.next_hello`), so the per-tunnel reservation is unchanged.
- `mux.Stream.readable()` waits without consuming data. The gate can therefore cancel the wait when the upstream decides, without losing client bytes.

**D7 — Delete the session `resolv.conf` write.** A test asserts that the prepared session directory no longer contains it.

## Risks / Trade-offs

- **Gate latency.** Client bytes sent with the first flight, such as early data, wait for the server's first response. TLS servers answer a ClientHello immediately, so the extra latency is at most one network round trip, and only for clients that send before receiving.
- **Unusual servers.** A legitimate server that sends nothing for more than 10 s after a ClientHello will now fail.
  - Mitigation: the reason `tls-timeout` is recorded; bundled profiles target responsive provider endpoints.
- **Coalesced early data before the second ClientHello.** These records are forwarded opaque.
  - Mitigation: they are encrypted under keys the server discards after a HelloRetryRequest. A plaintext ClientHello cannot hide in them, because the server would fail to decrypt them and skip them.
- **Renegotiation stays uninspected.**
  - Mitigation: clear documentation. TLS 1.3 removes renegotiation; common provider frontends refuse client-initiated renegotiation. The residual-exfiltration review continues in N21.
- **Requalification burden on revision bump.**
  - Mitigation: readiness failure is explicit, and setup guidance already explains rerunning `--container-setup`.

## Migration Plan

1. Land the code with the updated tests.
2. Rerun `./claude-container.sh --container-setup`. This rebuilds the immutable proxy image, installs the protected files and requalifies.
3. Old proxy images fail readiness with the revision mismatch until then.
4. **Rollback:** check out the previous commit and rerun setup. Both installation and proxy image must come from the same commit.

## Open Questions

- Real-service evidence: whether the Anthropic endpoints ever send a HelloRetryRequest to the installed Claude Code client. This is recorded as observed or unavailable in `docs/validation.md`; controlled fixtures provide the acceptance evidence either way.
