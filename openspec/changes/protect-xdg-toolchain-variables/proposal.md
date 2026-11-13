# Proposal

## Why

The OpenCode wrapper places all of its state under `/opencode-home` by
setting `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME` and
`XDG_STATE_HOME` in every session. Its launcher treats those names as
authoritative and never forwards host values for them.

The shared toolchain module (`setup/toolchains.py`, `sandbox-ref-13`)
protects identity, shell, runtime, proxy, CA and wrapper variables, but not
the XDG base-directory variables. When the OpenCode launcher adds the default
toolchain environment, Podman keeps the last `--env` for a name (checked on
this host: `--env XDG_DATA_HOME=/wrapper --env XDG_DATA_HOME=/toolchain`
yields `/toolchain`). A default toolchain recipe that sets an XDG variable
would therefore move OpenCode's configuration, credentials or history to
another directory in new sessions, without any error.

This was found while planning the OpenCode adoption. It is a defect of the
shared rule, so it is fixed here under a new tag before OpenCode adopts the
library.

## What Changes

- `setup/toolchains.py` protects every variable whose name starts with
  `XDG_`, in recipe validation (`add`) and in `launch-env`. This covers
  `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME`, `XDG_STATE_HOME`,
  `XDG_RUNTIME_DIR` and the `XDG_*_DIRS` search paths.
- `tests/test_toolchains.py` (shared) covers the rejection in `add` and in
  `launch-env`.
- The README "Toolchains" section lists XDG variables among the protected
  ones.
- Tag `sandbox-ref-15`. The qualified shared code changes, so restricted
  installations rerun `--container-setup` after adopting it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `toolchain-library`: a new requirement names the session variables a
  toolchain cannot set, including the XDG base-directory variables.

## Impact

- `setup/toolchains.py`, `tests/test_toolchains.py`, `README.md`,
  `docs/validation.md`, `docs/network-contract.md` (parity cells).
- Wrappers: OpenCode, Pi and Antigravity adopt `sandbox-ref-15` directly with
  the library. Codex, already on `sandbox-ref-14`, adopts it through a small
  change of its own.
- A toolchain already installed with an XDG variable would make `launch-env`
  fail with a protected-variable error. This is unlikely, because no example
  recipe sets one, and the operator fixes it with `remove` and `add`.
