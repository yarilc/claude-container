# Design

## Context

Claude is on `sandbox-ref-21`. Its launcher, `claude-container.sh` (960 lines), is a family-A launcher. Apart from profile data, it matches the reference line for line in phases 3-4. The launcher contract (`docs/launcher-contract.md` in `sandbox-container`) names the Claude-only behavior:

- the `CLAUDE_YOLO` flag;
- the six provider-only optional-traffic settings (M2);
- `ANTHROPIC_API_KEY` forwarding (U10).

The test map (`docs/launcher-test-map.md`) sorts Claude's 83 `tests/test_wrapper.py` cases as follows:

| Kind | Cases | Notes |
| --- | --- | --- |
| Duplicates of the reference | 67 | |
| Rewritten into shared cases | 9 | |
| Shared | 4 | |
| Hooks | 3 | |

Six of the shared and rewritten cases are marked "to verify at adoption":
- `test_missing_network_mode_requires_setup_without_side_effects`;
- `test_shell_does_not_receive_yolo_or_cli_arguments`;
- `test_toolchain_cannot_set_claude_variables`;
- `test_proxy_hardening_failure_never_starts_agent`;
- `test_proxy_probe_timeout_and_interruption_clean_only_proxy`;
- `test_private_existing_claude_and_wrong_owner`.

The `tools/propagate.py` dry run from `sandbox-ref-21` to `sandbox-ref-22` (2026-11-17) gives this plan:

- **Copy (new files):**
  - `launcher/core.sh`;
  - `tests/test_launcher.py`;
  - `tests/fake_podman.py`;
  - `tests/fixtures/agent/launcher.sh`;
  - `tests/fixtures/shell-agent/launcher.sh`.
- **Update (changed files):**
  - `network/README.md`, `network/agent_profile.py`, `network/control.py`, `network/qualification_records.py`, `network/qualify.py`;
  - `setup/common.py`, `setup/launch.py`, `setup/setup.py`;
  - `tests/fixtures/agent/profile.json`, `tests/sandbox_profile.py`, `tests/test_agent_profile.py`, `tests/test_alignment.py`, `tests/test_network_policy.py`, `tests/test_qualification.py`, `tests/test_setup.py`.
- **Rewrite:** six references in `docs/network-contract.md`.
- **Move:** the manifest.

## Goals / Non-Goals

**Goals:**
- Claude runs entirely on the shared core. Its own launcher code is the entry script and `agent/launcher.sh`.
- No Claude launcher behavior disappears without being either a recorded visible change or a shared test.

**Non-Goals:**
- Adopting the core in the other four wrappers.
- Changing Claude's image, policy inventories or profile.
- Changing reference files inside this repository. A defect found here is fixed in `sandbox-container` and arrives by a tag.

## Decisions

1. **Adopt with the tool, from `sandbox-ref-21`.** The dry run must list exactly the plan in "Context". `--apply` switches to the branch `adopt-sandbox-ref-22`. Alternative rejected: copying the core by hand. That would bypass the manifest and the exact-copy check.

2. **Entry script and agent part.**
   - `claude-container.sh` is the reference `sandbox-container.sh`, with only the wrapper name changed in its comment.
   - `agent/launcher.sh` declares:
     - the profile values;
     - `AGENT_EXEC=/usr/local/bin/claude` and `AGENT_EXEC_TMP=0`. These are the profile defaults, so `agent/profile.json` stays as it is.
     - `AGENT_CREDENTIALS=(anthropic-api=ANTHROPIC_API_KEY anthropic-account=)`;
     - the six settings in `AGENT_PROVIDER_ENV`;
     - empty session, restricted, unset and reserved arrays;
     - one hook. `agent_approval_bypass` sets `agent_bypass_args=(--dangerously-skip-permissions)`; the core already skips it in shell mode and in the qualification probe.
   - Alternative rejected: an `agent_environment` hook for `ANTHROPIC_API_KEY`. The core already forwards the selected profile's credential (U10), and a hook would duplicate that.

3. **Old tests gate the deletion.** Before the old launcher is deleted, the current `tests/test_wrapper.py` (the `sandbox-ref-21` version) runs against the new entry script and core. Its fake engine and the 83 cases stay unchanged. Every failing case is resolved in exactly one of three ways:
   - **(a) Visible change.** The failure matches a row of the contract's "Visible changes" list, so the case is dropped.
   - **(b) Lost behavior.** The work stops. The behavior and a shared case go into `sandbox-container` through a reference change and a new tag, and this change then adopts that tag instead.
   - **(c) Claude-only behavior.** The case stays in the reduced `tests/test_wrapper.py`.

   Every passing duplicate is dropped, because `tests/test_launcher.py` covers it. The six "to verify at adoption" cases are resolved by name. The result goes into `docs/validation.md` as a table: the case, its outcome, and the shared case or visible-change row it maps to.

   Alternative rejected: deleting the old tests and trusting the map. The map was built by reading tests, not by running them against the core.

