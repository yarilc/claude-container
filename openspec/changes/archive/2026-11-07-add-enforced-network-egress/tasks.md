# Tasks

All tasks are implementation or acceptance work; preparing these artifacts does not complete any N01–N14 item. References identify the source TODO coverage. Work in sibling repositories is outside this checklist; deliver a parity contract and record their pending adoption here.

Design revised on 2026-11-06: the exact Linux 6.6.87.2-microsoft-standard-WSL2
x86_64 / Landlock ABI-3 environment is the mandatory initial support target.
Replace the ABI-9 prototype with ABI-3 filesystem confinement plus an additive
in-process seccomp filter, preserving the standard OCI profile and SELinux.
Provider mode requires one verified preconnected multiplexed data channel.
New Unix listeners and unconnected Unix sockets are denied even in private tmpfs; connected
stream/seqpacket pairs and own loopback remain supported. No kernel upgrade is
required. The credential-free WSL gate has passed; mandatory per-session checks
replace the hold. See docs/validation.md for actual results and remaining real
acceptance evidence. Account login/reuse/refresh passed in the observed
HTTPS/SSE flow; real-key API acceptance is optional/unavailable. No untested flow
is declared verified.

The prior checklist had 14/38 completed component tasks. Reopen 1.1, 1.5, 3.1
and 3.6 for the changed contract, guard, artifact and protocol documentation;
add 3.7–3.8 for multiplexing. Other component evidence retains only its original
scope. The primitive ABI-3 probe is feasibility evidence, not full acceptance.
Task IDs remain stable; 1.4 depends on 1.5–1.8 and the multiplexed transport.

## 1. Rootless feasibility gate and common contract

- [x] 1.1 (N01, N02, N12) Revise the portable contract/parity checklist for the required WSL 6.6.87.2 x86_64 ABI-3 target, additive seccomp, preconnected multiplexing and denied named/abstract Unix IPC; document preserved OCI policy, no upgrade requirement and pending validation.
- [x] 1.2 (N02, N05, N11) Add a disposable rootless feasibility harness for an agent with `--network=none`, loopback relay, and external Unix-socket proxy; verify a controlled HTTPS request succeeds through the proxy while direct IPv4/IPv6, host aliases/gateway, external DNS, and UDP fail, without additional privileges or relabeling.
- [x] 1.3 (N02, N04, N11) Exercise read-only socket-directory binds, mapped caller permissions, standard SELinux/seccomp, concurrent sockets, and identical host bind paths through local and same-host Unix launch contexts; record passed/failed/unavailable results and client/server/Netavark versions in `docs/validation.md`.
- [x] 1.5 (N02, N04) Replace the ABI-9 prototype with a protected static bootstrap implementing ABI-3 MAKE_SOCK/REFER rules, no_new_privs, descriptor hygiene, verified provider preconnection and additive x86_64 seccomp; verify rejection of missing rules/filter, ABI below 3, compat/x32 calls, unsafe FDs and pre-policy loader hooks. Record reproducible guard/filter identity.
- [x] 1.6 (N02, N05, N11) On the exact measured WSL ABI-3 target, reproduce the unguarded IPC positive control and prove guarded denial for existing/late pathname/abstract sockets in every shared/isolated/worktree bind and alias, stream/datagram/seqpacket and explicit-recipient sends; verify only the preconnected policy-filtered provider channel survives.
- [x] 1.7 (N02, N05, N11) Test socket/socketpair family/type/flag and argument-truncation cases, compat/x32 syscalls, inherited/SCM_RIGHTS descriptors, io_uring setup/enter/register, pidfd_getfd, inheritance and attempted guard removal; prove VSOCK/other non-IP socket denial with controlled positive controls under standard OCI policy.
- [x] 1.8 (N02, N04, N11) Prove stream/seqpacket pairs cannot retarget through reconnect, AF_UNSPEC, explicit sendto/sendmsg, shutdown, bind/autobind, listen or FD transfer; deny datagram/raw pairs and named listeners even on tmpfs. Verify MAKE_SOCK/REFER placement restrictions, reserved-path overlap, ordinary Git/worktree persistence and permitted pipes/pairs/loopback.
- [x] 1.4 (N02, N04, N12) After the native guard, multiplex transport and complete real-rootless gates pass on WSL 6.6.87.2 x86_64 ABI 3, publish the support matrix and replace the blanket hold with mandatory per-session checks; distinguish incomplete implementation from incompatible kernel features and never demand ABI 9 or an upgrade for this target.

