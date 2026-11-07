# Design

## Context

See `proposal.md` for motivation and the delta specifications for the observable contract. Today `claude-container.sh` parses wrapper flags, immediately validates network/state options and then verifies the engine. There is no preferences store or setup dispatch. The README's installation commands manually copy runtime helpers, compile a guard, build images and export provider settings. `network/build-guard.sh` requires a prepared immutable toolchain and an existing native output directory; `network/control.py` validates trusted inputs, a static guard, manifest and effective mount overlap. The build-context allowlists intentionally exclude most checkout files.

The accepted restricted target remains WSL Linux 6.6.87.2 x86_64, Landlock ABI 3, the measured rootless Netavark service and existing standard OCI policy. This change simplifies preparation; it does not extend that support matrix. Account login, reuse and expired-token refresh have manual evidence; a real API-key check remains optional/unavailable. Neither a setup success nor a version command upgrades that evidence.

## Goals / Non-Goals

**Goals:**

- Make a fresh supported host usable through one interactive command, a reviewed preparation phase and one generated launcher.
- Separate prerequisite diagnosis, host maintenance, runtime confinement and authentication status.
- Preserve a working installation across failed updates and make choices repeatable without shell-profile edits.

**Non-Goals:**

- Installing host packages or changing account mappings, WSL init, lingering, root/system services or host security policy.
- Adding a noninteractive provisioning API, arbitrary provider-policy editor, automatic credential migration or background service manager.
- Automatically testing paid model requests, widening network policy on login failure, or adding support for unverified kernels/backends.

## Decisions

### 1. Dispatch setup before runtime initialization

Keep the Bash entry point and introduce a separate host-side Python 3 standard-library setup module, provisionally `setup/setup.py`. The wrapper recognizes help first; then it accepts setup only as a standalone operation. Dispatch uses the script's physical directory and isolated Python mode before network-variable parsing, state creation, image checks or ordinary application argument forwarding. Absence of Python is an actionable setup prerequisite; unrestricted direct invocation retains its current dependency contract. Help never imports the setup module or reads managed preferences.

This isolates interactive orchestration from the established runtime lifecycle. Adding prompts inside existing runtime checks would make ordinary pipelines and first-run failures unpredictable. Require terminal stdin/stdout and use normal terminal input; no yes-to-all or piped-answer mode in this change. A PTY test drives the actual interface.

### 2. Use a staged questionnaire and explicit review

The setup flow is:

1. Read-only prerequisite diagnosis and discovery of an existing managed installation.
2. Collect intended workflow and paths, then validate compatibility before mutation.
3. If a required engine endpoint cannot yet be queried, offer the separately confirmed user-service preparation; reverify the selected engine afterward.
4. Show the full installation/build plan and obtain maintenance/filesystem consent.
5. Prepare a candidate installation and selected-mode artifacts, run its smoke checks, then activate it.
6. Offer account login and present separate sandbox/authentication results.

The questionnaire uses ordinary language and skips irrelevant questions. First-run setup defaults to provider mode with account authentication; online choices explain account-restricted, API-restricted and unrestricted operation. Account use does not depend on an API key. Shared state, disabled delegation, disabled YOLO, current workspace only and disabled host CA trust preserve existing defaults. Advanced choices include isolated native state, an existing private Claude configuration, parent-directory worktree exposure, CA bundle, installation/command paths and existing Unix endpoint. Existing saved settings, including explicit offline mode, become reviewed rerun defaults. The direct wrapper retains its existing offline default when no managed preferences apply. Ambient runtime variables are displayed as potential conflicts rather than silently persisted; confirmed questionnaire choices control preparation. Smoke checks run without ambient overrides so they validate the saved plan.

Permission bypass and worktree scope remain independent choices, with their respective approval and writable-parent implications. Delegation is offered only with unrestricted networking; a conflicting selection returns to an explicit choice. The CA question reuses the existing opt-in single-file contract. Setup never fixes existing directory modes recursively or silently clears a nonempty `CLAUDE_CONFIG_DIR` conflict.

### 3. Enable only a verifiable user socket

Check Podman availability first. Reject root execution, named/remote contexts and unsupported endpoints consistently with the wrapper. For unrestricted local operation with delegation off, a service is unnecessary. Restricted operation requires the existing explicit same-host Unix service; delegation also requires its exact separately selected endpoint to be verified.

Prefer a user-selected reachable endpoint. Otherwise check for an accessible systemd user manager and offer `systemctl --user enable --now podman.socket`, showing its persistent effect and the destination. Verify the resulting service through the exact Unix URL using the existing strict response/engine checks. Socket existence or a successful systemctl call alone is insufficient. Preserve true host paths and reject ambiguous remapping rather than assuming that a visible Unix socket proves same-host operation.

