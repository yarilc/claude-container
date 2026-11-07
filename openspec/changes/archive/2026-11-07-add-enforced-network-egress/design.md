# Design

## Context

See `proposal.md` for motivation. Partial implementation supplies policy validation, snapshots, a separate CONNECT proxy, a loopback relay, and owned cleanup. The candidate passed IP/TLS checks but failed the filesystem Unix-socket probe recorded in `docs/validation.md`: an offline agent reached a controlled external service through a socket in its writable workspace. Restricted startup was held closed when this design was revised. Implementation on 2026-11-07 replaced the hold with mandatory checks after the credential-free WSL gate; current results and authenticated gaps are recorded in docs/validation.md.

The measured environment is Linux 6.6.87.2-microsoft-standard-WSL2, Podman client 4.3.1/server 4.9.3, rootless Netavark, standard seccomp enabled, and SELinux disabled. The image reports Claude 2.1.316, Node 22.23.4, and Python 3.11.2. A read-only ABI query on 2026-11-06 returned Landlock ABI 3 both in the workspace environment and in a fresh rootless runtime container. That exact x86_64 environment is now the mandatory initial support target. The previous ABI-9 guard is a superseded prototype, not a usable implementation for this target. A disposable credential-free probe on this ABI-3 runtime installed filesystem Landlock plus an additional seccomp filter, denied Unix/VSOCK socket creation and datagram socket pairs, retained connected stream/seqpacket pairs, and ran Node/Python subprocesses and Claude --version. That probe alone was primitive feasibility evidence. Subsequent production-guard, multiplex and wrapper enforcement results are recorded separately in docs/validation.md; operator-reported account login/reuse/refresh is now verified for the observed HTTPS/SSE flow; optional real-key API acceptance remains unavailable.

The common TODO mentions five wrappers; this checkout contains only Claude. Publish a portable contract and parity matrix here, with other implementations explicitly pending. Do not infer or edit sibling repositories.

## Goals / Non-Goals

**Goals:** enforce egress and host IPC boundaries despite arbitrary commands, live host bind mounts, and mutable Claude state; preserve ordinary shared/isolated file persistence; make operator authority explicit; retain identity, lifecycle, CA, and standard runtime security policy; distinguish enforcement evidence from authenticated compatibility.

**Non-Goals:** TLS interception, application-level data-loss prevention, filtering provider-hosted tools, protecting against the host operator/root or an escaped container, a delegated-build broker, automatic kernel/LSM configuration, and implementing sibling wrappers. No bundled local-provider, SSO, third-party cloud, or optional-feature exception is enabled by default. External Unix-service exceptions other than the selected proxy frontend are outside this change; local provider exceptions continue to use the trusted destination proxy.

## Decisions

### 1. Portable modes and explicit maintenance authority

Use `CLAUDE_CONTAINER_NETWORK=offline|provider|unrestricted`; unset/empty selects offline and unknown values fail. Offline is a safe default that does not guess the user's authentication flow. Provider mode additionally requires `CLAUDE_CONTAINER_NETWORK_PROFILE` and an absolute `CLAUDE_CONTAINER_NETWORK_POLICY` path to an operator-installed versioned policy. Unrestricted mode is a deliberate compatibility escape hatch, never a retry/fallback. Generic sibling wrappers can map these semantics to their own variable prefixes.

Use exact `CLAUDE_CONTAINER_MAINTENANCE=1` to authorize missing-image builds and explicit refreshes. Without it, report the needed operator invocation instead of auto-building. This authorization is host-side only and is not forwarded into the session. Report that image pulls, proxy-image acquisition, and build RUN steps occur outside runtime filtering; they need their own operator network controls if required. Pin the trusted proxy artifact by digest and require it to be prepared under maintenance authority. Never fetch proxy code during agent startup without that authority.

Before image mutations, validate mode, delegation conflict, policy, trusted assets, supported engine/backend, and available host kernel features. Confirm the actual container can enforce the complete policy before executing any agent-controlled code. Help remains side-effect free. An ABI below 3, disabled Landlock, blocked syscall, or failed rule/filter installation is an unsupported restricted session, not a reason to drop a required rule. No custom replacement seccomp profile, extra capability, host networking, relabeling, or automatic kernel/LSM change is introduced.

