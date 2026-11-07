# Network policy contract

Status: mandatory implementation/acceptance complete; specifications synchronized
and change archived as `2026-11-07-add-enforced-network-egress` following
the IPC design revision. IP-only tests passed, but an unapproved workspace Unix
socket bypassed that candidate, now replaced by mandatory native confinement.
The ABI-3 guard and multiplexed proxy are integrated; evidence and remaining
authenticated compatibility gaps are recorded separately.
See [the validation record](validation.md). A real account request using existing
OAuth credentials, fresh isolated login, saved-credential reuse and automatic
refresh after expiry passed in operator-reported checks. Real-key API access
remains unverified.
API-key support remains implemented with mandatory synthetic coverage; the
separately authorized real-key check is optional and unavailable without a key,
and does not block this change or account use. It is not counted as a passed
real-provider test.

The durable contract is [network-egress](../openspec/specs/network-egress/spec.md).
The [archived change](../openspec/changes/archive/2026-11-07-add-enforced-network-egress/)
retains the design, delta specifications, completed tasks and optional real-key
API check.

## Portable behavior

| Mode | Agent access | Socket delegation |
| --- | --- | --- |
| `offline` (unset/empty default) | Own loopback, pipes and fixed-peer socket pairs only | Rejected |
| `provider` | Loopback/pipes/pairs and preconnected exact-destination proxy | Rejected |
| `unrestricted` (explicit only) | Ordinary runtime networking | Exact opt-in allowed |

Unknown modes fail before image operations. Restricted setup errors never retry
with unrestricted networking. Operator configuration selects the outer policy;
workspace/application settings, native approvals, YOLO, and shell mode cannot
broaden it. Restricted agents have no direct route, external resolver, UDP/QUIC,
host/LAN/metadata access, lateral session access, or proxy administration access.

## Required kernel and IPC boundary

Both restricted modes require a protected static native bootstrap before any
application, interpreter, relay or shell initialization. The mandatory initial
target is Linux 6.6.87.2-microsoft-standard-WSL2 x86_64 with usable Landlock ABI 3.
No kernel upgrade or ABI-9 IPC right is required. Native/rootless evidence is
required for support; primitive or mocked probes alone do not establish it.

The bootstrap sets no_new_privs, installs ABI-3 MAKE_SOCK/REFER filesystem rules,
and stacks a restrictive native x86_64 seccomp filter on the standard OCI profile.
SELinux, noexec tmpfs and ordinary rootless privileges remain unchanged. Deny new
socket families except IPv4/IPv6 (contained by private network=none), including
Unix, VSOCK and Netlink. Permit only connected AF_UNIX stream/seqpacket pairs;
deny retargetable datagram/raw pairs, compat/x32 syscall ABIs, io_uring operations
and pidfd_getfd. A failed rule/filter installation stops before agent code.
Never replace/weaken the OCI profile or retry unrestricted automatically.

Provider mode retains exactly one bootstrap-verified preconnected data channel
to its protected session proxy; offline retains none. A versioned bounded
multiplex protocol supports repeated/concurrent independently authorized tunnels.
The relay is confined, no unfiltered supervisor remains, and neither proxy nor
protocol sends host descriptors or exposes administration. Channel death fails
closed and requires a new session; no finite one-shot socket pool or reconnect
exception is permitted. Close the data FD before executing the application branch.

External pathname/abstract Unix services stay inaccessible regardless of mount,
alias, socket type or creation time. **New named Unix services and unconnected Unix sockets are denied everywhere,
including private tmpfs.** Existing connected pairs may have inert private names,
but cannot become listeners, retarget or publish on host binds. Preserve own-loopback services, pipes and
fixed-peer connected stream/seqpacket pairs. Verify attempts to retarget those
pairs, descriptor transfer and inheritance against controlled external peers.
Host agents, named caches/daemons and external supervisors are incompatible with
restricted mode; a private runtime directory does not restore named IPC.

