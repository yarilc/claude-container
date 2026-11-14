# Design

## Context

`setup/toolchains.py` (`sandbox-ref-16`) holds one protected set:

- `PROTECTED`: neutral names (identity, shell, runtime, proxy, CA,
  `CONTAINER_HOST`, `CONTAINER_CONNECTION`) plus the profile's
  `config_dir_env`, `approval_bypass_env` and `credential_envs`;
- `PROTECTED_PREFIXES`: `ld_`, `xdg_`, the profile's `env_prefix` and
  `sandbox_`.

`protected()` checks both, case-insensitively. `validate_recipe()` (used by
`add`) rejects a protected name, and `launch_env()` raises `SetupError` for one
found in the index. The launchers print `launch-env` warnings and stop on its
failure.

Each wrapper loads the module with its own `agent/profile.json`. The profile
part of the set therefore differs per wrapper, while the library and its index
are shared.

## Goals / Non-Goals

**Goals:**

- A recipe accepted by one wrapper never stops another wrapper's sessions.
- `DBUS_SESSION_BUS_ADDRESS` can never come from a toolchain.
- The neutral rules keep their current strictness.

**Non-Goals:**

- Rejecting the other agents' variables in `add`. The shared code cannot name
  them.
- Agent settings that a launcher sets after the toolchain environment (Pi's
  `PI_TELEMETRY`, Antigravity's `AGY_CLI_DISABLE_AUTO_UPDATE`). Each port
  already orders its values last.
- `env.sh`. A toolchain's own `env.sh` still exports every variable of its
  recipe when the agent sources it explicitly.

## Decisions

1. **Two named groups:**

   - `PROTECTED` and `PROTECTED_PREFIXES` keep only neutral entries, plus
     `DBUS_SESSION_BUS_ADDRESS`;
   - `PROFILE_PROTECTED` (configuration, approval and credential variables)
     and `PROFILE_PREFIX` (`env_prefix` + `_`) hold the profile entries;
   - `protected()` keeps meaning "either group", so `add` is unchanged apart
     from the bus variable;
   - a new `profile_protected()` tests only the profile group.

   The comment on the sets explains why the groups differ.
2. **`launch-env` order of checks, per variable:**

   1. invalid name, neutral name, control character or tab → `SetupError`,
      as today;
   2. profile name → skip it and add the warning `toolchain <name> sets
      <VARIABLE>, which this wrapper protects; it is left out of this
      session`;
   3. otherwise → emit it.

   The warning goes through the existing `warnings` list, so the launchers
   print it with the module prefix and need no change.
3. **Why the bus variable is neutral.** No wrapper provides a session bus.
   Antigravity removes the variable with `--unsetenv`, which does not remove a
   value given with `--env` on the tested engine. Rejecting it in `add` gives
   every wrapper the same rule, whatever the launcher order.
4. **Tests (shared, `tests/test_toolchains.py`):**

   - the recipe-rejection table gains `DBUS_SESSION_BUS_ADDRESS`;
   - `launch-env` with an index entry carrying a profile variable (the
     profile's first credential, or its configuration variable when it has
     none) returns the other lines and one warning naming the toolchain and
     the variable;
   - the existing XDG index test keeps the neutral failure, and a bus
     variable in the index fails the same way.

   The tests use `PROFILE` values only, so they pass in every wrapper.

## Risks / Trade-offs

- [A profile variable is now silently tolerated in the index] → The warning
  names the toolchain at every launch, so the operator can remove or replace
  it.
- [An existing toolchain that sets `DBUS_SESSION_BUS_ADDRESS` stops every
  launch] → None of the example recipes sets it. The operator runs `remove`
  and `add`, as the error names the variable.
- [`env.sh` still exports a profile variable] → Only when the agent sources
  that toolchain explicitly. The variable came from the operator's own recipe,
  and the launcher's session environment is unaffected.

## Migration Plan

1. Merge, run the tagging modes, tag `sandbox-ref-17`. The operator pushes
   `main` and the tag and reruns `--container-setup`.
2. Archive this change with the spec sync.
3. Codex, OpenCode and Pi adopt `sandbox-ref-17`. The Antigravity change is
   updated to target it.