### 2. Combine private networking with Landlock ABI 3 and additive seccomp

Keep `--network=none`, explicitly private PID/IPC namespaces, read-only root, noexec tmpfs, caller identity and standard OCI security policy. Before untrusted execution, a protected static bootstrap installs Landlock ABI-3 filesystem restrictions and stacks an unprivileged classic seccomp BPF filter. This explicitly revises the earlier blanket ban on custom seccomp: only an additive in-process restriction is authorized. Never replace/disable/weaken the OCI profile or SELinux labels, add capabilities, or change the host kernel/LSM configuration.

Landlock handles MAKE_SOCK and REFER. Deny socket inode creation on host workspace/state/worktree binds; grant MAKE_SOCK only on verified container-private ephemeral /tmp, /run and /var/tmp hierarchies. Grant only REFER at the filesystem root to retain ordinary file rename/link behavior. Reject binds overlapping private roots, including aliases and descendants. This does not provide Unix connect mediation on ABI 3; the additional syscall filter supplies that boundary. Do not request ABI-9 RESOLVE_UNIX or abstract-scope rights or silently mask missing required rights.

The native x86_64 seccomp filter permits `socket()` only for AF_INET/AF_INET6; private networking contains those families. Deny AF_UNIX, AF_VSOCK, AF_NETLINK and all other new socket families. Allow `socketpair()` only for AF_UNIX connected SOCK_STREAM or SOCK_SEQPACKET, protocol zero, with CLOEXEC/NONBLOCK flags; deny datagram/raw and other pairs. Connected pairs must remain fixed to their original peer: verify reconnect, AF_UNSPEC disconnect, explicit sendto/sendmsg, shutdown, bind/autobind, listen and descriptor-transfer cases against real controlled external peers. Datagram pairs are unsafe because they can be retargeted. The filter checks native architecture and rejects i386/compat and x32 syscall ABIs; audit argument truncation and flag handling. Other architectures are outside the initial support target and require a separately tested filter.

Deny io_uring_setup/enter/register and pidfd_getfd, close inherited rings/pidfds/namespace descriptors, and retain no unconfined agent-side peer or supervisor. This closes alternate socket operations and foreign descriptor acquisition; shared same-session SCM_RIGHTS can convey only already confined handles. The trusted proxy never sends SCM_RIGHTS or host capabilities. Inherited fork/exec/thread restrictions cannot be removed by native permissions or later filters. No host /proc, namespace handles, devices or extra runtime directories are mounted.

**Compatibility cost:** new named or abstract Unix listeners and unconnected sockets are unavailable everywhere, including private tmpfs. Own loopback services, pipes and fixed-peer anonymous stream/seqpacket pairs remain usable. Existing connected pairs may bind/autobind private pathname or abstract names, but must never listen, change peer or publish a name on a host bind. This narrow naming allowance was explicitly approved by the operator after the real WSL probe. A private XDG_RUNTIME_DIR remains for ordinary runtime files but cannot restore named Unix IPC. Host agents, named cache/supervisor daemons and tools requiring named sockets are unsupported in restricted modes. Verify actual Claude tool execution; a version command alone is insufficient.

### 2a. Protected bootstrap and one preconnected provider channel

Use an immutable, hash/architecture-verified statically linked single-threaded native entrypoint from the protected installation. Before confinement it must not execute interpreters, load agent-selected libraries, read shell initialization/settings, or fork helpers. Validate ordinary terminal/pipe/file standard I/O and close all unrelated inherited descriptors. Set/check no_new_privs and install both enforcement layers before starting relay, Bash, Claude or any untrusted initialization. A failure in either layer exits nonzero; no partially confined application runs.

Only in provider mode, the bootstrap first connects once to the verified session proxy frontend. Validate protected directory/leaf, inode identity, owner/mode, mapped access, read-only transport bind, readiness and selected session/policy identity. This existing connected stream is the sole external descriptor exception; offline retains none. Close all setup descriptors and transfer the data descriptor only to the confined relay branch, closing it in the application exec branch. No unconnected Unix socket survives. The proxy is a separate read-only container outside the agent PID/IPC namespaces, with no agent workspace/state or Podman socket and no administrative protocol.