Without a working user manager, reuse an already running verified service or print the existing foreground `podman system service --time=0` procedure and runtime-directory requirements. Return incomplete until the user supplies a working endpoint and reruns setup. Do not invoke sudo, create root-owned `/run` hierarchies, enable lingering or start an unowned background daemon. This supports non-systemd hosts with an existing service without introducing a second service supervisor.

Service changes can be needed before the final image plan is known; they therefore get their own consent. On subsequent cancellation, report an enabled socket instead of undoing a user-approved persistent service or stopping a service used elsewhere.

### 4. Install versioned candidates in native protected storage

Default installation root: `$HOME/.local/lib/claude-container`; default command: `$HOME/.local/bin/claude-container`. A root contains `releases/<unique-id>/` and an atomic `current` pointer. Each candidate includes runtime and setup helpers, recipes/build-context filters, policy inventory, guard sources/headers/build script and, when required, the compiled guard and digest manifest. An explicit source manifest prevents omissions such as the earlier guard digest failure and excludes checkout credentials, tests, Git metadata and unrelated files. Installation can copy from a `/mnt/...` checkout; native outputs and host build bind sources retain their real absolute paths.

Create protected directories privately and validate caller/root ownership, ancestors, symlink targets, Unix permission enforcement and disjointness from selected workspace/worktree/state. An existing flat installation can remain in place while managed releases are added if the root is safe; do not overwrite its files. Reject symlinks or unexpected files at reserved managed control paths. Use a per-installation atomic lock with owned cleanup and a clear stale-lock recovery diagnostic. A second setup must fail safely instead of racing activation.

Candidates reside at their final release path before validation, so absolute references do not become stale on promotion. Each contains its own versioned preferences. The managed command delegates to the release selected by `current`; activation changes one pointer after smoke success. On first installation, command publication is also checked and failures restore the previous pointer or leave no active first release. Never overwrite an unrelated command at the chosen path. Keep the previous release available for rollback and existing sessions; do not garbage-collect it automatically.

Updating files in place was rejected because a failed copy/build could invalidate the current guard/manifest pair. Installing under a workspace was rejected because an application could alter future launch policy.

### 5. Reuse pinned recipes and authorize maintenance narrowly

Produce an operation plan after inspecting the selected verified engine. Every mode needs a runtime image. Offline adds a toolchain when compilation is necessary and the protected guard. Provider additionally needs the proxy image, selected packaged profile and private runtime directory. Unrestricted does not need a guard/toolchain/proxy. Reuse valid artifacts by inspected identity; refresh only on explicit approval. Give each candidate a distinct managed runtime image tag, tagging a reusable inspected image or building a fresh one without retagging the active release. Save its inspected identity as provenance and the proxy's immutable ID as its runtime reference. This preserves rollback across failed setup builds while keeping the wrapper's explicitly authorized `--container-build` usable with a named runtime image. A subsequent direct build is deliberate maintenance outside setup's release transaction.

For fresh restricted setup, acquire the exact base references from the existing recipes, prepare the pinned toolchain, resolve its immutable ID and call `network/build-guard.sh` with exact maintenance authorization and native output. Compilation remains network-free. Prepare the runtime and proxy through explicit host build operations rather than launching an incidental `--container-build --container-shell` session. Copy required build inputs into the protected candidate with the existing restrictive context filters. Inspect results, validate manifests/static ELF/policy and record non-secret artifact identities.

No compiler is installed on the host. Do not change pinned package versions or policy inventories to recover from unavailable upstream inputs; report the stage and instructions. The user review explains that pulls, toolchain package acquisition and build RUN steps use host maintenance networking outside session egress controls, even if offline mode is selected. Scope `CLAUDE_CONTAINER_MAINTENANCE=1` to preparation subprocesses; remove it from the smoke/login environment and never save it. Existing ordinary build authorization remains unchanged.

### 6. Keep preferences declarative and confined

Each release holds a private `setup.json` with a strict schema version and an allowlist of non-secret fields: mode, authentication method/profile, physical paths, endpoint selection, runtime image tag/recorded ID, immutable proxy ID, CA opt-in/bundle, delegation, YOLO and workspace scope. Files use mode 0600, directories 0700, with all ancestors protected. Reject unknown schema/invalid fields and credential fields. Do not serialize the environment wholesale, source shell configuration or use eval. A small fixed Bash dispatcher invokes an isolated Python launch helper that loads validated JSON and execs the installed Bash wrapper with an explicit environment and argv. For help, the dispatcher invokes wrapper help directly before requiring Python or reading preferences.

Runtime defaults are applied only to variables absent from the caller environment; presence, including an empty value, is an explicit override. Existing validation rejects incompatible effective combinations. Never persist API keys, OAuth tokens, maintenance authority or raw authentication output. Derive a default user socket from the current runtime directory at each launch; persist an absolute endpoint only when explicitly selected. A reboot must not reuse an obsolete session-specific default path blindly.

