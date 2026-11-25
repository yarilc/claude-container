# Proposal

## Why

Claude runs on `sandbox-ref-34`. The reference's runner suites failed on the
native Rocky 9 lab host, because the tests assumed a host with IPv6, every
cgroup controller delegated, a Debian CA bundle path, and a terminal that
attaches through the runner's Podman client. `sandbox-ref-35`
(`fix-runtime-test-portability`) fixes the shared tests. Claude's own copies of
the network and setup acceptance tests carry the same assumptions, and Claude's
runner image has the same Podman 4.3.1 client. Until Claude adopts the tag and
fixes its own copies, its suites fail on that host for reasons that are not
product defects.

## What Changes

- **Adopt the tag.** `tools/propagate.py` adopts `sandbox-ref-35` from
  `sandbox-ref-34`. The 2026-11-25 dry run gave this plan:
  - update 5 shared tests: `tests/guard_runtime_fixture.py`,
    `tests/network_fixture.py`, `tests/test_alignment.py`,
    `tests/test_guard.py` and `tests/test_network_feasibility.py`;
  - add the shared terminal probe `tests/guard_terminal_probe.py`;
  - rewrite 5 tag references in `docs/network-contract.md`;
  - move the manifest to commit `2f407bf`.

  No product file changes: no launcher, network, setup or image file. The thin
  Windows entry and `.gitattributes` are unchanged.
- **Claude's network acceptance tests** (`tests/test_network_runtime.py`):
  - `test_agent_budgets_are_effective_and_lifetime_cleans_owned_proxy` checks
    each budget as the engine enforces it, in both its offline and provider
    cases. A delegated controller holds the budget. An undelegated one reads
    `max`. On the process rlimit fallback, the limit is checked in
    `/proc/self/limits`. Today the test always reads `cpu.max` and fails
    where `cpu` is not delegated.
  - The terminal case of
    `test_guarded_arguments_stdin_status_and_tty_both_state_modes` runs in
    its own subtest. It skips with the shared probe's reason where no
    terminal attaches to a `--read-only` container through the runner's
    client. The piped case still runs in both state modes.
- **Claude's setup acceptance test** (`tests/test_setup_runtime.py`):
  - The CA case copies the runner's bundle into the disposable native test
    state, and answers the prompt with that path.
  - `clean_tags` removes the engine, guard toolchain and proxy tags that
    setup names after each release the test created.
- **`AGENTS.md`:**
  - the reference's manual terminal check, with Claude's names;
  - the policy path rule names `/claude-home`. It named `/codex-home`, a
    copy error.
- **Spec gap from `sandbox-ref-33`.** Claude copied the
  `session-container-engine` delta before the reference added the namespace
  interface scenario and the README's read-only `/sys` item. Claude's tests
  and README already have both. Only its spec lacks them.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `session-container-engine`:
  - "Engine shares the session network boundary" gains the scenario
    "Interfaces of a restricted session with an engine";
  - "Engine documentation" requires the README to say that a session with an
    engine sees the host's `/sys` read-only.

  Both take the reference's text.

## Impact

- **Shared files:** the six test files of the dry run. They are test-only, so
  installations need no new setup. A defect in them pauses this change for a
  fix in `sandbox-container`.
- **Claude's tests:** `tests/test_network_runtime.py` and
  `tests/test_setup_runtime.py`.
- **Documentation:**
  - `AGENTS.md`;
  - `docs/validation.md`;
  - the parity table in `docs/network-contract.md` here;
  - Claude's parity row in the reference and the other four wrappers.
- **Validation:**
  - the modes the tool prints: the reference-copy and alignment tests,
    `--guard` and `--network`;
  - `--network-feasibility`, which the tool does not print for this fixture;
  - `--setup-runtime`, because its test changed;
  - the unit discovery.

  These run on the native Rocky 9 lab host and on WSL, as for the reference.
- **Operators:** nothing to rerun. Claude's runtime, egress, engine and guard
  images and the installed code are unchanged.