The relay accepts HTTP CONNECT on agent loopback, then multiplexes logical tunnels over this one inherited channel. Every logical OPEN is authorized independently by the trusted proxy. Direct agent access to the channel cannot broaden policy. If the channel or proxy dies, requests fail closed and a new session is required; never reconnect by opening Unix sockets, retain an unconfined in-container broker, or preopen a finite pool of one-shot sockets.

```text
Protected bootstrap --> connect verified proxy once (provider only)
        |               install Landlock ABI 3 + additive seccomp
        v
Confined Claude / Bash / relay -- one multiplexed data FD --> trusted proxy
        |                                                    |
        + own loopback / fixed-peer socket pairs              + approved host
        + direct IP: network=none
        + new Unix / VSOCK / alternate families: syscall denial
```

### 2b. Gate support on the measured WSL target

Require Linux 6.6.87.2-microsoft-standard-WSL2 x86_64 with usable Landlock ABI 3, successful additive-filter installation under the standard OCI profile, and the complete real-rootless gate. Record kernel/architecture, ABI, bootstrap/filter/protocol revisions, engine/backend, bind filesystem and security policy. ABI 3 must not itself trigger unsupported status or kernel-upgrade guidance; incomplete implementation/evidence is reported separately. Other platforms require their own evidence.

Retain the current unconditional restricted-startup hold until the complete revised gate passes on this WSL target and mandatory per-session checks are implemented. Neither the primitive probe nor mocked guard tests justify removing it. Test non-IP denial with syscall results and controlled positive controls; absence of a listening peer is not containment proof. If the target cannot pass, retain the hold and report the specific failed boundary rather than silently dropping controls or selecting unrestricted.

### 3. Protected installation and policy snapshots

Trust the host operator and launcher/bootstrap/proxy installation; treat the entire selected workspace (including its parent in worktree mode), Claude/OpenSpec state, commands, image environment, and agent-side relay as untrusted before bootstrap confinement. An operator needing persistent enforcement must launch a protected installation outside writable trees. Validate launcher/bootstrap/helper assets, immutable bootstrap identity, policies, and effective bind targets against those trees and reserved private IPC paths. Workspace `/` or another mount enclosing enforcement assets must fail restricted startup. No filesystem socket in a permitted host bind is implicitly an approved IPC exception.

Use a strict versioned JSON policy with schema version, revision, named profiles, exact hostname/port entries, required authentication hosts, optional feature switches, dated sources, and tested CLI/authentication metadata. Local-service entries additionally specify exact approved address/port scope; the initial shipped profiles contain none. Reject unknown fields, duplicate/conflicting entries, wildcards, unsafe ports, and malformed hostnames. Canonicalize ASCII DNS names case-insensitively with a single documented terminal-dot rule; reject non-ASCII or ambiguous authority forms rather than guessing IDNA normalization.

Resolve symlinks and validate ownership/access of files and ancestor directories. Accept only caller-owned or root-owned trusted inputs without group/other write access; require caller-owned private session storage. Refuse overlaps with every writable mount, including nested/symlink aliases and engine-remapped bind sources. Do not repair existing modes recursively. Snapshot validated content before use, record its content digest and revision, and do not hot-reload policy from agent state.

For same-host Unix launch service use, all bind sources must exist at their true absolute host paths. Validate an operator-provided session runtime base when the default cannot satisfy that invariant. Do not assume wrapper-local `/tmp` exists on the service host. Never delegate the launch endpoint to the agent. A protected policy alone is insufficient if mutable code or transport configuration can grant broader access.

### 4. Small trusted proxy surface

Package a dedicated minimal proxy process separately from the Claude image. A Python implementation can use strict authority parsing and `ipaddress` checks, but it must be treated as security-sensitive infrastructure with independent negative tests and bounded headers, tunnels, timeouts, and connection counts. Keep its container read-only under the standard runtime security policy; only its socket and redacted log storage are writable. Disable forwarding, inbound TCP listeners, and administration features. Do not require privileged firewall configuration.

