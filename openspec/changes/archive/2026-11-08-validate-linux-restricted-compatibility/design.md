# Design

## Context

See `proposal.md` for motivation and breaking behavior. The wrapper and `setup.setup.verify_engine` duplicate WSL kernel, Podman 4.9.3 and disabled-SELinux/AppArmor checks. `setup/smoke.py` already checks Unix socket creation rejection, direct IP failure, loopback bind and socket-pair creation; it does not provide controlled external-peer evidence, data exchange, complete transport checks or a persistent qualification record. The static guard's `--probe` queries ABI only. Current main specs require full transport evidence before platform support, so the deltas explicitly separate local installation qualification from release-measured acceptance.

## Goals / Non-Goals

**Goals:** Admit native Linux and WSL2 based on enforceable capabilities and local evidence; retain all outer boundaries; share eligibility decisions; invalidate evidence after relevant changes; avoid an exhaustive distribution/version matrix.

**Non-Goals:** Guarantee compatibility with SELinux/AppArmor, support other architectures/backends or remote services, automatically alter host policy, authenticate to providers, implement N20's missing-setup UX, or close N21-N24. Apply N18 first and preserve its hardening and enforced proxy budgets.

## Decisions

### Shared protected eligibility validation

Introduce `network/platform_check.py` as a standard-library-only helper and command entry point used by wrapper preflight and setup. Package and validate it with the protected installation. Retain the existing launch-engine and exact endpoint verification; centralize the restricted-specific evaluation and stable failure categories. Parse stable numeric Podman server versions >= 4.9 (accept distribution suffixes only after an unambiguous numeric core; reject prerelease/unknown forms). There is no upper bound. Require Linux x86_64, rootless Netavark, same-host Unix launch service, host Python, standard OCI seccomp and actual ABI >= 3 guard support. Kernel release is evidence, not an eligibility whitelist. Host and container probes remain separate from actual rule installation.

SELinux/AppArmor enabled flags become recorded observations rather than automatic rejection. Keep both policies and normal mount labels. Policy failure is an incompatibility diagnostic, never a request to disable the module or relabel the workspace. This permits attempted qualification without promising it succeeds.

Alternative: retain per-distribution allowlists. Rejected because it requires precisely the matrix maintenance the operator wants to avoid. Pure ABI/version admission is rejected because it cannot establish enforcement.

### Dedicated fixed qualification operation

Add `--container-qualify`, usable alone through direct or managed invocation. Setup invokes it against its protected candidate before activation. It runs only fixed protected credential-free fixtures with disposable state, never forwarded application arguments, workspace startup hooks, real Claude configuration or a model request. It uses the ordinary production container preparation, guard, relay, proxy, hardening and cleanup paths. Only the requirement for an existing qualification report is bypassed for these fixed probes; no runtime enforcement or path validation is bypassed. Reject mixed options. Do not add an environment variable that authorizes arbitrary report-free application startup.

Keep `--container-help` independent of report loading. Ordinary explicit environment configuration remains supported when its effective workflow has matching qualification; N20 is not implemented. Maintenance remains separately authorized, and qualification does not grant pulls/builds implicitly.

### Bounded local gate with meaningful controls

Move reusable fixture logic from the existing guard/network acceptance helpers into protected production qualification inputs, explicitly excluding syscall mocks and monkeypatches from shipped enforcement. Expand the current smoke instead of treating it as full qualification. Add `network/qualify.py` for host orchestration and a protected fixture program executed through the guard. Use private native temporary storage, caller-owned endpoints and bounded per-check/overall deadlines; failure removes only owned fixtures and never activates the candidate.

The required gate covers:

| Boundary | Required evidence |
| --- | --- |
| Direct IP, DNS, UDP and IPv6 | Controlled host listeners reachable by unconfined controls; restricted attempts cannot reach them, including with proxy variables removed. Verify only loopback exists and no secondary route. Protocols disabled on the host require explicit syscall/policy denial evidence rather than an arbitrary connection error. |
| External Unix IPC | Existing and late-created controlled sockets in disposable host binds are reachable outside confinement and inaccessible inside; named listeners/publication remain denied. Exercise aliases and explicit datagram destinations where applicable. |
| Allowed local IPC/files | Actual TCP/UDP loopback and stream/seqpacket pair data exchange, descendant inheritance and ordinary caller-owned file persistence work. Pair retargeting, datagram/raw pairs and descriptor transfer remain denied. |
| Alternate host paths | Production-filter syscall checks cover non-approved families including VSOCK/Netlink, compat/x32 and asynchronous bypasses. Creation or operation explicitly rejected by the installed filter is evidence; no listening peer alone is insufficient. Any enabled path not assessable keeps qualification unavailable. |
| Provider path | Controlled matching-SNI TLS with certificate validation, mismatched SNI with zero upstream client bytes, denied CONNECT and channel/proxy-loss failure closure through the production proxy and relay. Verify N18 capability/privilege and effective cgroup settings. |

