# Design

## Context

See proposal.md (Why). Observed on the lab host: `ipv6.disable=1` on the
kernel command line, no `/proc/sys/net/ipv6`, and
`socket(AF_INET6)` raising `OSError: [Errno 97]` (`EAFNOSUPPORT`). Landlock
ABI 6 is active.

Code that assumes IPv6 today:

- `network/qualify.py` `Gate.qualify`:
  - creates `network create --internal --ipv6`;
  - requires both `IPAddress` and `GlobalIPv6Address` from the peer;
  - passes both addresses to every case.
- `network/qualification_peer.py` binds TCP/UDP servers on `0.0.0.0` and
  `::`.
- `network/control.py` (`qualification-input`) accepts only
  `addresses == [IPv4, IPv6]`.
- `network/qualification_probe.py` `external()` connects to, or expects
  denial from, every address.
- `network/qualification_runtime.py` creates `socket(AF_INET6)` outside its
  `try` block, so it would crash rather than prove "no route".
- `network/proxy.py` `connect()` creates `socket(family, …)` outside its
  `try` block. An AAAA answer aborts the tunnel on an IPv6-less kernel,
  instead of falling through to the A records.
- `network/qualification_records.py` `fingerprint()` already runs a
  server-side `--network=none` probe container for boot id, seccomp,
  Netavark and CA digests.

Agent sessions use `--network=none`. The guard's seccomp filter allows
`AF_INET6` sockets (`guard_seccomp.h`), so the kernel itself returns
`EAFNOSUPPORT` under the guard.

## Goals / Non-Goals

**Goals:**
- Qualify and run offline and provider modes on IPv6-less kernels without
  weakening any IPv4, DNS/UDP, Unix, syscall, hardening or TLS check.
- Keep the IPv6-present path byte-for-byte equivalent in behavior.

**Non-Goals:**
- Kernels with IPv6 compiled in but disabled per interface through the
  `disable_ipv6` sysctl. These are "present" and keep today's dual-stack
  path. If Netavark fails there, qualification still fails closed.
- Platform eligibility changes (Landlock, Podman version and backend rules
  are unchanged).
- Propagation to the sibling wrappers (a follow-up).

## Decisions

### Detect the IPv6 state on the engine host, inside the identity probe

Extend the existing `security_probe` in `fingerprint()` with an `ipv6` field:

- **present**: `/proc/sys/net/ipv6` exists and `socket(AF_INET6)` succeeds.
- **absent**: `/proc/sys/net/ipv6` is missing and `socket(AF_INET6)` raises
  `EAFNOSUPPORT`.
- Any other combination or errno raises "unverifiable security identity".

The probe runs on the engine host's kernel, which also matters when the
client itself is containerized. `--network=none` still has its own netns
sysctl tree when IPv6 exists.

- Alternative: read `/proc/cmdline` or the client's `/proc`. Rejected. The
  command line is indirect, and the client may run in a different
  environment from the engine.

### Bind the state into the identity

`security.ipv6` becomes part of the identity, so `validate_report` and the
staleness checks compare it like the boot id. Changing `ipv6.disable`
requires a reboot, which already changes the boot id. The explicit field
makes the evidence path auditable in the report.

Old reports lack the field and are stale. The code digests change anyway, so
`REVISION` stays `local-enforcement-v1`. The checks list keeps `ip6`, and its
evidence kind follows from `security.ipv6`.

### IPv4-only fixtures when absent

`Gate.qualify(identity)`:

- **present**: unchanged (`--ipv6` network, both addresses required).
- **absent**:
  - create the network without `--ipv6`;
  - run the peer as `peer.py ipv4`, which binds only `AF_INET`;
  - require a non-empty `IPAddress` and an empty `GlobalIPv6Address`;
  - pass `addresses = [ipv4]`.

The peer takes a fixed argument, `dual` or `ipv4`. Anything else exits with
an error.

### Explicit fixed-input field

The qualification input gains `ipv6: bool`. `control.py` requires
`addresses` to be exactly `[v4, v6]` when it is true and `[v4]` when it is
false. Deriving the state from the list length was rejected, because an
explicit field makes a truncated list an error instead of a mode switch.

### Kernel-rejection evidence in control and guarded probe

When `config['ipv6']` is false, both `qualification_probe.py control`
(unconfined) and `probe` (under the guard) assert that `socket(AF_INET6, …)`
for `SOCK_STREAM` and `SOCK_DGRAM` raises `EAFNOSUPPORT`.
`qualification_runtime.py` accepts `EAFNOSUPPORT` on `AF_INET6` creation as
"no direct route" only when `config['ipv6']` is false. When IPv6 is present,
the same error fails the check.

This is the "explicit enforcing syscall rejection" the requirement already
permits. The kernel, not the guard, enforces it. That is stronger than a
guard denial, because no IPv6 stack exists for any process.

### Proxy skips unsupported families

In `Proxy.connect`, move `socket.socket(family, kind, proto)` inside the
existing `try`, so that an `OSError` on creation, such as `EAFNOSUPPORT`,
closes nothing and continues with the next validated address. Addresses are
still the single validated `resolve()` result. Nothing is re-resolved. If no
address connects, the tunnel is rejected as `upstream-unavailable`, as
today.

## Risks / Trade-offs

- [The IPv6 positive control is replaced by absence evidence] This weakens
  nothing: with no IPv6 stack, no IPv6 egress is possible for the agent, the
  proxy or anything else. The gate still proves that absence under the
  production guard.
- [Misdetection, such as a seccomp profile returning `EAFNOSUPPORT`]
  "Absent" also requires a missing `/proc/sys/net/ipv6`, and the guarded
  probe must agree. Any contradiction fails closed.
- [Shared code drift] The sibling wrappers keep the old code until
  propagation. They fail on such hosts exactly as today. That is safe but
  unhelpful.
- [Unverified on a real IPv6-less engine here] The maintainer's WSL host
  has IPv6. Unit tests cover both paths, and the lab host provides the real
  acceptance, recorded as operator-reported.

## Migration Plan

1. Land the change. Rerun `--container-setup` on every restricted
   installation, because the existing reports become stale.
2. Rollback: revert and rerun setup. IPv6-less hosts then fail qualification
   as before.

## Open Questions

- Whether the provider proxy container, which uses the engine's default
  rootless network, has further IPv6 assumptions on such hosts. This can only
  be observed on the lab host and does not change the plan. A failure there
  would surface in the provider qualification cases.
