# Tasks

## 1. Setup entry point and interactive choices

- [x] 1.1 Add standalone `--container-setup` dispatch before runtime option validation and state creation, preserving help precedence; verify PTY setup works with invalid provider defaults and missing images while mixed arguments and nonterminal setup fail without mutations.
- [x] 1.2 Implement the host-side standard-library questionnaire with reviewed existing defaults, conditional account/API questions, network/state/path choices and advanced CA/YOLO/worktree/delegation options; verify PTY transcripts cover defaults, input retries, cancellation and restricted/delegation conflict resolution without automatic broadening.
- [x] 1.3 Document the new entry point, terminal/Python requirements, plain-language choices and conservative defaults in wrapper help and the README; verify help works without Podman or preferences and the first-run example matches the interface.

## 2. Prerequisite checks and user Podman service

- [x] 2.1 Implement read-only Podman/rootless/dependency/platform diagnosis, reusing strict engine-response and selected-mode checks; verify fake engines cover missing Podman, rootful/non-Linux/malformed results, unsupported contexts and unsupported restricted platforms before image operations.
- [x] 2.2 Add exact-endpoint reuse and explicitly confirmed systemd user socket enable/start with post-start verification; verify command logs cover accepted/declined activation, manager failure, unreachable/rootful sockets, explicit endpoint precedence and no enablement when unrestricted local launch needs no service.
- [x] 2.3 Implement the no-systemd/manual-service recovery output and persistent-change reporting; verify fixtures never invoke sudo, package managers, lingering, account-map edits or unmanaged daemon backgrounding, and document recovery from a missing user bus/runtime directory.

## 3. Protected installation and repeatable activation

- [x] 3.1 Define a complete explicit source manifest and create native versioned candidate releases with protected path/ancestor/overlap checks and private state/runtime directories; verify synthetic Windows-source/native-target installation, missing inputs, unsafe ancestors, escaping symlinks, ignored permissions and workspace/state overlap without recursive repairs or credential copies.
- [x] 3.2 Add a per-installation update lock, owned temporary-resource tracking and atomic current-release/command publication with rollback; verify concurrent setup, first-publication failure, cancellation and interruption preserve the last working release and unrelated command files, containers and state.
- [x] 3.3 Support review/reuse of an existing managed release and coexistence with a safe flat manual installation; verify unchanged reruns reuse suitable artifacts and document release layout, stale-lock recovery, retained versions and explicit rollback.

## 4. Reviewed mode-specific maintenance

- [x] 4.1 Generate and confirm a concrete filesystem/image operation plan after engine verification; verify declining the plan causes no pull/build/activation and summaries accurately report any separately approved user-service change.
- [x] 4.2 Orchestrate runtime image preparation/reuse with distinct candidate tags and recorded image identities; verify absent-image versus inspection-error handling, failed builds, refresh consent, subsequent authorized `--container-build` and preservation of the previous release's runtime reference during failed setup.
- [x] 4.3 For restricted modes, acquire exact recipe inputs as approved maintenance, prepare/reuse the pinned immutable toolchain and run guard packaging to native storage; verify compilation uses network none, static ELF/manifest checks pass and unavailable inputs or altered digests prevent activation without changing pins.
- [x] 4.4 For provider mode, prepare/reuse the proxy, inspect its immutable identity and validate the selected packaged account/API policy plus private runtime paths; verify offline/unrestricted skip irrelevant components and fresh provider setup cannot retain a missing mutable proxy tag.
- [x] 4.5 Scope exact maintenance authorization to approved preparation subprocesses; verify smoke/login and generated launch defaults receive no persisted setup maintenance grant, and document host build-network exposure and mode-specific artifact preparation in the README/network guide.

## 5. Saved preferences and managed launcher

- [x] 5.1 Implement strict versioned non-secret JSON preferences with protected ownership/mode/ancestor validation; verify unknown schemas/fields, malformed values and credential fields fail closed and no environment dump, shell sourcing or eval is used.
- [x] 5.2 Generate the managed command and isolated launch helper, applying saved defaults only for absent runtime variables and deriving default runtime socket paths at launch; verify new-terminal use, explicit empty overrides, spaced/empty arguments, stdin/cwd/TTY/status/signal preservation and direct-wrapper compatibility.
- [x] 5.3 Enforce installation/preferences protection against effective workspace/worktree/state mounts on every managed launch, including unrestricted mode; verify future parent-workspace overlap and environment conflicts fail before image operations or launch.
- [x] 5.4 Wire managed setup reruns and help precedence, including help with corrupt preferences or absent Python/Podman; verify saved choices reappear on rerun and document PATH guidance, override precedence, worktree-default reversal and direct-wrapper invocation without shell-profile edits.

## 6. Readiness and authentication assistance

- [x] 6.1 Implement bounded credential-free smoke checks through the candidate's actual installed wrapper, with effective state/CA settings and real restricted guard enforcement; verify enforcement/preflight/engine failures prevent activation while both CA states and all selected network modes produce accurate readiness results.
- [x] 6.2 Offer explicitly accepted account login through the configured sandbox after activation, preserving shared credentials or fresh isolated state; verify synthetic login/status success, cancellation/failure and absent API-key paths without credential copying, secret capture, automatic model calls or policy expansion.
- [x] 6.3 Emit separate sandbox/authentication states, completion/rerun commands and outstanding actions; verify ready-with-authentication-pending is explicit and sandbox failures return nonzero, and document account/API/offline completion examples with their actual verification scope.

## 7. Integration acceptance

- [x] 7.1 Run the synthetic setup/PTY suite together with `python3 -m unittest discover -s tests -p test_wrapper.py -v`, changed-shell `bash -n`, `git diff --check` and strict change validation; verify every setup requirement has corresponding passing coverage or a named opt-in acceptance check.
- [x] 7.2 Exercise fresh setup, new-terminal launch, unchanged rerun, failed update/rollback and offline/provider enforcement on the measured rootless WSL target using disposable native installation/state; record versions and pass/fail/unavailable results in `docs/validation.md` without changing real credentials or user-service settings implicitly.
- [x] 7.3 Verify explicitly approved systemd user activation or reuse of the real same-host service, plus account reuse/fresh-login assistance when credentials are available; record unexercised real service/authentication variants as unavailable and keep any real API-key request optional without claiming authenticated model success from smoke checks.

## 8. Adversarial review corrections

- [x] 8.1 Protect the actual invoked launcher and every symlink hop, upgrade legacy dispatchers and retire obsolete managed commands transactionally; verify command migration, rollback, alias chains, dot-dot paths and unchanged physical entries in synthetic tests plus real WSL command relocation.
- [x] 8.2 Clean up owned process groups even after leader exit or pipe closure; verify timeout regressions terminate and reap descendants, preserve the primary failure and leave no test zombies.
