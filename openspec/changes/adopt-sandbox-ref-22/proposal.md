# Proposal

## Why

`sandbox-ref-22` adds the shared Bash launcher core (`launcher/core.sh`), so launcher behavior is fixed and tested once for all wrappers. Claude is the first wrapper to adopt it because its 960-line `claude-container.sh` is the closest to the reference. Until Claude adopts the tag, its launcher keeps diverging from the reference, and the 156 "to verify at adoption" cases in the reference test map stay open.

## What Changes

- Adopt `sandbox-ref-22` with `tools/propagate.py`, then `sandbox-ref-23`. `sandbox-ref-23` removes the Claude identifiers that `sandbox-ref-22`'s shared `tests/test_launcher.py` carried; this adoption found them (reference change `fix-shared-test-identifiers`). This copies `launcher/core.sh`, `tests/test_launcher.py`, `tests/fake_podman.py` and the launcher fixtures, plus the changed shared files (`network/*`, `setup/*`, `tests/test_alignment.py`, `tests/test_setup.py`, ...), and moves the manifest and the current-state references to the tag.
- Replace `claude-container.sh` with the thin entry script. The entry script is identical to the reference's apart from its name.
- Add `agent/launcher.sh`: the Claude profile data, and one hook, `agent_approval_bypass`, which turns `CLAUDE_YOLO` into `--dangerously-skip-permissions`. The six optional-traffic settings become `AGENT_PROVIDER_ENV`. `ANTHROPIC_API_KEY` is listed only under the `anthropic-api` policy profile.
- Before the old launcher is deleted, run Claude's current `tests/test_wrapper.py` against the new core. For each failing case, decide one of three outcomes:
  - it is a recorded visible change;
  - it is a lost behavior, which is fixed in the reference with a shared case, and the adoption then moves to the new tag;
  - it is Claude-only behavior, which stays in the reduced `tests/test_wrapper.py`.
- Reduce `tests/test_wrapper.py` to Claude's hook and data tests. Update the wrapper-owned runtime tests: `tests/run-runtime.sh` (`--wrapper` also runs `test_launcher.py`), the tmpfs sizes in `tests/test_runtime.py`, the installation files in `tests/test_network_runtime.py`, `tests/test_setup_runtime.py` and `tests/test_setup_wrapper.py`.
- Visible changes for Claude users, all from the contract's "Visible changes" list. Breaking changes are allowed: the project has no release.
  - **BREAKING**: a missing `CLAUDE_CONTAINER_NETWORK` selects `provider`. Without the provider settings, the launch still stops with setup guidance.
  - **BREAKING**: `--container-build` without Claude arguments builds and exits. A stale image is refused until it is rebuilt.
  - **BREAKING**: shell mode passes its arguments to Bash.
  - **BREAKING**: `ANTHROPIC_API_KEY` reaches provider sessions only with the `anthropic-api` profile. It never reaches offline or unrestricted sessions unless `CLAUDE_CONTAINER_ENV_VARS` lists it in unrestricted mode.
  - `/tmp`, `/var/tmp` and `/run` are 512, 512 and 32 MiB, and shared-state sessions get a 512 MiB tmpfs home.
  - New: `CLAUDE_CONTAINER_ENV_VARS` and `CLAUDE_CONTAINER_READONLY_STATE`.
  - Unrestricted sessions forward `COLORTERM`, `LANG`, `LC_ALL` and the proxy variables. They run with `--init`, and delegated sessions get private tmpfs storage for nested Podman. Every session gets `USER` and `CONTAINER_NAME`.
  - Engine queries are bounded by timeouts.
  - `CLAUDE_CONTAINER_STATE_DIR` and `CLAUDE_CONFIG_DIR` paths are checked before the engine. Isolated-home children must be contained and private.
- Update the README, `docs/setup.md`, `docs/network-contract.md` and `docs/validation.md`. The help text now comes from the core.

## Capabilities

### New Capabilities

- `shared-launcher`: Claude's launcher is the shared core with a thin entry script and the Claude agent part. The agent part stays consistent with the profile, and its hooks and data are tested by Claude's own tests.

### Modified Capabilities

- `container-launcher`:
  - provider default with setup guidance;
  - extra variables by name;
  - build-only operation and stale-image refusal;
  - bounded engine queries;
  - environment forwarding and shell arguments;
  - `--init` and `CONTAINER_NAME`;
  - qualification checks with the resolved mode;
  - first-user guidance without the pre-`c777b73` migration history.
- `container-isolation`:
  - the new temporary storage sizes and the tmpfs home;
  - approval bypass through the agent hook, with shell mode keeping its arguments.
- `container-podman-access`: private nested-Podman tmpfs mounts in delegated sessions.
- `container-setup`:
  - runtime builds always go through the wrapper's build-only operation;
  - the installation contains the core and the agent part.
- `network-egress`:
  - provider is the default mode;
  - the API key is forwarded only with the API profile;
  - qualification and preflight bind the core and the agent part;
  - profile fields;
  - the disclosure is printed from the policy.
- `persistent-state`:
  - read-only state;
  - the tmpfs home in shared mode;
  - state paths checked before the engine;
  - private, contained isolated-home children.

## Impact

- Code:
  - `claude-container.sh` shrinks from 960 lines to the thin entry script;
  - new `agent/launcher.sh`;
  - shared files copied from the tag;
  - wrapper-owned tests and docs updated.
- `agent/profile.json` needs no new fields: Claude uses the defaults `native.exec=/usr/local/bin/claude` and `native.exec_tmp=false`.
- The qualification identity now includes the core and the agent part. Every installation needs `--container-setup` again: the operator runs it on the three reference hosts.
- The other four wrappers stay on `sandbox-ref-21` until their own adoption changes. If this adoption finds a lost behavior, a reference fix and a new tag come first.
