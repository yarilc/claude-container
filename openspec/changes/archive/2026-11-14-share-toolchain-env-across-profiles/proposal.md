# Proposal

## Why

The toolchain library is one host directory shared by all five wrappers, so a
toolchain installed once must work the same way in every wrapper. Two defects
of the shared module (`setup/toolchains.py`, `sandbox-ref-16`) break that
contract. Both were found while porting the library to Antigravity.

- **A session variable outside the protected set.** The Antigravity launcher
  removes `DBUS_SESSION_BUS_ADDRESS` with `--unsetenv`, so a session never
  reaches a host bus. On this host's engine (Podman server 4.9.3),
  `--unsetenv` does not remove a value given with `--env`:

  ```text
  podman run --env DBUS_SESSION_BUS_ADDRESS=x --unsetenv DBUS_SESSION_BUS_ADDRESS … → x
  ```

  A default toolchain that sets the variable would therefore reach every
  Antigravity session. The other wrappers have no bus either, so the
  variable is useless in any session.
- **Protection depends on the wrapper that runs the command.** Besides the
  neutral names, the module protects the variables of the current wrapper's
  profile: its prefix (for example `ANTIGRAVITY_CONTAINER_`), its
  configuration and approval variables, and its credentials (for example
  `GEMINI_API_KEY`). A recipe that sets `GEMINI_API_KEY` is accepted by
  Claude's `add`. Afterwards, Antigravity's `launch-env` rejects the whole
  index, so no Antigravity session starts until the toolchain is removed.
  The shared code cannot name the other agents, because the alignment test
  forbids agent identifiers in shared files.

## What Changes

- `DBUS_SESSION_BUS_ADDRESS` joins the neutral protected set. `add` rejects a
  recipe that sets it, in every wrapper.
- The protected names split into two groups:
  - **neutral:** session identity, shell, runtime, proxy, CA, loader, `XDG_`,
    `SANDBOX_` and `DBUS_SESSION_BUS_ADDRESS`. `add` rejects them and
    `launch-env` fails on them, as today;
  - **profile:** the current wrapper's prefix, configuration, approval and
    credential variables. `add` still rejects them. `launch-env` no longer
    fails: it leaves the variable out of this wrapper's session environment
    and prints one warning naming the toolchain and the variable. The other
    variables and the library mount are unchanged.
- `tests/test_toolchains.py` (shared) covers the DBUS rejection, the skipped
  profile variable with its warning, and the neutral failure.
- The README "Toolchains" section describes both groups.
- Tag `sandbox-ref-17`. The qualified shared code changes, so restricted
  installations rerun `--container-setup` after adopting it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `toolchain-library`: the "Session variables are protected from toolchains"
  requirement gains the bus variable and the split between neutral and
  profile variables in `launch-env`.

## Impact

- `setup/toolchains.py`, `tests/test_toolchains.py`, `README.md`,
  `docs/validation.md`, `docs/network-contract.md` (parity cells).
- The launcher is unchanged: Claude does not set `DBUS_SESSION_BUS_ADDRESS`.
- Wrappers:
  - Codex, OpenCode and Pi adopt `sandbox-ref-17` from `sandbox-ref-16`
    through small changes of their own;
  - Antigravity's paused `adopt-sandbox-ref-16` change is updated to target
    `sandbox-ref-17`.
- A toolchain already installed with `DBUS_SESSION_BUS_ADDRESS` makes
  `launch-env` fail with an invalid-environment error. No example recipe sets
  it; the operator fixes it with `remove` and `add`.
- Out of scope:
  - agent settings that a launcher sets after the toolchain environment, such
    as Pi's `PI_TELEMETRY`. The launcher's value wins there, as each port
    already specifies;
  - protecting the other agents' names in `add`.
