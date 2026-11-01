# Design

## Context

See `proposal.md` for motivation. The Bash wrapper validates launch context before engine queries, prepares shared or isolated state, builds from its physical script directory, then assembles container arguments. Current gaps are localized: `unix:///*` accepts `/` as the entire endpoint path; disabled delegation has no environment-removal argument; only `/tmp` and `/run` are explicit; and `umask 077` remains active after state setup. There is no `.containerignore`, and the Containerfile has no `COPY` or `ADD` instructions requiring repository contents.

Existing synthetic tests capture Podman argv and validate private state on native storage. Runtime tests and `tests/run-runtime.sh` supply synthetic state and preserve host absolute paths. Earlier validation records report an unavailable engine; exploration subsequently observed a reachable Linux rootless Unix service and an existing image, with client 4.3.1 and server 4.9.3. Those observations establish prerequisites only, not runtime acceptance.

## Goals / Non-Goals

**Goals:** Make endpoint validation, environment removal, temporary storage, umask scope, and build inputs deterministic. Keep checks observable with the existing synthetic and opt-in runtime layers.

**Non-Goals:** Do not enforce a container process umask, claim internal sandbox compatibility, broaden authority, or introduce settings for these defaults. Do not modify the main specifications during implementation; the change deltas are synchronized through the normal later workflow.

## Decisions

### 1. Reject malformed explicit launch endpoints before any Podman invocation

After scheme validation, require an absolute Unix path containing a non-slash pathname component; reject `unix://`, `unix:///`, and slash-only variants. This is syntactic validation, not a new local socket accessibility check: the launch engine query remains responsible for checking a valid endpoint. Keep local operation with unset/empty `CONTAINER_HOST`, remote-context rejection, and side-effect-free help. An independent delegation override cannot rescue an invalid launch endpoint.

Alternative: rely on Podman's query failure. Rejected because it delays a predictable configuration error and makes diagnostics engine-dependent. Requiring a separate launch `-S` check is unnecessary for this scope.

### 2. Remove defaults from the session environment, not the host client

Add `--unsetenv CONTAINER_HOST` only to disabled-delegation container arguments. Enabled delegation retains its explicit `--env CONTAINER_HOST=unix:///run/podman/podman.sock` and verified socket bind. Never unset the wrapper's host environment: an explicit Unix launch endpoint is still needed by image and lifecycle commands. Do not broaden this change to other connection variables.

Alternative: set an empty container value or change the stock image's ENV. Rejected because the contract requires absence and must work with custom images and engine defaults.

### 3. Provision three constrained temporary mounts

Set `--read-only-tmpfs=false`. Keep `/tmp` at 256 MiB and `/run` at 16 MiB; explicitly add `/var/tmp` at 256 MiB. All three retain `rw,nosuid,nodev,noexec`; specify mode `1777` for `/tmp` and `/var/tmp` so the caller can write and sticky semantics are explicit. Keep existing `/run` permission behavior and delegated socket composition. Do not add `/var/log` or additional writable system paths.

The `/var/tmp` limit is a proposed default matching `/tmp`, not an observed existing guarantee. It makes the additional writable storage bounded without adding a configuration surface. This also tightens direct execution from `/var/tmp` compared with any permissive automatic mount.

Alternatives: leave `/var/tmp` read-only, retain automatic mounts, or enable execution to help internal sandbox startup. Rejected because the backlog requires writable explicit `/var/tmp`, predictable mounts, and retained execution restrictions.

### 4. Apply umask only inside state directory creation

Use a small directory-creation helper whose subshell runs `umask 077` and `mkdir -p --` on its arguments. Use it for shared Claude/OpenSpec paths and isolated home/configuration paths. Keep resolved-path checks in their current order, especially before creating isolated children, and retain validation and actionable failures. Paths needed later remain resolved in the parent shell. Existing directories are not chmodded or repaired.