Expose only a versioned multiplexed data protocol on the protected Unix frontend; keep HTTP CONNECT on agent loopback. Support approved HTTPS ports only. Normalize and compare exact hostnames; reject IP literals unless a policy explicitly authorizes a local-service entry, userinfo, encoded/ambiguous hosts, and every other method. Resolve only approved names in the trusted proxy. Reject mixed safe/unsafe DNS answer sets, mapped IPv4, and all non-global/special-use IPv4/IPv6 destinations, with explicit version-tested classification. Connect to the validated numeric address without a second DNS lookup; revalidate each new connection. Apply the same checks at every CNAME/resolution result. Local exceptions use a separate exact-address rule, never a blanket private-network bypass.

The multiplexed transport requires a fixed magic/version handshake, nonzero monotonically increasing 32-bit stream IDs, and bounded OPEN, OPEN_OK/ERR, DATA, HALF_CLOSE, CLOSE and WINDOW_UPDATE frames. OPEN carries only the bounded exact authority; it grants one upstream connection after the existing policy/DNS/address checks. Reuse no closed stream IDs; exhausted IDs require a new session. No administrative messages, client policy changes or host descriptor transfer exist. Reject malformed/unknown frames, version mismatches, duplicate IDs, length/credit overflow and invalid state transitions without logging raw input.

Limit sessions to 64 active streams, data frames to 16 KiB, OPEN authorities to 8 KiB, queued data to 256 KiB per stream and 16 MiB per session, with bounded connect/idle/handshake deadlines and flow-control credits. Enforce bounds independently at both peers; backpressure one stream without unbounded queues or starvation. Sequential requests beyond 64 must work; this is an active concurrency bound, not a lifetime request pool. Test multiplex isolation, cancellation, half-close, abrupt death, malformed frames, sustained TLS/streaming/WebSocket traffic and redacted errors. Pin the new proxy protocol/artifact revision; the existing one-connection-per-tunnel proxy and relay are not compatible with this design.

No static CDN addresses or vendor wildcards. Trusted upstream resolution may follow DNS infrastructure dependencies, but arbitrary unapproved agent names must never enter it. The proxy itself is trusted; its infrastructure network path and upstream resolver configuration must not be agent-writable.

CONNECT tunnels cannot establish application-level isolation: encrypted HTTP Host, domain fronting, shared services, and provider-side actions remain outside inspection. Allowed endpoints may receive arbitrary session data. Preserve TLS verification at the client and the existing CA opt-in; no decryption or `NODE_TLS_REJECT_UNAUTHORIZED=0`.

### 5. Client configuration and Claude inventory

Set both cases of HTTP/HTTPS proxy variables to the loopback relay, replace both cases of `NO_PROXY` with exact loopback entries, and clear inherited/image alternate proxy defaults such as `ALL_PROXY`. Offline clears proxy variables and does not start a relay. Unrestricted must be documented separately from restricted client configuration. Relay startup/exit must preserve stdin, argv, TTY, and signals for Claude and Bash.

For both restricted modes, create a caller-owned `0700` runtime directory inside the private `/tmp` tmpfs before application startup and set `XDG_RUNTIME_DIR` to that fixed session-private location. Do not inherit an image or host value pointing into persistent state. Keep HOME and Claude/OpenSpec configuration persistence unchanged. This directory holds ordinary runtime files; named Unix services remain denied even there. Verify each CLI/tool flow under that limitation.

Initial inventory, checked against official standalone CLI documentation on 2026-11-06; these are candidate profiles pending installed-version evidence:

| Profile | Base exact destinations on 443 | Readiness |
| --- | --- | --- |
| `anthropic-api` | `api.anthropic.com` | Implemented with synthetic CLI/proxy coverage; real-key verification is optional, unavailable without a key and non-blocking |
| `anthropic-account` | API host plus `claude.ai`, `claude.com`, `platform.claude.com` | Operator-reported login, reuse and post-expiry refresh passed on 2026-11-07; see validation.md for transport/callback limits |
| Explicit SSO extension | Only the selected flow's hosts, including `sso.claude.com` when required | No default grant |
| Cloud/gateway/local/feature extensions | Separate reviewed exact inventory | Not bundled or verified |

