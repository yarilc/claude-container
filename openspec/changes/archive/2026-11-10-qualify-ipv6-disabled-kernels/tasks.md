# Tasks

## 1. IPv6 state in the qualification identity

- [x] 1.1 Extend the `security_probe` in
  `network/qualification_records.py` `fingerprint()` with
  `ipv6: present|absent`:
  - **present**: `/proc/sys/net/ipv6` exists and `AF_INET6` creation
    succeeds;
  - **absent**: the directory is missing and creation raises
    `EAFNOSUPPORT`;
  - otherwise raise "unverifiable security identity".

  Validate the field together with the other security fields. Verify with
  new `tests/test_qualification.py` cases: both states are accepted, a
  mismatched or missing field is rejected, and a report for one state is
  stale for the other.

## 2. Gate fixtures and fixed input

- [x] 2.1 Add a fixed `dual|ipv4` argument to
  `network/qualification_peer.py` (`ipv4` binds only `AF_INET`; any other
  value exits with an error). In `network/qualify.py` `Gate.qualify`, create
  the network with `--ipv6` only when `security.ipv6` is present. Require
  both peer addresses when present, and an IPv4 address with an empty
  `GlobalIPv6Address` when absent. Pass `ipv6` and the matching
  `addresses` into each case's input. Verify with
  `tests/test_qualification.py` cases using a mocked engine: the network
  arguments, the peer argument, the address lists, and a failure on
  contradictory inspect output.
- [x] 2.2 Extend the fixed-input validation in `network/control.py`: the
  `ipv6` boolean is required, and `addresses` must be exactly `[v4, v6]`
  when true and `[v4]` when false. Verify with tests that accept both
  shapes and reject a missing field, a mismatched list or a reversed order.

## 3. Probe evidence

- [x] 3.1 In `network/qualification_probe.py`, when `config['ipv6']` is
  false, assert `EAFNOSUPPORT` for `AF_INET6` stream and datagram socket
  creation in both `control` and `probe`. In
  `network/qualification_runtime.py`, accept `EAFNOSUPPORT` on `AF_INET6`
  creation as "no direct route" only when `config['ipv6']` is false, and
  fail otherwise. Verify with `python3 -m py_compile` and with a
  unit-level execution of the assertion helpers that patches
  `socket.socket` to raise `EAFNOSUPPORT`, covering the accepted (absent)
  and rejected (present) cases.

## 4. Provider proxy

- [x] 4.1 In `network/proxy.py` `connect()`, create each upstream socket
  inside the `try` block, so that an `OSError` on creation continues to the
  next validated address. Verify with a new test (in
  `tests/test_tls_proxy.py` or `tests/test_network_policy.py`):
  `resolve()` returns IPv6 and then IPv4 public addresses, `AF_INET6`
  creation raises `EAFNOSUPPORT`, the IPv4 connection succeeds with no
  second resolution, and an IPv6-only answer is rejected as
  `upstream-unavailable`.

## 5. Documentation and regression

- [x] 5.1 Document the IPv6-absent qualification path in
  `network/README.md` (qualification gate) and `docs/network-contract.md`:
  the evidence is kernel rejection, the state is bound into the report, and
  the `disable_ipv6` sysctl is out of scope. Verify with `git diff --check`.
- [x] 5.2 Run the credential-free suites `test_qualification.py`,
  `test_network_policy.py`, `test_tls_proxy.py`, `test_alignment.py`,
  `test_setup.py` and `test_wrapper.py`, comparing against `main` with the
  same runner. Verify that there are no new failures and record any
  environment-only ones.
- [x] 5.3 On this IPv6-capable WSL host, run
  `bash tests/run-runtime.sh --qualification`, or the narrowest available
  runtime qualification, to confirm that the dual-stack path is unchanged.
  Verify that it passes, or record it as unavailable with the reason.
- [x] 5.4 On the IPv6-less lab host, have the operator rerun
  `--container-setup` (provider, refresh). Verify that qualification passes
  and the setup reports `Sandbox: ready`, or record the failure. Then add a
  dated `docs/validation.md` entry with all results, and close the pending
  4.2 and 4.3 of `https-image-package-sources`.

## Workflow follow-up

- Propagate the changed shared files to the Codex, Antigravity, OpenCode and
  Pi wrappers.
- Sync the `network-egress` delta and archive after review.
