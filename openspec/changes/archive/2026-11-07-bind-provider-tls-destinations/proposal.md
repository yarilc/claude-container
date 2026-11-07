# Proposal

## Why

The current provider proxy authorizes a CONNECT hostname and its resolved address but forwards arbitrary tunnel bytes, including a TLS ClientHello naming another service on a shared endpoint. The 2026-11-07 follow-up therefore requires a stronger, testable destination boundary without claiming application-level isolation.

## What Changes

- Resolve N15 by specifying separately CONNECT authority/address authorization, initial TLS server-name binding, and the remaining encrypted HTTP/shared-service limits; update provider help and setup guidance accordingly.
- **BREAKING**: Resolve N16 by requiring a bounded, structurally valid TLS 1.2/1.3 initial ClientHello with exactly one unambiguous policy-matching SNI before the trusted proxy forwards any client bytes upstream. Reject non-TLS, absent/mismatched SNI, malformed or unsupported negotiation, ECH (including GREASE ECH), timeouts, and inspection overflow without unchecked fallback.
- Keep certificate verification end-to-end, preserve the existing CA integration and multiplex resource limits, and enforce inspection outside agent control even when the relay is bypassed.
- Resolve N17 with controlled shared-address TLS regression fixtures through the production guard, relay and proxy, including positive controls, fragmentation, concurrency, failures, and both authentication profiles.
- Version and verify the proxy's destination-binding enforcement identity so an old immutable proxy image cannot silently satisfy the new startup contract.
- Record the historical observation and measured acceptance results in tracked validation documentation. Treat N15–N17 as incomplete until their corresponding evidence exists.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `network-egress`: Add mandatory initial TLS server-name binding and destination-binding acceptance evidence; revise exact destination enforcement, transport readiness, diagnostics, and documentation guarantees.

## Impact

Affected areas include `network/proxy.py`, a focused ClientHello parser, `network/Containerfile`, protected session manifests/readiness validation in `network/control.py` and `claude-container.sh`, setup packaging/smoke checks, and network/guard/runtime tests. The multiplex wire format can remain v1; the enforcement revision must be separately checked. Documentation updates cover README, network documentation, provider help, setup guidance, AGENTS.md, and `docs/validation.md`.

Policies retain their exact host/port inventories. Existing clients using ECH or raw tunnels become incompatible; compatibility failures must be diagnosed rather than expanding policy. N01 sibling rollout, TLS interception, encrypted HTTP Host enforcement, remote provider tools, real-key API acceptance, and new platform support are outside this change. Real authenticated checks remain separately authorized; routine acceptance uses synthetic state and controlled endpoints.
