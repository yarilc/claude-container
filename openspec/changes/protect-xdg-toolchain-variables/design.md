# Design

## Context

- `setup/toolchains.py`:
  - `PROTECTED` is a set of lowercase names;
  - `PROTECTED_PREFIXES` is `('ld_', <wrapper prefix>_, 'sandbox_')`;
  - `protected()` checks both;
  - `validate()` (recipe `env`) and `launch_env()` (index entries) call it.
- Of the five wrappers, only OpenCode sets XDG variables (`--env
  XDG_{CONFIG,DATA,CACHE,STATE}_HOME`). The other four set none, and their
  shells or tools may read XDG defaults.
- The OpenCode launcher adds the toolchain environment after its own `--env`
  values, as the reference does, and Podman keeps the last value.
- `tests/test_toolchains.py` has a table of rejected recipes (`protected
  variable`, `prefix variable`, `loader variable`, `proxy variable`) and a
  `launch_env` test.

## Goals / Non-Goals

**Goals:**
- No toolchain can change where a wrapper keeps its state through XDG
  variables, in any wrapper.
- The rule is enforced in the shared module, at `add` and at `launch-env`,
  like the existing protected names.

**Non-Goals:**
- Agent-specific variables outside the wrapper prefix, such as
  `OPENCODE_CONFIG`. A recipe that sets one is an explicit operator
  configuration of the agent. A profile field for extra protected names
  would be a separate change.
- Changing the launchers' `--env` order.

## Decisions

1. **Protect the whole `xdg_` prefix** by adding it to
   `PROTECTED_PREFIXES`, instead of listing five names.
   - The XDG Base Directory variables all start with `XDG_`, including the
     `XDG_*_DIRS` search paths that change where configuration is found.
   - No toolchain needs to set them: caches are set through tool-specific
     variables, such as `GOCACHE`.
   - Alternative: list `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME`,
     `XDG_STATE_HOME` and `XDG_RUNTIME_DIR`. Rejected: it leaves
     `XDG_CONFIG_DIRS` and `XDG_DATA_DIRS`, and any future variable,
     uncovered.
2. **Tests.**
   - Add an `xdg variable` case to the rejected-recipe table.
   - Add a `launch_env` case with a hand-written index entry carrying
     `XDG_DATA_HOME`, which must raise the invalid-environment error.
3. **Documentation.** The README "Protected variables" bullet names XDG
   variables. The sibling READMEs get the same wording when they adopt the
   tag.
4. **Tag `sandbox-ref-15`** on the merge. The runner modes follow the
   `docs/propagation.md` rule for a change to `setup/` and to a file in
   `SHARED_CODE`: unit discovery, `--setup`, `--setup-runtime` and
   `--qualification`. `--wrapper` and the default runtime mode also run,
   because the launcher calls `launch-env`.

## Risks / Trade-offs

- [An installed toolchain already sets an XDG variable] → `launch-env`
  fails and the launcher suggests `<PREFIX>_TOOLCHAINS=0` to start without it;
  the operator removes and re-adds it. No documented recipe sets one.
- [Qualification identity] → `setup/toolchains.py` is qualified code, so
  installations rerun `--container-setup` after adoption.

## Migration Plan

1. Merge and tag `sandbox-ref-15`. The operator pushes and reruns
   `--container-setup` on the three hosts.
2. Archive with the spec sync.
3. OpenCode adopts `sandbox-ref-12` → `sandbox-ref-15` with the library port.
   Codex adopts `sandbox-ref-14` → `sandbox-ref-15`.
4. Rollback before the push: delete the local tag and reset `main` to
   `2e3206f`.
