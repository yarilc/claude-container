# Proposal

## Why

On RHEL and Rocky hosts, Podman's `mounts.conf` contains
`/usr/share/rhel/secrets:/run/secrets`. Every container therefore receives a
**writable** tmpfs at `/run/secrets`, containing the host's subscription
certificates. On the Rocky 9 lab host the static guard correctly refuses that
nested mount under the private `/run` ("nested private IPC mount validation
failed (errno=1)"), so restricted setup cannot complete. The mount also exposes
host subscription material to the agent in every mode. The host must not be
modified.

Verified on the lab host: when the container already has
`--mount type=tmpfs,destination=/run/secrets,ro=true`, Podman skips its own
secrets mount. One empty tmpfs remains, mounted read-only.

## What Changes

- Every agent container (all modes, including shell, worktree and
  delegation) and every provider proxy is created with an empty read-only
  tmpfs at `/run/secrets`. This masks the engine's default secrets mount
  wherever one exists, and is harmless where none does.
- The guard's nested-mount validation accepts exactly `/run/secrets` when it
  is a `tmpfs` whose per-mount options are read-only (`ro`). A writable
  `/run/secrets`, any other filesystem type, or any other nested mount under
  `/tmp`, `/run` or `/var/tmp` is still rejected before agent code runs. A
  read-only fresh tmpfs can neither hold pre-existing host sockets nor accept
  new ones.
- Documentation explains the mask and its privacy benefit: host subscription
  certificates are no longer visible to the agent.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-isolation`: agent containers mask the engine's default
  `/run/secrets` with an empty read-only tmpfs.
- `network-egress`: the restricted bootstrap's private-runtime mount
  validation admits only that read-only mask.

## Impact

- `claude-container.sh` (agent container arguments) and `network/session.py`
  (proxy).
- `network/guard.c` (`verify_mount_layout`). This is shared code, so it is
  propagated to the sibling wrappers. The guard binary changes, so setup
  recompiles it and requalification follows.
- Tests:
  - `tests/test_wrapper.py`: mask present in every mode;
  - `tests/test_session.py`: proxy mask;
  - `tests/test_guard.py`: the read-only mask is accepted, while a writable
    `/run/secrets` and other nested binds are rejected;
  - the existing `test_network_runtime.py` nested-mount rejection still
    holds.
- `README.md` and `docs/network-contract.md`.
