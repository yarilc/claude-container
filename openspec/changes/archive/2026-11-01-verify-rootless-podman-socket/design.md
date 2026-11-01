# Design

## Context

See `proposal.md` for motivation. `claude-container.sh` resolves a fixed socket and checks `-S` only inside the exact-value opt-in branch, before image operations. Both Claude and shell modes use the same socket mount and container `CONTAINER_HOST`. The README already offers a manual remote `info` check, but startup does not enforce it. There is no test framework.

The reference [Antigravity wrapper](https://github.com/yarilc/antigravity-container/blob/main/antigravity-container.sh), inspected on 2026-11-01, separately checks its outer engine and queries its selected socket for rootless status and a host socket path. This change adopts only the selected-service rootless verification. The existing capability's enabled-success scenario must gain a verified-service precondition; conditional validation must explicitly exclude service queries when disabled.

## Goals / Non-Goals

**Goals:**
- Verify the service receiving wrapper-granted API authority rather than infer its privilege from a filename or caller UID.
- Make rejection explicit and actionable under `set -Eeuo pipefail`, before builds or launch.
- Preserve existing argument arrays, mount paths, and shared launch-mode policy.

**Non-Goals:**
- Adding unconditional validation of the engine used for outer container operations, Linux/transport restrictions, or remote-context rejection.
- Adopting Antigravity's configurable socket discovery, host socket remapping, or boolean parsing.
- Changing the image, API authority, persistence, or independently configured endpoints.

## Decisions

### Query the exposed socket explicitly

After the existing `-S` check, run `podman --remote --url "unix://$socket" info --format '{{.Host.Security.Rootless}}'`. The explicit URL targets the fixed socket that will be mounted, regardless of default connection selection. A plain `podman info` can describe a different engine; UID, path, and ownership checks cannot establish the service's privilege mode. Only the rootless field is needed: there is no socket-remapping change requiring `RemoteSocket.Path`.

### Accept only successful affirmative verification

Capture the command output in a checked assignment with an explicit `die` branch on command failure. Compare the captured value to exact `true` (command substitution removes trailing newlines). Reject `false`, empty output, and unexpected text rather than guessing. Keep Podman's stderr available for diagnosis. The wrapper error must include the socket and distinguish query failure (check service availability/permissions) from a non-affirmative result (use a rootless service under the intended non-root account). No JSON parser or additional dependency is needed.

### Keep the check conditional and before image operations

Place the probe within the existing `container_podman` branch, before `podman image exists` and `podman build`. Disabled access requires no service and issues no service query. Retain the missing/non-socket error and the `--container-help` early exit. One check before the shared launch arguments covers Claude, shell, build, and worktree combinations. Checking after a build would do unnecessary work before rejecting an enabled launch.

### Verify behavior using controlled service results

Use temporary executable Podman stubs on a filesystem that permits execution and a copy of the script, as repository guidance permits. Provide a controlled Unix socket fixture, isolating its path in the copied script if necessary, without replacing any real user socket. Record command order and argument boundaries; simulate successful `true`, `false`, query failure, empty output, and unexpected output. Verify the explicit remote URL and that failures reach neither image operations nor `run`. Disabled values must reach ordinary startup without the service probe, mount, or container `CONTAINER_HOST`. Do not require a real rootful service for negative tests.

## Risks / Trade-offs

- [Service unavailable despite an existing socket] → Fail before image operations and explain how to check/start the rootless API service; this is the intended stricter behavior.
- [One extra API request per enabled launch] → Restrict the query to enabled access and request one formatted field.
- [Socket replaced after verification] → This is a startup check, not socket identity pinning; retain the existing host-user trust boundary and avoid claiming ongoing attestation.
- [Outer engine and exposed API can differ] → Query the exposed service explicitly; outer-engine policy is unchanged and not attested by this check.

## Migration Plan

Ship the script, wrapper help, README, and AGENTS verification guidance together. Existing enabled users need a reachable service reporting rootless operation through the existing fixed socket; document a remote formatted `info` command and recovery instructions. Disabled users need no changes. No image rebuild or state migration is required for this change. Reverting restores the prior socket-existence-only validation and removes the new service guarantee.