Browser login performed on the host is outside the container's boundary. Record which browser steps are external and which CLI token exchange/refresh steps traverse the proxy. Test localhost OAuth callbacks inside the isolated topology; do not add host networking to repair them. If a login flow cannot operate under the boundary, record it as unsupported until an explicit narrow design is reviewed.

On the queried installed version, verify supported controls such as `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`, update/telemetry/error-reporting controls, `ENABLE_CLAUDEAI_MCP_SERVERS=false`, and artifact disablement. Record exact effective values rather than assuming a setting exists. Documentation and plugin requests remain denied even if writable state re-enables them. Add destinations only through explicit operator profile revisions. API hosts may carry optional traffic as well as inference; domain filtering cannot distinguish them.

### 6. Ownership, diagnostics, and acceptance

Initialize cleanup traps before creating any new resource. Use unguessable session tokens, atomic names, and recoverable ownership labels/IDs for proxy and agent containers; protect per-session directories and never share proxy policy state across sessions. Extend the current bounded control helper to all resources without multiplying its 20-second deadline. Remove the agent before proxy transport/configuration, recover interrupted creates, reap only owned clients, and report uncertain removal. Proxy death leaves the agent without a direct network path; do not restart it under another policy or attach another network.

Emit mode/profile/policy revision/digest, bootstrap revision, filter/protocol revisions and usable ABI/features at startup. Keep the earlier protected redacted destination logs. Bootstrap diagnostics distinguish missing ABI, blocked rule installation, unsafe inherited descriptors, bad socket identity, and denied persistent IPC placement without dumping environment values or arbitrary file paths from request data. Client-visible provider authentication errors remain separate from transport failures.

Acceptance has three layers: synthetic policy/bootstrap/lifecycle checks; credential-free real-rootless IP and IPC enforcement; separately authorized authenticated CLI compatibility. Credential-free enforcement and synthetic API-key client coverage remain mandatory. A real API-key request is an optional manual compatibility check, never a prerequisite for account authentication or completion of this change when no key is available. Keep its result unavailable instead of passing it by inference, and reserve real-provider-verified claims for observed requests. This availability exception does not waive the remaining account login/refresh acceptance. The original unconfined IPC fixture remains a positive control. On a supported platform the same outside socket must be denied in workspace, worktree parent, shared state, and isolated home, whether it exists before startup or appears later. Cover stream/datagram/seqpacket operations, explicit-address sendmsg/sendto, pathname aliases, replacement, abstract endpoints, inherited descriptors/SCM_RIGHTS, io_uring paths, cross-session access, and non-IP transports. Verify connected stream/seqpacket pairs, own-loopback services, ordinary file rename/link/Git behavior and multiplexed proxy access positively; verify named Unix services are denied even on private tmpfs.

Install failure, spoofed feature reporting, an ABI below 3, filter installation failure, compat/x32 syscalls, and early loader/interpreter injection must fail before any agent sentinel executes. Verify inheritance through shell, native permission bypass, threads, fork/exec, namespaces, and attempted removal of the policy. Rerun lifecycle, CA/TLS/streaming/WebSocket and actual Claude tool-spawning checks through the bootstrap. Historical pre-guard passes remain component evidence, not revised full acceptance. No credentials or paid calls belong in these automated fixtures.

## Risks / Trade-offs