## 2. Operator controls and protected policies

- [x] 2.1 (N01, N07) Parse network mode and provider-profile selection before image operations, preserving side-effect-free help; add synthetic checks for unset/empty/invalid modes, missing profiles, and exact delegation opt-in rejection across state/shell/YOLO/build/worktree combinations.
- [x] 2.2 (N01, N04) Add the strict versioned JSON policy schema and example API/account policies with revision, source date, required hosts, feature controls, and tested-version metadata; verify malformed/unknown fields, duplicate hosts, wildcards, unsafe ports, and incomplete profiles fail validation.
- [x] 2.3 (N02, N04) Extend trusted path and bind validation to the immutable native bootstrap/hash, effective mount targets, and reserved private IPC roots; verify synthetic fixtures reject writable code, escaped aliases, unsafe ancestors, / or parent overlap, and host binds nested in or replacing /tmp, /run or /var/tmp.
- [x] 2.4 (N04, N08) Preserve validated immutable policy snapshots and add protected bootstrap/ruleset identity to the session manifest; verify source changes cannot alter active policy, no agent mount exposes configuration/logs/setup descriptors, and readiness binds policy plus bootstrap identities to that session.
- [x] 2.5 (N01, N04, N12) Document variables, protected assets, ABI-3/additive-filter prerequisites, preconnected multiplexing, named IPC limitations and operator-only extensions; verify WSL examples and pending validation status match actual preflight without upgrade guidance.

## 3. Trusted destination proxy

- [x] 3.1 (N03, N04) Repackage/pin the proxy artifact for the versioned multiplex protocol, with read-only runtime, Unix-only frontend and bounded streams/frames/queues; verify no Podman socket, agent state/workspace, administration listener, host networking or descriptor-transfer protocol.
- [x] 3.2 (N03) Implement exact normalized CONNECT authority/port validation; add tests for approved hosts, case/terminal-dot rules, deceptive suffixes, literals, userinfo, malformed/encoded/non-ASCII authorities, forbidden methods, excessive headers, and wildcard requests.
- [x] 3.3 (N05) Resolve only authorized names, reject unsafe/mixed IPv4/IPv6 answers and mapped/special addresses, and connect to validated numeric addresses; verify deterministic DNS fixtures cover CNAME results, rebinding, private/loopback/link-local/metadata ranges, multiple answers, and no second unchecked lookup.
- [x] 3.4 (N05) Implement explicit local-exception validation with exact destination/address scope and port, disabled in bundled profiles; verify test-only narrow exceptions cannot authorize adjacent hosts, alternate ports, or unrelated private ranges.
- [x] 3.5 (N10) Add bounded sanitized denial records and private log retention with distinct policy/DNS/readiness reasons; verify userinfo, tokens, control characters, headers, prompts, and bodies cannot appear in logs or inject records.
- [x] 3.6 (N03, N10, N12) Document the multiplex protocol, handshake, state transitions, limits/flow control, channel death semantics, address handling and redacted diagnostics; preserve CONNECT/domain-fronting/shared-service limitations and verify examples against parser tests.

- [x] 3.7 (N03, N06) Implement the versioned single-channel proxy/relay multiplex transport with monotonic IDs, independent per-OPEN authorization, cancellation/half-close and bounded credits: 64 active streams, 16 KiB DATA, 8 KiB OPEN, 256 KiB per-stream and 16 MiB session queues; verify more than 64 sequential tunnels without reconnecting or unconfined helpers.
- [x] 3.8 (N03, N10, N11) Add codec/state/overflow/credit fuzz and negative tests, cross-stream isolation/fairness/backpressure tests, abrupt channel death and repeated TLS/streaming/WebSocket checks; prove malformed frames cannot expose secrets, allocate unbounded resources, change policy or transfer host descriptors.