Landlock additionally denies socket inode creation/placement on shared file
state. Verify private /tmp, /run and /var/tmp roots and reject overlapping binds;
explicit REFER grants retain baseline ordinary rename/link/Git/worktree behavior.
Keep HOME/configuration unchanged and use a private 0700 XDG_RUNTIME_DIR for
ordinary runtime files. Preserve validated terminal/pipe/file stdio and close all
other inherited handles before preparation. Explicitly use private PID/IPC
namespaces; expose no host process, namespace, ring or device handles.

The release matrix records kernel/architecture, ABI, bootstrap/filter/protocol
identities, engine/backend, standard OCI policy, filesystem and actual positive/
negative results. Test Unix bypasses, alternate-family denial with positive
controls, async/compat syscalls, actual tool execution and session lifecycle.
Historical IP-only passes and mocked guard passes remain component evidence.
Startup uses mandatory checks after the credential-free WSL gate; authenticated
account login/reuse/refresh has scoped manual evidence; optional real-key API
readiness remains unverified. Actual tool execution has a separate synthetic
Messages-API check.

These semantics are the common contract. Each sibling wrapper needs its own
bootstrap integration, compatibility and enforcement evidence before adoption
can be declared complete. Kernel/API references are recorded in the change's
design; this document does not claim that the current environment passed them.

Provider policies are versioned protected inputs outside writable mounts. They
select exact normalized hostnames and ports, normally HTTPS CONNECT on 443.
Connection-time IPv4/IPv6 validation denies private/special destinations and DNS
rebinding. Explicit local exceptions require an exact destination, address scope,
and port. Denials never add exceptions. TLS verification remains enabled without
decryption. Shell/commands that ignore proxy variables remain isolated.

API and account authentication use separate profiles. SSO, cloud/gateway/local
providers, optional features, Git, registries, browsing, and MCP destinations
require explicit reviewed additions. Record policy revision, source date, CLI
version, authentication method, and actual compatibility evidence. Disable
unnecessary optional traffic using version-supported controls.

Image pulls, proxy acquisition, and build RUN steps are separate host maintenance
activities. Exact operator maintenance authorization is required for acquisition
or builds; selecting unrestricted runtime mode does not authorize maintenance.
The runtime filter does not constrain those host activities. Do not forward
maintenance authority into the agent.

Each session owns distinct recoverable resources. Setup failure and shutdown
remove only owned resources within one 20-second budget and preserve the primary
exit/signal status. Proxy failure leaves outbound connections closed. Protected
bounded logs contain sanitized destination/port/reason, never secrets or payloads.

## Claude migration examples

The following interfaces require the prepared protected guard and the measured
platform. Use the protected installed wrapper path in place of
`./claude-container.sh` when the checkout is agent-writable:

```bash
# Default offline shell; image must already exist.
./claude-container.sh --container-shell

# Restricted API session with an operator-installed policy.
CLAUDE_CONTAINER_NETWORK=provider \
CLAUDE_CONTAINER_NETWORK_PROFILE=anthropic-api \
CLAUDE_CONTAINER_NETWORK_POLICY=/opt/claude-container/network/policies/default.json \
CLAUDE_CONTAINER_NETWORK_RUNTIME_DIR="$HOME/.local/state/claude-egress" \
CLAUDE_CONTAINER_EGRESS_IMAGE="$egress_image" \
./claude-container.sh

# Select anthropic-account for the verified account login/reuse/refresh flow.
# Prepare service/image/runtime per README; see validation.md for evidence limits.
# Explicit broad-network compatibility and host API authority.
CLAUDE_CONTAINER_NETWORK=unrestricted CLAUDE_CONTAINER_PODMAN=1 \
./claude-container.sh

# Operator-controlled preparation; runtime mode does not filter build traffic.
CLAUDE_CONTAINER_NETWORK=unrestricted CLAUDE_CONTAINER_MAINTENANCE=1 \
./claude-container.sh --container-build
```

Changing profiles or adding endpoints requires an operator policy revision and
revalidation. An agent-writable launcher cannot protect its own future launches;
install launcher/helpers/policies outside every writable workspace/state tree.

## Five-wrapper parity checklist

