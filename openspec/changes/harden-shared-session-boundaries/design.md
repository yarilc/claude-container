# Design

## Context

See proposal.md for the findings. Relevant current state:

- `network/agent_profile.py` validates `native` with required fields and the
  optional `private_shared_dirs` (`:152-166`). It checks that the
  configuration, approval and credential names are distinct from the derived
  `<PREFIX>_*` names (`:194-198`).
- `setup/toolchains.py:44-58` builds `PROTECTED`/`PROTECTED_PREFIXES`
  (neutral) and `PROFILE_PROTECTED`/`PROFILE_PREFIX` from the profile.
  `protected()` is used by `add` (`:239`); `launch-env` (`:645-651`) fails on
  neutral names and warns and skips profile names.
- `setup/toolchains.py:464` `check()` runs `podman run` without `--workdir`.
- `setup/common.py:267` `writable_mounts()` returns the workspace (the parent
  in worktree mode) and the state mounts. `protect_mounts` checks only the
  installation against them.
- `claude-container.sh:405-436` creates and checks the isolated home without
  comparing it to `workspace_mount` (`:268-270`).
- `claude-container.sh:926,931` attach with `podman start --attach
  --interactive`; `shutdown()` already forwards signals with `podman kill`.

## Goals / Non-Goals

**Goals:**
- One declarative place, the profile, for the variables each agent owns, so
  protection no longer depends on `--env` order in five launchers.
- Remove the remaining image-`WORKDIR` dependency from shared code.
- Make the state/workspace overlap rule shared for managed launches, and
  enforce it in Claude's direct launches.

**Non-Goals:**
- Moving the container lifecycle into shared code. The adopters' missing
  recovery and ownership checks (M2) are ported per wrapper.
- Credential forwarding (M1).
- Choosing the adopters' `protected_env` values; each adoption change does.

## Decisions

### `native.protected_env`: names and prefixes in one list

An entry ending in `_` is a prefix; any other entry is an exact name. Both
must match `[A-Z][A-Z0-9_]*`. The loader rejects duplicates, entries that are
neutral protected names or prefixes (`HOME`, `XDG_`, …), and prefixes shorter
than three characters, so a profile cannot protect everything by accident.
The neutral set moves from `setup/toolchains.py` into `network/agent_profile.py`
so that the loader can check it without importing setup code; the toolchain
module imports it from there.

- Alternative: two lists (`protected_env`, `protected_env_prefixes`). Rejected:
  the trailing `_` is unambiguous and keeps the profile short.
- Alternative: keep relying on launcher order and add a text-scanning test.
  Rejected: a wrapper that sets no literal (OpenCode's `OPENCODE_PERMISSION`
  without YOLO) is not protected by order at all.

The list is optional and defaults to empty. Profiles of adopters that have
not declared it behave as before, and `propagate.py` copies the profile
loader without touching the wrapper's `agent/profile.json`.

Claude's values: `CLAUDE_CODE_`, `ANTHROPIC_`, `DISABLE_TELEMETRY`,
`DISABLE_AUTOUPDATER`, `DISABLE_ERROR_REPORTING`,
`ENABLE_CLAUDEAI_MCP_SERVERS`. `ANTHROPIC_` covers `ANTHROPIC_BASE_URL` and
`ANTHROPIC_AUTH_TOKEN`, which could redirect traffic or credentials, and
contains the existing credential `ANTHROPIC_API_KEY`. The distinctness check
of `:194-198` does not apply to this list.

### `check()` starts in `/`

Add `'--workdir', '/'` to the `podman run` arguments, as `sandbox-ref-12` did
for qualification. The check command already reaches the toolchain by an
absolute path (`env.sh`).

### Overlap check in `writable_mounts()`

When the isolated state directory is selected, `writable_mounts()` compares
its resolved path with the resolved workspace (already the parent in
worktree mode) and raises `SetupError` when either equals or contains the
other. This covers managed launches in every wrapper with the tag. Direct
launches stay a launcher responsibility: Claude gets the same Bash check as
OpenCode (`opencode-container.sh:440-454`), placed before engine operations.
The shared default-state mounts are not checked here: the sensitive-workspace
rule already refuses the home directory.

### `--sig-proxy=false`

Claude's two `podman start --attach` calls get `--sig-proxy=false`, matching
the adopters. `shutdown()` already forwards INT, TERM and HUP within the
bounded-shutdown budget, so no forwarding is lost. A wrapper test asserts the
flag, and the existing signal tests keep passing.

### Alignment tests

- `test_consistency_check_detects_a_mismatch` calls the real check, a
  `missing_profile_names` helper, on modified wrapper text and expects the
  renamed variable.
- The helper checks the launcher's code and its `usage()` help text
  separately (decided during apply, 2026-11-15). Ignoring the help text
  outright failed in all five wrappers on `<PREFIX>_TOOLCHAINS_DIR`, which only
  shared code reads, so review finding L2's second point was a false positive.
  The rule is:
  - every profile variable appears in the code outside the help text, except
    those in `SHARED_READ` (today `TOOLCHAINS_DIR`);
  - every prefix-derived variable appears in the help text, except those in
    `INTERNAL` (today `QUALIFICATION_INPUT`, which setup sets).

  Credential variables are not required in the help text: Claude and
  OpenCode do not list them there today.

These are shared tests and travel with the tag.

## Risks / Trade-offs

- [The `ANTHROPIC_` prefix drops a legitimate toolchain variable, for example
  an SDK setting in a Python toolchain] → `launch-env` warns, and the operator
  forwards it explicitly. A narrower list can replace the prefix later.
- [An adopter adopts `sandbox-ref-18` but declares no `protected_env`] → It
  is no worse than today. Each adoption change lists its values as a task.
- [The stricter alignment test fails in an adopter whose launcher uses a
  profile variable only in its usage text] → The adoption dry run and suites
  show it; the adoption change fixes the launcher.
- [The overlap check refuses an existing operator setup] → The project is not
  distributed; the error names both paths. Move the state directory.
- [`--sig-proxy=false` changes signal timing in Claude] → The adopters have
  run with it since their lifecycle ports. The signal-matrix tests cover it.

## Migration Plan

1. Implement on a branch, run the runner modes listed in
   `docs/propagation.md` for `setup/`, `network/agent_profile.py` and shared
   tests: `--shared`, `--setup`, `--setup-runtime`, `--qualification`
   (`setup/` modules are qualified code) and `--wrapper`, plus the default
   mode.
2. Merge, update the parity table to the new tag, and create the annotated
   tag `sandbox-ref-18`.
3. Restricted Claude installations rerun `--container-setup`.
4. Each adopter adopts the tag in its own OpenSpec change.

Rollback before tagging is a revert. After tagging, a fix ships as
`sandbox-ref-19`.