The managed launcher validates effective writable mounts against its installation/preferences on every launch, including unrestricted mode, before executing untrusted code. Selecting a future workspace/worktree parent that contains managed files fails with relocation guidance. It preserves cwd, stdin, empty/spaced arguments, signals and wrapper terminal behavior through exec. Saved worktree scope injects only the existing wrapper flag; returning to current-directory scope uses rerun setup or direct wrapper invocation. Existing wrapper options remain available. Environment defaults are documented alongside the direct-wrapper escape path; the checkout wrapper itself does not automatically load global preferences.

Managed `--container-setup` bypasses launch defaults and reopens the questionnaire using saved choices. Managed `--container-help` bypasses preference loading so help works with corrupt/missing preferences and absent runtime prerequisites. Do not edit shell startup files; report the absolute command and how to add its directory to PATH if needed.

### 7. Validate the sandbox before offering authentication

Run candidate protected-path/state/CA checks and invoke its installed wrapper in shell mode with a fixed credential-free smoke program from the intended workspace. Restricted checks must reach the actual guard-enforced application path, verify the configured loopback/proxy environment and ensure direct external connection attempts fail; ABI query or `--version` alone is insufficient. Reuse the established guard checks rather than introducing a weaker setup-only backend. Do not send paid model requests or conflate synthetic checks with authenticated compatibility. Apply bounded timeouts to diagnostic calls and smoke checks, preserving existing session cleanup/exit handling; builds can run normally until cancellation.

Publish the candidate only after the sandbox smoke succeeds. Then offer `auth login --claudeai` through the configured installed wrapper for an account user who needs it. Shared state can reuse existing credentials; isolated state starts fresh. Let Claude own login display and credential persistence; the setup layer does not capture or log codes, URLs, tokens or credential files. Optional non-billable CLI authentication status can be reported as such, with its exact scope. Login cancellation/failure leaves a functioning sandbox installed with authentication pending. API mode never prompts for a secret or requires a key to prepare images; explain the current runtime environment-key mechanism. Offline mode reports provider authentication as not applicable.

Completion has two axes: sandbox ready/incomplete and authentication verified/pending/not applicable. Exit zero only for a successful sandbox preparation, even if authentication remains pending; failures before activation return nonzero. Completion includes selected boundaries, resolved command, rerun command, persistent service changes and next authentication action. Do not claim a model request was verified unless the user explicitly performs one separately.

## Risks / Trade-offs

Adversarial review corrections: the dispatcher identifies its actual entry path
to the launch helper. A component-by-component resolver preserves kernel
symlink/dot-dot semantics and validates every link against writable mounts;
checking only the configured path or final target is insufficient. Setup
upgrades recognized legacy dispatchers atomically and rejects normal legacy
launches without this entry information. Command relocation retires the prior
owned entry after publication, rolls back on failure, and compares resolved
entries to avoid deleting an unchanged command referenced through another path.
Rollback across this interface change requires a matching dispatcher/helper pair.

Timeout teardown addresses the owned process group independently of the leader's
exit state. After the graceful allowance it terminates residual descendants even
when they closed captured pipes. Isolated test subreapers collect orphaned test
descendants, making resource cleanup verifiable without relying on PID 1.

- [Restricted support is deliberately narrow] → Diagnose the measured platform early; never make unrestricted a hidden fallback. Keep unsupported environments actionable and incomplete.
- [Pinned upstream build packages may disappear] → Reuse prepared immutable artifacts when suitable; fail clearly rather than silently changing compiler inputs.
- [Source checkout trust] → Setup is an operator invocation of reviewed source; copying and hashing do not establish provenance. Keep it outside agent execution and preserve the existing protected-installation boundary.
- [Maintenance has persistent effects] → Consent precedes operations; report enabled sockets and created images on failure. Do not remove shared images or undo user-service changes automatically.
- [Saved choices can conflict with future workspaces or overrides] → Revalidate effective paths and settings on every managed launch and preserve direct invocation.
- [Atomic release management adds files and retained versions] → Keep the state machine small, retain the previous working release and document rollback instead of automatic pruning.
- [Authentication cannot always be completed during setup] → Publish separate readiness states and exact next commands; preserve account support without API-key dependencies.

## Migration Plan

1. Add setup dispatch and host helpers without changing ordinary direct invocation defaults. Add isolated synthetic/PTY tests before any real service mutation is exercised.
2. Make `bash ./claude-container.sh --container-setup` the primary documented first-run path, including checkouts on Windows mounts. Keep the manual setup as troubleshooting/reference.
3. Test an isolated fresh install and rerun on the measured WSL host, separately verifying systemd-user activation and existing-endpoint use. Exercise the no-systemd diagnostic path with controlled fixtures. Record unavailable real service cases honestly.
4. Existing manually installed wrappers remain usable. Users opt into the managed launcher; no credentials or shell profiles are migrated automatically.
5. Roll back by restoring the previously activated release pointer under the installation lock, or invoke the prior manual wrapper. Preserve state directories and report service enablement independently; no image deletion or credential restoration is required.
