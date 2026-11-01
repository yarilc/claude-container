# Design

## Context

See `proposal.md` for motivation. `claude-container.sh` currently shares the selected Claude configuration and host OpenSpec configuration, always allocates a TTY, and verifies rootless operation only for an enabled delegation socket. Its filesystem is read-only apart from workspace/configuration mounts and two `noexec` tmpfs mounts. There is no automated test suite.

The reference is `../antigravity-container/antigravity-container.sh` and its wrapper/runtime tests. Its validation record establishes results only for its own CLI and environment; its Google keyring and sandbox failure are not Claude requirements. The user explicitly chose to preserve shared `~/.claude` by default and make a dedicated home optional.

## Goals / Non-Goals

**Goals:** Fail closed on unverified engines and unsafe credential directories, provide a deliberate isolated-state mode, preserve explicit authority grants, and make isolation claims reproducible without real credentials.

**Non-Goals:** Change native Claude authentication, enforce a CLI permission policy against user arguments/settings, restrict network egress, encrypt application state, broaden privileges for nested sandbox compatibility, or change workspace/worktree selection or host CA semantics.

## Decisions

### 1. Preserve shared state and select isolation through an explicit directory

An unset or empty `CLAUDE_CONTAINER_STATE_DIR` preserves the current layout: `${CLAUDE_CONFIG_DIR:-$HOME/.claude}` mounted at `/claude-home/.claude` and `$HOME/.config/openspec` mounted at `/claude-home/.config/openspec`. `/claude-home` otherwise remains read-only in this mode. Do not create unused host cache/share directories.

A nonempty `CLAUDE_CONTAINER_STATE_DIR` selects an isolated home mounted read/write at `/claude-home`. Its `.claude`, `.config/openspec`, caches, and other home data persist there. Inside both modes, `HOME=/claude-home` and `CLAUDE_CONFIG_DIR=/claude-home/.claude`. In isolated mode, a nonempty host `CLAUDE_CONFIG_DIR` is an actionable configuration error: silently ignoring it or overlaying shared credentials would undermine the selected mode. Unset it when selecting isolation. The README recommends `$HOME/.local/share/claude-container/home` as an explicit directory; isolation does not create or select it automatically.

An automatic new default was rejected per the user's compatibility decision. Automatic copies, credential discovery, and shared OpenSpec overlays in isolated mode are excluded. A selected workspace or worktree parent can independently expose host files, including shared configuration; isolation describes mounts added for application state, not denial of files already in the selected workspace.

### 2. Verify state ownership and privacy in both modes

Use `umask 077`, create only selected directories, resolve their physical absolute paths, and require caller ownership and read/write/search access. Reject group/other permission bits on the shared Claude configuration directory or isolated home. In isolated mode, also validate an existing `.claude` directory and ensure application configuration paths resolve inside the selected home. Reject symlinks escaping that home; do not claim isolation while importing external paths. A symlink used to select the top-level state directory is allowed after resolution.

Do not recursively chmod, chown, or audit every historical credential file. Preserve existing host OpenSpec permissions in shared mode, since it is a compatibility mount rather than the credential boundary. Errors name the selected path and suggest explicit repair or native Linux storage. New privacy checks intentionally reject some previously accepted directories, including Windows-backed storage that ignores Unix modes.

### 3. Verify the launch engine separately from delegation

After argument/environment validation, query the actual launch engine for rootless status, OS, and remote-service status. Require affirmative rootless Linux results and reject failures or malformed output before image inspection/build/create. Reject `CONTAINER_CONNECTION`, TCP/SSH endpoints, and implicit remote contexts; allow local execution or an explicit absolute Unix `CONTAINER_HOST` on the same Linux host.

Launch-engine verification is mandatory even when delegation is off. With local Podman it requires no API socket. With an explicitly selected Unix launch service it necessarily queries that service, but grants no socket to Claude. This deliberately refines the current `container-podman-access` wording that forbids all API queries when delegation is off. Update that delta and repository guidance together rather than leaving contradictory promises.

### 4. Select and verify the exact delegation socket

Only exact `CLAUDE_CONTAINER_PODMAN=1` enables delegation. All other values remain disabled without errors. When enabled, endpoint precedence is:

1. Nonempty `CLAUDE_CONTAINER_PODMAN_SOCKET`.
2. Explicit absolute Unix `CONTAINER_HOST` used by the wrapper.
3. `${XDG_RUNTIME_DIR:-/run/user/<uid>}/podman/podman.sock`.

Require an absolute, accessible Unix socket and resolve its physical path. Query it explicitly with `podman --remote --url ... info`, requiring rootless `true` and an absolute service-reported `Host.RemoteSocket.Path`. Bind the reported host-side path to `/run/podman/podman.sock:rw` and set the container's `CONTAINER_HOST` accordingly. An enabled verification failure blocks even an explicit build. When disabled, do not inspect or query the delegation endpoint, even if its override is invalid.

