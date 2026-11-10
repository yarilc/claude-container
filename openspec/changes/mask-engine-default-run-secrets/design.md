# Design

## Context

See proposal.md (Why). Observed on the lab host (Podman 5.8, Rocky 9):

- **Without the mask**, `mountinfo` inside the container shows
  `.../userdata/run/secrets /run/secrets rw,... tmpfs`.
- **With `--mount type=tmpfs,destination=/run/secrets,ro=true`**, it shows a
  single `/ /run/secrets ro,nosuid,nodev,relatime tmpfs`, and the directory
  is empty. Podman skips its subscription mount when a user mount targets the
  same destination.

`network/guard.c` `verify_mount_layout()` reads only the mount point (field 5)
of each `mountinfo` line. Below `/tmp/`, `/run/` and `/var/tmp/` it allows
exactly `/run/sandbox-egress` (provider mode, verified separately) and a
regular-file `/run/.containerenv`, and fails on everything else. The guard
grants private socket creation on the three tmpfs roots. A nested writable
mount under them would let the agent place sockets in host-backed storage,
here the container's `userdata` on the host.

## Goals / Non-Goals

**Goals:**
- Start restricted sessions on hosts with a default secrets mount, without
  host changes.
- Keep the nested-mount rule fail-closed. The only new exception must be
  incapable of holding or accepting sockets.
- Stop exposing host subscription certificates to the agent and the proxy.

**Non-Goals:**
- Other `mounts.conf` entries, which would still be rejected by the guard, an
  explicit and visible failure.
- The qualification fixture containers (peer and control), which run no
  guard and no agent code.

## Decisions

### Mask with an empty read-only tmpfs instead of tolerating the default

The wrapper adds `--mount type=tmpfs,destination=/run/secrets,ro=true` to
the common agent arguments (every mode, shell and worktree included).
`network/session.py` adds the same to the proxy. Podman then omits its
default secrets mount.

- Alternative: allow the default `/run/secrets` in the guard. Rejected. It is
  writable and host-backed, which is the exact IPC risk the check exists for,
  and it would also leak the subscription certificates.
- Alternative: an empty user `mounts.conf`, or `--default-mounts-file`.
  Rejected. The first is a host configuration change, and the second is a
  global client flag that a remote service ignores.

### Guard admits only a read-only tmpfs at `/run/secrets`

`verify_mount_layout()` also parses the per-mount options (field 6) and the
filesystem type (the first token after ` - `). It continues past
`/run/secrets` only when the first option is `ro` and the type is `tmpfs`.
Otherwise the existing `nested private IPC mount validation` failure applies.

A fresh tmpfs has no pre-existing sockets, and a read-only mount refuses new
sockets (`EROFS`) regardless of Landlock. The exception therefore adds no
reachable or creatable IPC endpoint. The guard revision string is unchanged:
an older guard paired with the new wrapper rejects the mask and fails closed.

## Risks / Trade-offs

- [A future Podman stops skipping its default mount when a user mount
  targets the same path] Two mounts appear, the writable one is rejected and
  startup fails closed with the existing diagnostic. A runtime test on such a
  host would show it.
- [A tool expecting writable `/run/secrets`] None is known in the image. If
  one needs it, it fails visibly with a read-only filesystem error.

## Migration Plan

1. Land the change and rerun setup with refresh: the guard is recompiled and
   the installation requalified.
2. Rollback: revert. Hosts with the default secrets mount fail again at the
   guard.