Controlled TLS qualification must not require public DNS/CDN availability. Reuse the existing shared-address TLS fixture approach in a separate disposable topology with exact fixture-only policy/certificates and positive controls. Any existing test instrumentation for private fixture connectivity stays confined to disposable fixtures and cannot enter the shipped production proxy image, guard or production policy. Exercise actual production authorization separately with an unapproved name and the selected policy's startup identities. No trusted-runtime switch may disable production DNS/address or SNI validation. If a local fixture cannot establish a required production guarantee, qualification fails; do not replace it with a version query.

Use the same protected gate for offline and provider workflows, with provider checks added for provider mode. Do not require a separately qualified record for shared/isolated state solely because paths differ: all actual paths still undergo per-launch checks and the gate exercises both mount semantics. Profiles and effective policy/image changes do require matching qualification.

### Protected report and invalidation

Publish `qualification/<fingerprint>.json` atomically inside the protected installation release, outside all application-writable mounts. Validate ownership, ancestors, file type, strict schema and overlap on publication and every read. The record includes gate revision/time, complete pass outcomes and positive controls, plus a fingerprint of:

- Kernel release, boot identity, architecture and effective ABI.
- Actual server version, backend, verified host socket identity (including remapped endpoint resolution), effective engine/security configuration and observable LSM policy identity.
- Guard digest/revision, protected enforcement/gate code and fixture digests.
- Inspected immutable runtime/proxy image IDs, restricted mode, policy/profile digest, and N18 hardening/resource settings.

Hash canonical structured data; never use a writable boolean or timestamp alone. Compare current evidence at ordinary launch before application execution. Unknown identities, missing/malformed reports and any mismatch request setup or explicit qualification again. Relevant host security-policy changes must invalidate evidence; where a stable policy identity cannot be obtained, rerun the gate before ordinary launch rather than silently reuse unverifiable evidence. Bind reports to the boot so reboot cannot preserve stale host assumptions.

Keep qualifications for multiple exact workflows separate. Environment overrides select their own fingerprint; they do not inherit broader evidence from saved preferences. Resolved mount paths and permissions are still validated each launch. During qualification compute identities before and after the gate; publish only if they match, and abort on concurrent change. Per-launch bootstrap, policy/readiness and effective hardening checks remain mandatory even with a matching report.

Alternative: run the entire gate for every session. Rejected as the default due to startup cost; it remains the conservative behavior when policy identity cannot safely be reused. A receipt authorizes only the measured installation contract and cannot replace inherited confinement.

### Honest readiness categories

Use machine-readable `ineligible`, `qualification-required`, `locally-qualified` and `release-measured` categories with concise English diagnostics. Setup reports local qualification separately from authentication. A combination receives `release-measured` only when tracked evidence matches the relevant current inputs; matching the historical kernel string is insufficient. Unmeasured native/WSL combinations show a visible notice. SELinux/AppArmor compatibility remains unguaranteed even after a local pass; the report describes the tested effective policy, not all future policies.

`network/release_acceptance.json` is an optional protected exact-fingerprint inventory for those display claims. Its initial inventory is empty; local qualification never automatically adds a release acceptance entry. This display inventory cannot authorize startup without a successful matching installation report. The shared eligibility module is named `platform_check.py` to avoid shadowing Python's standard `platform` module.

## Risks / Trade-offs

- Local tests cover a finite boundary and cannot certify all future kernels or engine behavior. Mitigation: retain production enforcement, explicit limits, invalidation and release regression suites; accurately label local evidence.
- Qualification on restrictive host policies may fail to create fixtures. Mitigation: distinguish fixture/precondition failures from denials; leave unavailable checks blocking and policies unchanged.
- Reports introduce a startup trust input and a migration requirement. Mitigation: strict protected-path/schema checks, atomic publication, no application bypass and stale/tampered-report regressions.
- Engine/security identity can be difficult to observe across versions. Mitigation: fail parsing unknown data; rerun qualification when reuse cannot be established rather than guessing equivalence.
- Fixture orchestration can leak resources or stall. Mitigation: session ownership, bounded subprocess groups, disposable state and existing rollback patterns.

## Migration Plan

1. Apply and validate N18 first. Package the shared validator, gate and fixtures in managed releases and update fixture-copy inventories in runtime tests.
2. Introduce capability eligibility and candidate qualification together; never ship relaxed pins without the gate and ordinary-launch checks.
3. Rerun setup for existing managed installations. A previous release stays selected until the candidate passes and publishes its report. Manually prepared installations run `--container-qualify` with explicit protected configuration before ordinary restricted use.
4. Exercise the existing WSL environment and any native environment actually available; record native checks as unavailable if none is provided. A native release matrix is not required for completion, but the locally executed gate must be mandatory and tested through production paths.
5. Update docs/spec wording and N19 status to distinguish measured release regression from per-installation qualification. Roll back by restoring the previous complete protected release and its original admission rules, never by accepting a new release without evidence.
