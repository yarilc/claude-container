# Tasks

## 1. Consolidate capability eligibility after N18

- [x] 1.1 Confirm N18's implemented hardening and proxy budgets before changing admission; verify its production acceptance is recorded and carry the final settings into N19 fixtures/fingerprints.
- [x] 1.2 Add protected `network/platform_check.py` with common Linux/x86_64, rootless same-host Unix service, Netavark, stable Podman >= 4.9, seccomp and ABI eligibility rules; verify table-driven tests cover native/WSL kernels, later stable versions, distribution suffixes, active LSM flags and malformed/unsupported inputs.
- [x] 1.3 Route wrapper/setup restricted checks through the shared validator while retaining exact endpoint and engine verification; verify synthetic parity, fail-before-image prerequisite failures and unchanged help/unrestricted behavior. Keep relaxed admission unavailable to ordinary use until report checks land.
- [x] 1.4 Package and trust-check the validator in `setup/common.py`, control preflight and runtime fixture-copy inventories; verify installed-path execution rejects unsafe/missing helpers and does not import workspace modules.
- [x] 1.5 Update eligibility wording in README/help, AGENTS.md and network/setup guidance; verify documents identify native Linux/WSL2 eligibility, no upper pins, effective ABI checks and unguaranteed SELinux/AppArmor compatibility without suggesting policy changes.

## 2. Build the protected local gate

- [x] 2.1 Add protected gate orchestration and fixed fixture inputs with private native storage, bounded process groups and owned cleanup; verify synthetic fixture/precondition failure, timeout, cancellation and concurrent runs cannot issue success or remove unrelated state.
- [x] 2.2 Extend IP/DNS/UDP/IPv6 checks with controlled listening peers and unconfined positive controls; verify real restricted denial with proxy variables removed, actual loopback data exchange and rejection of unrelated-connectivity errors as proof.
- [x] 2.3 Extend Unix/alternate-transport checks for existing/late endpoints, aliases, host-bind publication, pair transfer/retargeting, descendants, forbidden families, compat/x32 and asynchronous bypasses; verify production guard syscall results and permitted pair/file data exchange, keeping mocks out of shipped artifacts.
- [x] 2.4 Add disposable controlled TLS qualification through the production guard/relay/proxy for matching SNI, mismatch zero-byte rejection, denied authority and channel/proxy loss; verify fixture isolation cannot change production DNS/address checks, policy inventories or CA defaults and needs no public CDN or credentials.
- [x] 2.5 Cover N18 effective capability, no-new-privileges and proxy cgroup settings in the gate; verify a failed or unverifiable setting blocks qualification and that both state-mode mount semantics are exercised.
- [x] 2.6 Expose fixed `--container-qualify` dispatch for direct and managed invocation and use it for setup candidates; verify mixed arguments, writable fixture substitution and environment-based report bypass attempts fail, while actual fixed probes can run before any report exists.
- [x] 2.7 Package gate/fixture inputs in protected releases and document the operation, required controls and blocking unavailable checks in `network/README.md` and `docs/setup.md`; verify an installed candidate runs independently of the checkout/tests tree.

## 3. Bind readiness to current evidence

- [x] 3.1 Implement strict report schema, canonical fingerprinting and protected atomic publication under the release's `qualification` directory; verify checks cover host/boot, endpoint remapping, ABI, engine/backend/security, enforcement/gate code, immutable images, mode/profile/policy and N18 settings without storing secrets.
- [x] 3.2 Compare identities before/after qualification and invalidate reused evidence on changed or unobservable security-policy state; verify concurrent changes abort publication and unknown reusable identity requires a fresh gate rather than an assumed match.
- [x] 3.3 Require matching successful reports for ordinary restricted launches while retaining all per-launch guard/path/readiness checks; verify missing, stale, malformed, tampered, unsafe-path and mismatched override cases fail before application execution, including explicitly configured direct invocation.
- [x] 3.4 Publish reports before managed activation and preserve prior release/report on failure; verify setup synthetic and real disposable runtime cases cover activation rollback, rerun, interrupted publication, multiple workflow reports and authentication status separation.
- [x] 3.5 Add eligibility/qualification diagnostics and conservative measured-status reporting; verify only matching tracked acceptance can yield release-measured status and locally qualified combinations display a visible notice.
- [x] 3.6 Document migration, manual qualification, reboot/update invalidation and rollback in README/help, setup guidance and the network contract; verify examples do not implement N20 or imply exhaustive/native-LSM/authenticated compatibility.

## 4. Integrated acceptance and evidence

- [x] 4.1 Run wrapper/setup synthetic suites, qualification-specific tests, policy/mux/TLS suites, changed shell syntax checks and `git diff --check`; verify no weakened enforcement, private policy-path exceptions or changes to unrestricted mode.
- [x] 4.2 Run real guard, network, policy and setup-runtime suites plus the installed qualification operation on the available WSL target; verify the production path, stale-report rejection and both restricted modes without real credentials or model requests.
- [x] 4.3 Exercise native Linux qualification if an environment is available and record the actual kernel/engine/backend/LSM and outcomes in `docs/validation.md`; if unavailable, record that limitation without creating an exhaustive platform-matrix completion dependency or claiming a native pass.
- [x] 4.4 Reconcile implemented admission/evidence terminology with all affected docs/spec scenarios and update only N19 in `todo.md`; verify the measured WSL record remains historical evidence, missing required local checks remain blocking and N01/N20-N25 are not marked complete by this change.

## Workflow follow-up

- Synchronize and archive N18 before merging N19's network-egress delta, or otherwise verify both independent requirement additions are retained during synchronization.
- Synchronize and archive N19 after implementation review; retain separate local qualification, release regression and authenticated evidence.
