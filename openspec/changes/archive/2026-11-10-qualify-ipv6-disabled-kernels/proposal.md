# Proposal

## Why

Restricted modes (offline and provider) cannot be qualified on hosts whose
kernel boots with `ipv6.disable=1`, a setting operators often cannot change.
On the Rocky 9 lab host (kernel 5.14.0-687.12.1.el9_8, Landlock ABI 6,
Podman 5.8, rootless Netavark), setup builds every image and the guard, and
then qualification stops at
`network create --internal --ipv6` with "netavark: set sysctl
net/ipv6/conf/podman1/forwarding: No such file or directory".

Everything else on that host meets the restricted-platform rules. Without
IPv6, there is simply no IPv6 path to deny: the kernel rejects `AF_INET6`
sockets with `EAFNOSUPPORT`.

## What Changes

- Qualification detects the host's IPv6 state from the engine side:
  - **present**: IPv6 is available;
  - **absent**: there is no `/proc/sys/net/ipv6`, and `AF_INET6` socket
    creation fails with `EAFNOSUPPORT`;
  - anything else fails closed.

  The state is bound into the qualification identity, so a reboot that
  enables IPv6 makes the report stale. The boot id already changes, and the
  explicit field documents why.
- With IPv6 absent:
  - the positive-control network is IPv4-only (no `--ipv6`);
  - the peer listens on IPv4 only;
  - the fixed qualification input carries one IPv4 address.

  The `ip6` check is satisfied by explicit kernel rejection: `AF_INET6`
  socket creation fails with `EAFNOSUPPORT` in both the unconfined control
  and the guarded probe. This is enforcing-rejection evidence, not a skipped
  check. All IPv4, DNS/UDP, Unix, syscall and provider checks are unchanged.
- With IPv6 present, behavior is unchanged: dual-stack positive controls and
  two addresses.
- The guarded runtime assertions (`qualification_runtime.py`) treat an
  `EAFNOSUPPORT` from `AF_INET6` socket creation as "no direct route",
  instead of crashing on it.
- The provider proxy skips a resolved upstream address whose family the
  kernel does not support and tries the next one. Today the
  `socket(AF_INET6)` call sits outside the `try` block, so an AAAA record
  aborts the connection on an IPv6-less kernel.
- No fallback: a mismatch between the detected state and the observed
  network, fixture or probe evidence fails qualification.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `network-egress`: local enforcement qualification gains an explicit
  IPv6-absent host path (kernel rejection replaces the IPv6 positive
  control, and the state is bound into the qualification identity). Provider
  upstream connection tolerates address families the kernel does not
  support.

## Impact

- Shared code, copied unchanged to the Codex, Antigravity, OpenCode and Pi
  wrappers:
  - `network/qualify.py`, `network/qualification_peer.py`,
    `network/qualification_probe.py`, `network/qualification_runtime.py` and
    `network/qualification_records.py` (the identity field);
  - `network/control.py` (validation of the fixed input);
  - `network/proxy.py`.
- Tests: `tests/test_qualification.py`, `tests/test_network_policy.py` or
  `tests/test_tls_proxy.py` (proxy family fallback), and the fixed-input
  validation tests.
- Docs: `network/README.md` (qualification gate), `docs/network-contract.md`
  and `docs/validation.md`.
- Existing qualification reports become stale, because the identity gains a
  field and the code digests change. Restricted installations rerun setup or
  qualification.
- The sibling wrappers must receive the same shared files in follow-up
  propagation.