4. **Reduced `tests/test_wrapper.py`.** It uses the shared `tests/fake_podman.py` and the real `agent/launcher.sh`. It covers:
   - the three hook cases:
     - `test_four_independent_permission_combinations`;
     - `test_shipped_inventories_are_exact`;
     - `test_removed_account_hosts_require_a_separate_profile`;
   - the provider-only settings, present in provider mode and absent in the other modes;
   - `ANTHROPIC_API_KEY` with each policy profile, including a `CLAUDE_CONTAINER_ENV_VARS` attempt under `anthropic-account`;
   - the provider disclosure in `--container-help`;
   - every outcome (c) from decision 3.

   Real-image behavior stays in `tests/test_runtime.py`.

5. **Wrapper-owned runtime tests follow the reference diff.**
   - `tests/run-runtime.sh --wrapper` runs `test_launcher.py` and `test_wrapper.py`.
   - `tests/test_runtime.py` uses 512/32/512 MiB.
   - `tests/test_network_runtime.py` installs `agent/launcher.sh`, `launcher/core.sh` and `.containerignore`.
   - The `tests/test_setup_runtime.py` shim answers only the `{{.Id}}` inspection.
   - `tests/test_setup_wrapper.py` covers the provider default: a missing mode without settings still gets setup guidance, and an empty override selects provider.

6. **Documentation.**
   - **README.** It is rewritten where the launcher changed:
     - help and first steps;
     - network modes, with the provider default and no `c777b73` history;
     - temporary storage and home;
     - `CLAUDE_CONTAINER_ENV_VARS` and `CLAUDE_CONTAINER_READONLY_STATE`;
     - credentials;
     - build-only and stale images;
     - the shared components section, which names the core.
   - **`docs/setup.md`.** It follows the provider default.
   - **Parity table in `docs/network-contract.md`.** It is fixed by hand after `--apply`, as for `sandbox-ref-21`:
     - the reference row is copied from `sandbox-container`;
     - the Claude row says it adopted `sandbox-ref-22`, with its runtime results;
     - the other wrapper rows are copied from their repositories.

7. **Validation scope.** The launcher, installation manifest and qualification identity all change, so validation covers the full set:
   - **Unit tests:** the unit discovery in the disposable test container.
   - **Runtime runs:**
     - `--wrapper`, `--setup`, `--setup-runtime`, `--qualification`, `--network` and `--guard`;
     - the default runtime run (`test_runtime.py`) against an image rebuilt with the `build-inputs-hash` label;
     - `tests/image-smoke.sh`.
   - **Other checks:**
     - `git diff --check`;
     - `tests/test_reference_copy.py` with host Python next to the `sandbox-container` checkout.

## Risks / Trade-offs

- **[Decision 3 finds a lost behavior]** → Implementation pauses for a reference change and a new tag. The tasks name that branch point, so it is not absorbed into this change.
- **[Images built before the adoption have no `build-inputs-hash` label and are refused as stale]** → This is intended (U8). The test images and the operator's installations are rebuilt with `--container-build` or `--container-setup`.
- **[Installed qualification reports no longer match, because the code identity now includes the core and the agent part]** → The operator runs `--container-setup` on the three reference hosts after the merge.
- **[Help text moves to the core and can drift from the README]** → The README quotes no help text. It describes behavior and points to `--container-help`.
- **[Other wrapper rows in the parity table still read `sandbox-ref-21`]** → This is correct until their own adoptions.

## Migration Plan

1. Commit this change directory on `main`, branch `prepare-adopt-sandbox-ref-22`, then dry-run and apply the propagation.
2. Write the entry script and the agent part. Run the old tests (decision 3) and resolve every failure before touching `tests/test_wrapper.py`.
3. Reduce the wrapper tests, update the runtime tests and the documentation, validate, and merge into `main`.
4. The operator pushes, then runs `--container-setup` on the three hosts. The change is archived with spec sync.

Rollback: before the merge, delete the branch. After the merge, revert the merge commit. The installed release stays the previous one until setup runs.