- Breaking offline default and maintenance gate -> publish migration commands before rollout; existing broad workflows require explicit unrestricted mode.
- Unix socket bind, path remapping, permissions, or SELinux incompatibility -> mandatory rootless feasibility gate; fail closed on unsupported environments.
- Additive seccomp compatibility -> require ABI 3 and successful installation on the measured WSL target under the standard OCI policy; do not require an upgrade or weaken that policy.
- All named Unix daemons/caches are unavailable, including in private tmpfs -> verify actual Claude tool spawning and use pipes, fixed-peer pairs or own loopback where supported; record incompatible flows without disabling the guard.
- Landlock REFER and socket aliases affect filesystem compatibility -> explicitly preserve ordinary REFER behavior, deny persistent socket creation/placement, and test Git/worktree rename/link operations.
- Pre-policy application code or leaked connected descriptors could bypass IPC mediation -> use a protected static single-threaded bootstrap, clean descriptor inheritance, and adversarial loader/FD tests.
- Syscall/ABI or asynchronous bypass -> audit native architecture checks, reject compat/x32, io_uring and pidfd_getfd; retain descriptor hygiene and controlled transport tests.
- Multiplex framing adds trusted code and shared-channel failure -> version/pin the protocol, bound credits/buffers/streams, fuzz state/length errors and fail all requests closed on channel death.
- Provider endpoints and unpinned CLI behavior change -> query versions, date inventories, and revalidate login/refresh/transports on upgrades.
- Other wrappers may choose inconsistent defaults -> publish normative parity examples and mark sibling adoption pending; do not claim five-wrapper completion here.
- Unavailable credentials cannot establish real-provider readiness -> keep the real-key API check optional/non-blocking and explicitly unavailable; keep mandatory account acceptance unchecked until verified.

## Migration Plan

1. Implement and test the protected bootstrap as an isolated component. Replace the ABI-9 prototype with ABI-3 filesystem rules and the audited additive native filter; implement the preconnected multiplexed proxy/relay. Use the measured WSL kernel as the required acceptance environment.
2. Reproduce the original IPC bypass as a control, then verify the complete IP/IPC/alternate-transport gate and standard security-policy compatibility. Publish supported kernel/ABI/bootstrap/engine/filesystem combinations only from passing results. Retain the startup hold while the gate is incomplete.
3. Install trusted launcher/bootstrap/proxy assets and policies outside workspace/state, prepare digest-pinned images under explicit maintenance authorization, and verify private runtime directories, shared/isolated persistence and all bootstrap paths.
4. Publish examples for offline shell, API/account sessions, WSL ABI-3 prerequisites, denied named/abstract Unix IPC, explicit unrestricted workflows, and maintenance. Existing socket users must select unrestricted explicitly.
5. Replace the blanket hold only with verified mandatory per-session enforcement checks; allow the measured WSL target only after passing evidence and actual per-session installation; retain refusal on failed setups. Roll out the default with a startup summary and actionable capability diagnostics.
6. Run the separately authorized account acceptance and any available optional real-key API check; label each profile with its actual evidence. Lack of an API key does not block this change or account use. Keep sibling-wrapper adoption pending until independently verified.
7. Rollback requires an explicit operator installation/version decision or explicit unrestricted invocation. Never silently retry a restricted invocation without enforcement.

## References

- [Claude standalone CLI network configuration](https://code.claude.com/docs/en/network-config), reviewed 2026-11-06; endpoint/control inventory remains version-sensitive.
- [Podman 4.9.3 network creation](https://docs.podman.io/en/v4.9.3/markdown/podman-network-create.1.html#internal), reviewed 2026-11-06; internal-network behavior is backend-sensitive.
- [Podman API authority](https://docs.podman.io/en/latest/markdown/podman-system-service.1.html#security), reviewed 2026-11-06; socket exposure grants authority beyond runtime proxy variables.
- [Landlock userspace API](https://docs.kernel.org/userspace-api/landlock.html), reviewed 2026-11-06; IPC rights, inheritance, no_new_privs, bind semantics and ABI negotiation. This design intentionally rejects missing required features instead of using a best-effort subset.
- [Linux v6.6 Landlock UAPI](https://raw.githubusercontent.com/torvalds/linux/v6.6/include/uapi/linux/landlock.h), reviewed 2026-11-06; filesystem rights available to the ABI-3 target.
- [Seccomp filter API](https://docs.kernel.org/userspace-api/seccomp_filter.html), reviewed 2026-11-06; no_new_privs, inheritance, architecture checks and restrictive filter stacking. Filters cannot inspect pointed-to pathname memory.
- [Linux v6.6 Unix sockets](https://raw.githubusercontent.com/torvalds/linux/v6.6/net/unix/af_unix.c), reviewed 2026-11-06; connected stream/seqpacket behavior informs the selected pair allowance and must be confirmed by wrapper tests.