The launch engine and selected delegation service must be on the same Linux host; workspace, state, CA, and build paths must exist there at their original absolute paths. Unix transport alone cannot establish host identity, so this is an explicit supported-environment precondition, exercised by runtime tests rather than a claim of remote-host detection. Do not silently retarget the launch engine to the delegation service. Named connections, Podman Machine, and remote TCP/SSH are outside the supported contract.

This replaces the fixed `/run/user/<uid>` requirement, retaining that path as the fallback when no override, Unix launch endpoint, or custom runtime directory is present. Documentation must explain that the socket permits additional host mounts beyond the workspace.

### 5. Retain standard security policies and separate permission concepts

Keep `--read-only`, `--userns=keep-id`, caller UID/GID, and the current `/tmp` and `/run` limits and `nosuid,nodev,noexec` flags. Preserve CA trust as an opt-in read-only single-file mount. Remove the shared OpenSpec mount's automatic `:z` relabel; do not disable SELinux labels, customize seccomp, add capabilities, or use `--privileged` to resolve failures. SELinux failures should remain actionable and require host policy configuration.

YOLO controls only addition of `--dangerously-skip-permissions`, independently of socket/state selection, and never applies to shell mode. Normalize case for existing YOLO and CA boolean forms; retain the exceptional exact-value socket policy. Do not import Google's keyring, executable `/tmp`, or its `sethostname` workaround. Neither wrapper currently provides an egress restriction; do not describe filesystem isolation as network isolation.

### 6. Own lifecycle explicitly

Preserve argument arrays and use `--interactive`; add `--tty` only when stdin and stdout are terminals, forwarding `TERM` by name only for a terminal session. Shell mode discards CLI arguments and YOLO injection. Resolve the wrapper's physical script location for builds, including symlink invocation. Keep current build caching behavior; distinguish image-exists success, documented absence, and inspection errors rather than treating all failures as absence.

Enumerate all names, handle numeric suffixes in decimal, and reserve a workspace-index name with `podman create`. Retry actual name collisions up to 20 attempts; preserve other errors. Track the returned container ID, attach with preserved stdin, forward INT/TERM/HUP, and clean up only that ID on exit. This follows the reference's ownership discipline and avoids interpreting an application exit code 125 as a naming collision. Keep temporary diagnostic files private and remove them on all exit paths.

### 7. Verify behavior with synthetic and real-runtime layers

Use Python standard-library tests with a fake Podman executable to cover exact argv, precondition ordering, both state modes, socket precedence/remapping, malformed queries, error propagation, name races, and signals. Keep stubs on executable storage. Add opt-in real rootless runtime tests and a disposable runner that preserves host absolute paths; use private native Linux state when the workspace cannot enforce permissions.

Runtime checks use sentinel files outside the selected mounts, write failures under `/usr`, caller ownership, temporary-file disappearance, state reuse, worktrees, and child binds through the delegated socket. Test all four YOLO/socket combinations without a paid request or host credentials. Record versions, environment, commands, and explicit passed/failed/unavailable outcomes in `docs/validation.md`. Basic `bwrap`/namespace probes cannot establish Claude's internal sandbox compatibility; an actual sandboxed tool operation and its output must be checked separately when a suitable authenticated session is available.

## Risks / Trade-offs

- [Existing credential directories are too permissive] -> Fail with a path-specific repair instruction; never change existing permissions recursively or fall back to weaker checks.
- [Isolation is optional] -> State clearly that default sessions still share Claude and OpenSpec configuration and can modify it.
- [Dedicated writable home increases persistent application storage] -> Keep it confined to the selected directory and test for absence of implicit host configuration mounts.
- [Socket delegation bypasses project-only access] -> Document this authority grant in help/README; retain explicit exact-value opt-in.
- [SELinux enforcing support is not established by the reference] -> Preserve standard policies, report the environment and results, and never label untested support as passed.
- [CLI authentication/session formats vary] -> Keep native storage behavior and manual migration; never use real credentials in automated tests or promise encryption.
- [Internal sandbox fails under standard policy or `noexec`] -> Record the concrete failing operation and versions; a required policy change needs a separate decision rather than an automatic privilege increase.

## Migration Plan

1. Default users retain `~/.claude` or `CLAUDE_CONFIG_DIR`, subject to owner/privacy validation. Repair permissions explicitly if required. The shared OpenSpec mount remains, without automatic relabeling.
2. To isolate, choose a private native Linux directory, unset `CLAUDE_CONFIG_DIR`, and set `CLAUDE_CONTAINER_STATE_DIR`. Start with fresh login/settings, or manually copy selected Claude/OpenSpec state into the corresponding subdirectories while sessions are stopped. Do not overwrite an existing profile or copy all host home data. Protect backups and recheck permissions after copying.
3. To return to shared mode, unset `CLAUDE_CONTAINER_STATE_DIR` and restore any prior `CLAUDE_CONFIG_DIR`. Isolated data is retained; startup does not merge or delete either profile.
4. Keep `CLAUDE_CONTAINER_PODMAN=1` for child-container workflows. Document endpoint selection changes and how an explicit socket override pins the former endpoint.
5. Update README/help and repository testing guidance with the implementation. Retain the prior image/script revision for rollback; do not rewrite application state during an image or wrapper upgrade.
