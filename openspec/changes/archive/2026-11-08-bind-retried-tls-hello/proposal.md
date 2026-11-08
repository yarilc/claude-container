# Proposal

## Why

The trusted proxy binds only the first ClientHello of each provider tunnel to the authorized CONNECT hostname. A client can force a TLS 1.3 HelloRetryRequest (for example, by sending an unsupported key share) and then send a plaintext second ClientHello with a different SNI, which a permissive shared frontend may honor. This reopens the shared-address mismatch that N16 closed (N22). The same review also found small inconsistencies (N24): an unused session file, enforcement revision strings duplicated across components, a host probe that fails silently, and a test module that only imports under one runner layout. These should be fixed before the reference tag `sandbox-ref-2`.

## What Changes

- The proxy observes the upstream's first handshake message. When it is a TLS 1.3 HelloRetryRequest, the second ClientHello is reassembled, validated with the same rules as the first, and must name the same authorized host before it is forwarded. Client bytes sent after the first ClientHello are held, within the existing inspection bounds, until the proxy knows whether a retry occurred.
- If the upstream does not send a HelloRetryRequest, the tunnel switches to the existing opaque bridge without further inspection.
- TLS 1.2 renegotiation, whose ClientHello is encrypted under the established session, is documented as an accepted limitation in the contract, help and security documentation. It is not inspected and not decrypted.
- **BREAKING (operator deployment):** the destination-binding enforcement revision changes from `tls-clienthello-sni-v1` to `tls-clienthello-sni-v2`. Existing installations and proxy images fail readiness until setup is rerun and the installation is requalified. No unchecked fallback is added.
- The guard revision, the required Landlock ABI and the TLS enforcement revision are defined once in a shared Python module used by control, session and proxy code. A test checks that the C guard's `GUARD_REVISION` and its `--version` output match.
- The control helper no longer writes the unused per-session `resolv.conf`. The wrapper keeps mounting the protected `network/resolv.conf`.
- The host-side guard probe in session preparation runs with piped standard I/O, as qualification already does, so a socket on the caller's stdout or stderr (for example journald) no longer makes the probe exit 78 silently. A failed probe reports an actionable message.
- `tests/test_tls_proxy.py` imports its helpers independently of the test runner's start directory.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `network-egress`:
  - Adds binding of a retried TLS 1.3 ClientHello.
  - Adds a single source for the enforcement revisions.
  - Adds actionable host probe diagnostics.
  - Updates the provider identity documentation requirement to name TLS 1.2 renegotiation as an accepted limitation.

## Impact

- **Code:**
  - `network/proxy.py`: retry gate between the initial inspection and the bridge.
  - `network/tls_client_hello.py`: a reusable ClientHello parser and a ServerHello/HelloRetryRequest observer.
  - New `network/revisions.py`.
  - `network/control.py` and `network/session.py`.
  - `network/Containerfile`: the proxy image copies `revisions.py`.
  - `setup/common.py`: the installation file list.
- **Tests:**
  - `tests/test_tls_client_hello.py`, `tests/test_tls_proxy.py`, `tests/test_guard.py` and `tests/test_session.py`.
  - The alignment and setup file lists.
- **Docs:** `docs/network-contract.md`, `network/README.md`, `README.md` and the help limitations text, plus a new section in `docs/validation.md`.
- **Operators:**
  - Rerun `--container-setup` to rebuild the proxy image and requalify.
  - The guard binary and its digest do not change.
- **Sibling wrappers:** `network/` and `setup/` are copied unchanged in Wave 3, so the behavior propagates with them.