The upstream TODO identifies five wrappers but this checkout supplies only
Claude. The other four identities/repositories have not been supplied here.
Variable prefixes may differ; behavior and migration semantics must agree.

| Wrapper | Contract adoption | Implementation | Real enforcement | Auth compatibility |
| --- | --- | --- | --- | --- |
| Claude (this repository) | WSL ABI-3/additive-filter contract specified here | Mandatory bootstrap and multiplexed proxy integrated | See versioned guard, IP/IPC and wrapper evidence | Account login/reuse/refresh passed; real-key API optional/unavailable |
| Sibling 1 (identity not supplied) | Pending | Not assessed | Not assessed | Not assessed |
| Sibling 2 (identity not supplied) | Pending | Not assessed | Not assessed | Not assessed |
| Sibling 3 (identity not supplied) | Pending | Not assessed | Not assessed | Not assessed |
| Sibling 4 (identity not supplied) | Pending | Not assessed | Not assessed | Not assessed |

For each wrapper, record mode/default parity, operator policy authority, separate
maintenance permission, authentication/feature inventories, delegation rejection,
kernel/ABI/bootstrap prerequisites, Unix and alternate-transport isolation,
denied named IPC, fixed-peer pairs and multiplexed transport, preserved file persistence, DNS/address controls,
TLS/CA compatibility, redacted diagnostics,
owned bounded cleanup, controlled bypass evidence, and separate authenticated
login/refresh/streaming/WebSocket evidence. No untested entry counts as passed.

## Limits

Destination filtering permits data to be sent to allowed services. CONNECT does
not inspect encrypted application hosts, content, domain fronting, or shared
services. Network activity performed remotely by provider-hosted tools is outside
the local boundary. Rootless/backend support must be based on controlled positive
and negative tests, not an `--internal` flag or a failed Internet request alone.


## N01–N14 implementation and acceptance map

| Source task | Claude implementation | Acceptance / remaining scope |
| --- | --- | --- |
| N01 | Operator modes, protected profiles and separate maintenance authority | Wrapper/policy tests; sibling rollout pending |
| N02 | Private network/PID/IPC plus ABI-3 Landlock and additive seccomp | Real guard IP/IPC/alternate-family tests and wrapper gate |
| N03 | Outside session-owned versioned multiplex proxy, exact CONNECT authority policy | Codec/parser/address/TLS/streaming/WebSocket tests |
| N04 | Protected installation, static guard digest, policy snapshot/session manifest | Path/alias/ancestor/ELF/digest/mount/readiness rejection tests |
| N05 | Non-forwarding agent resolver, trusted per-OPEN resolution, numeric connect | DNS/rebinding/mixed/special IPv4/IPv6 and UDP/QUIC bypass tests |
| N06 | Consistent proxy/bypass variables, confined loopback relay, TLS unchanged | Synthetic real CLI/SSE tool and transport checks; real account request/refresh passed; long-lived/WebSocket transport covered by controlled fixtures |
| N07 | Exact delegation opt-in rejected before restricted setup | Real mode/state/shell/YOLO grid; unrestricted endpoint regressions |
| N08 | Unique ownership, recovery, one bounded shutdown budget | Concurrent/failed/interrupted setup, proxy death, stalled cleanup and statuses |
| N09 | Explicit host maintenance gate, immutable/prepared artifacts | Build/context/preflight tests; unrelated destinations remain denied |
| N10 | Protected bounded normalized destination/reason diagnostics | Secret/control-character/framing fuzz and real denial-log checks |
| N11 | Credential-free guard/proxy/wrapper and legacy positive controls | Mandatory account task 6.5 completed with scoped manual evidence; real-key check 6.4 is optional/unavailable |
| N12 | README/help/AGENTS, OpenSpec deltas, contract/parity and versioned evidence | Strict validation; main-spec sync/archive is a separate workflow |
| N13 | Dated installed-version API/account endpoint inventories | Account login/reuse/refresh passed; real-key API optional/unavailable |
| N14 | Version-supported optional-traffic controls and existing single-file CA trust | Native/YOLO/shell, actual synthetic Bash tool and CA checks; real login/reuse/refresh passed |