## 4. Wrapper networking, relay, and lifecycle

- [x] 4.1 (N02, N06) After the complete WSL gate passes, integrate the static Landlock/seccomp bootstrap for every restricted Claude/shell invocation with network=none and private PID/IPC namespaces; hand the sole provider data FD to the confined multiplex relay and close it in the application branch. Verify no early hooks, argv/stdin/TTY/signals/status and both state modes.
- [x] 4.2 (N05, N06) Normalize proxy/bypass/image defaults, non-forwarding DNS and private tmpfs XDG_RUNTIME_DIR without moving HOME/configuration; verify hostile/removed variables cannot bypass restrictions, named services remain denied everywhere and permitted pairs/pipes/loopback work.
- [x] 4.3 (N07) Revalidate host launch-endpoint retention and exact restricted delegation rejection through every bootstrap/shell/native-permission/state combination; verify disabled delegation ignores invalid overrides and unrestricted endpoint precedence/remapping remains unchanged.
- [x] 4.4 (N08) Extend/revalidate atomic owned lifecycle and interrupted-create recovery for bootstrap readiness/setup channels as well as existing proxy/agent resources; inject descriptor, rule-installation and pre-exec failures plus interruption at each resource boundary and verify only owned resources are removed.
- [x] 4.5 (N08, N10) Share the existing 20-second shutdown budget across all resources; verify stalled engine calls, repeated signals, ignored signals, exit 0/nonzero/125, and interrupted setup preserve primary status, bounded completion, and actionable remaining-resource identities.
- [x] 4.6 (N08, N11) Add/re-run real-rootless tests with the bootstrap for distinct concurrent domains sharing file state, proxy death, interrupted setup and foreign resources; verify no cross-session Unix access, no fallback, preconnected channel lifecycle and owned cleanup after each case.
- [x] 4.7 (N02, N06, N08, N12) Update README/help/AGENTS.md and validation records for WSL ABI 3, additive seccomp, preconnected FD/multiplexing, named Unix IPC limitations, failure closure and lifecycle; run credential-free examples on the target and label remaining evidence gaps.

## 5. Maintenance and runtime dependencies

- [x] 5.1 (N01, N09) Require exact maintenance authorization for implicit absent-image builds, explicit refresh, and proxy-image acquisition; verify preflight failures precede builds, inspection errors retain status, and runtime unrestricted mode alone never authorizes maintenance.
- [x] 5.2 (N04, N06, N09) Compile/package the revised static ABI-3 bootstrap and additive x86_64 filter with pinned inputs and immutable identities, plus multiplex relay assets; verify reproducibility, no pre-policy dynamic loading, build-context allowlists and exclusion of credentials/state/unrelated files.
- [x] 5.3 (N09, N12) Document and test maintenance examples, image-pull/build RUN boundaries, prebuilt-image usage, and provider-mode denial of Git/package/web/MCP access; verify running agents receive no maintenance authority or broad registry exceptions.

## 6. Claude profiles and compatibility

- [x] 6.1 (N04, N13) Query the selected image's Claude/Node versions and create a dated official-source endpoint inventory for `anthropic-api` and `anthropic-account`; verify exact profile hosts, required OAuth exchange/refresh hosts, optional SSO separation, and no implicit cloud/gateway/CDN expansion.
- [x] 6.2 (N06, N14) Apply and verify installed-version-supported optional-traffic controls through the bootstrap and review documented runtime/socket settings; verify unsupported controls do not broaden policy and re-enabled features or external supervisor/cache paths remain denied.
- [x] 6.3 (N06, N14) Re-run credential-free TLS, sustained/long-lived streaming, WebSocket and CA fixtures through the guarded relay; verify certificate failures remain failures and both CA modes preserve the exact existing single-file mount and four-variable contract.
- [x] 6.5 (N11, N13, N14) Run separately authorized account login and token-refresh checks, documenting external-browser versus container steps, loopback callback behavior, long-lived streaming and supported WebSockets; retain unavailable/unsupported status for any unverified flow without adding host networking or automatic exceptions.
- [x] 6.6 (N02, N06, N14) Verify actual Claude tool spawning, shell/native permissions and ordinary state/Git persistence under both layers in both state modes; test permitted socket pairs/pipes/loopback and record named Unix daemon/cache/internal-sandbox incompatibilities separately from authenticated readiness.