Alternative: save and restore the process-wide umask around the entire setup block. A subshell makes restoration unconditional and narrows inheritance without extra failure-path handling. Do not add `--umask`: actual runtime process/file modes are a separate observation, not an effect promised by host directory creation.

### 5. Default-deny repository build inputs

Add `.containerignore` excluding all entries, with explicit exceptions for `Containerfile` and `.containerignore`. The current recipe needs no other local files. This excludes arbitrary isolated state names and future unrelated files without maintaining a list of credential filenames. Keep both existing build calls using the physical script directory, so the filter applies consistently to automatic and explicit builds.

Alternative: denylist `.git`, `.claude`, `.test-state`, `.env`, caches, documentation, and similar paths. Rejected because it would miss custom state directories and new sensitive files. Future intentional local build inputs must be added explicitly with their build recipe changes. This filter controls build inputs; it does not alter workspace mounts or sandbox authority.

### 6. Verify behavior at the layer that can establish it

- Extend fake-Podman tests for early rejection with zero Podman calls, valid launch contexts, disabled-value environment removal, enabled delegation, all three tmpfs arguments, and state directory privacy. Capture the fake client's process umask under caller masks `0022` and `0002`, covering build, create, and subsequent lifecycle calls in both state modes. Preserve the existing mode-composition matrix rather than duplicating it.
- Extend runtime checks in both state modes to inspect actual mount flags, sizes, and temporary directory modes; exercise caller writes, direct execution denial using a copied executable, and disappearance across sessions. Check `/run` mounts without assuming its root must accept arbitrary caller writes. Record container `umask` and file/directory modes on native writable state separately from host umask assertions.
- Build a uniquely tagged disposable image derived from the existing runtime image that defines a synthetic `CONTAINER_HOST`. In shell mode, distinguish an absent variable from an empty one and verify enabled delegation overrides the inherited default. Check that disabled sessions have no delegated socket. Keep host Unix engine access functional throughout.
- Test the actual ignore policy with a disposable synthetic context at a host-resolvable path. Copy the policy into it, add representative sensitive/nested/unrelated sentinels, and use a fixture Containerfile based on an existing local image with `COPY .` to inspect what reached the build. Do not simulate ignore semantics with a custom pattern parser. Do not submit real repository credentials to the builder. The fixture verifies filtering; a normal runtime image build separately verifies the production recipe still works.
- Use unique owned tags/containers and cleanup handlers for fixtures. Integrate real-engine checks with the existing opt-in runner so native state and original absolute bind paths remain valid. A missing prerequisite is recorded as unavailable, not a pass.

## Risks / Trade-offs

- `/var/tmp` now has a bound and `noexec` -> Document the compatibility change and verify native startup/tool smoke under the retained restrictions; do not relax policy automatically.
- Client/server versions may differ -> Verify argument acceptance and actual environment/mount behavior against both reported versions and record them.
- Restrictive context filtering can hide future intended inputs -> Document the allowlist next to build instructions and validate the real production build after policy changes.
- Synthetic argv tests cannot prove engine defaults were removed or mounts enforced -> Require the targeted real-engine checks above and preserve failed/unavailable results in the validation record.
- Narrowing host umask may expose assumptions in external commands -> Preserve the caller's policy and test observed inheritance; keep credentials private through scoped creation and existing validation.
- Runtime prerequisites can change between planning and implementation -> Recheck service, image, storage permissions, and host path visibility before acceptance. Preserve historical validation entries with dates rather than replacing them with inferred success.

## Migration Plan

No credential migration or state conversion is required. Update the wrapper, ignore policy, tests, and documentation together. Validate both automatic and explicit builds, then run synthetic and opt-in runtime suites with disposable state. Record results before closing implementation tasks. Main-spec synchronization and archive remain separate actions.

Rollback consists of reverting the implementation changes together; it does not delete user state. Reverting removes the stricter endpoint/environment guarantees and restores reliance on automatic temporary mounts, so describe those effects if rollback is needed. Existing runtime images do not need a rebuild for wrapper mount/environment changes; verify a fresh build to accept the new build-context policy.
