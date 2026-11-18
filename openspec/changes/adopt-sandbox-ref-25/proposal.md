# Proposal

## Why

`sandbox-ref-25` (change `verify-delegated-socket-path` in `sandbox-container`) stops the launcher from mounting a delegated service's reported host socket path when that path is the root directory or a path the wrapper sees as something other than a socket. Claude runs on `sandbox-ref-24`, so a misbehaving service on the delegation endpoint could still make it bind the host root, or another visible directory, read/write into a session.

## What Changes

- Adopt `sandbox-ref-25` from `sandbox-ref-24` with `tools/propagate.py`. This copies `launcher/core.sh`, `setup/setup.py`, `tests/test_launcher.py` and `tests/test_setup.py`, rewrites the tag references in `docs/network-contract.md` (5), and moves the `tests/test_reference_copy.py` manifest to the tag.
- With delegation enabled, a reported host socket path made only of slashes, or one that exists in the wrapper's namespace as a non-socket, stops the launch before image operations. A path the wrapper cannot see is still accepted as the remapped socket of a containerized wrapper. Guided setup applies the same checks.
- The parity table rows are fixed by hand; Claude's row names `sandbox-ref-25` after validation and is copied into the other repositories.
- No Claude file changes besides the copied shared files, the manifest, the documents and the validation record.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-podman-access`: "Exposed Podman service must report rootless operation" refuses a slash-only reported host socket path and an existing non-socket path, and names the remapped limit.

## Impact

- **Code:** shared files only (`launcher/core.sh`, `setup/setup.py`) and their shared tests.
- **Qualification:** the installed core and setup change, so installations rerun `--container-setup`; the operator runs it on the three reference hosts.
- **Behavior:** a legitimate rootless service is unaffected; a delegated launch whose service reports a slash-only or visible non-socket path now stops.