Manual acceptance completed (2026-11-07): operator-reported checks passed for
existing account credentials (ACCOUNT_PROFILE_OK), a fresh isolated login
(Login successful), new-session credential reuse (ACCOUNT_LOGIN_OK), and
post-expiry automatic refresh (ACCOUNT_REFRESH_OK); all reported wrapper exit 0.
The token was already expired at the pre-request check (clock 10:53:14.601241 UTC,
expiry 09:16:05.307000 UTC), and persisted expiry advanced to 18:54:31.676000 UTC.
Claude version was 2.1.316; the first response identified claude-sonnet-5-5.

Task 6.5 records the observed HTTPS/SSE login/reuse/refresh flow as passed. Host
browser work remains outside the boundary; the exact callback/pasted-code
mechanism was not independently observed. Long-lived/large-payload/WebSocket
transport is covered by controlled production guard/proxy fixtures rather than
claimed as a real authenticated account-WebSocket test. Unexercised mechanisms
remain unverified as required by the task. See docs/validation.md for scoped,
redacted evidence; no credential contents enter fixtures or this checklist.

Real-key API check 6.4 remains optional/unavailable by operator decision on
2026-11-07. It is excluded from mandatory task counting, not marked passed.

## 7. Integrated acceptance

- [x] 7.1 (N11) Run the complete controlled IP/IPC bypass matrix on the supported platform: existing/late Unix services in every writable bind, aliases/replacement, stream/datagram/seqpacket and explicit-address sends, socket publication, abstract endpoints, socketpair retargeting, compat/x32 syscalls, inherited/SCM_RIGHTS/async-I/O descriptors, descendant enforcement, alternate host transports, original DNS/UDP/IPv6/direct-host cases, concurrency, proxy death and cleanup; preserve positive controls and versioned results.
- [x] 7.2 (N11, N12) Run `python3 -m unittest discover -s tests -p test_wrapper.py -v`, changed-shell `bash -n`, the expanded rootless runtime runner, and `git diff --check`; verify existing state/privacy, worktree, CA, engine, invocation, signal, and unrestricted delegation regressions remain passing.
- [x] 7.3 (N12) Review README/help/AGENTS.md, specs, endpoint/bootstrap/filter/protocol inventories, parity checklist and validation records against N01–N14; run strict OpenSpec validation and verify required WSL ABI-3 support, named Unix IPC limitations, maintenance/remote-tool/allowed-service limits and authenticated/sibling gaps are explicit.

## Optional manual verification (not counted in mandatory tasks)

**6.4 (N11, N13, N14) — Real-key API authentication and streaming.** Run only
when a real API key is available and the operator authorizes the check. Record
CLI version, policy revision, expected output and actual result without putting
real credentials or model calls in automated fixtures. Current result:
**unavailable — no key available; non-blocking by operator decision on
2026-11-07**. API-key forwarding, exact API-profile policy and synthetic real-CLI
integration remain implemented/tested. This does not claim a passed real-key
request. The original ID is retained for traceability; there are 39 mandatory
tasks, all complete after the recorded account acceptance; this optional
real-key check remains unavailable and is not a passed provider test.

## Workflow follow-up

- Mandatory implementation and acceptance are complete (39/39). Review the recorded evidence and limitations before specification synchronization/archive; optional real-key API check 6.4 remains unavailable and non-blocking.
- Synchronize specifications and archive only through the corresponding OpenSpec workflow after implementation and acceptance; keep unavailable authenticated checks visible rather than marking them passed.
- Coordinate sibling-wrapper adoption separately using the published parity contract; this repository does not implement or validate their rollout.
