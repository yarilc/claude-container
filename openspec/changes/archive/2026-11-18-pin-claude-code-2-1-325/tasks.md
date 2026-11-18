## 1. Baseline

- [x] 1.1 Record the current image ID and the reported versions (2.1.316 and 1.16.0). Run the pin tests and the credential-free unit suite on the unchanged tree, and save the results as the baseline for the old-test gate.

## 2. Pins and policy

- [x] 2.1 Set `CLAUDE_CODE_VERSION=2.1.325` and `OPENSPEC_VERSION=2.0.0` in `Containerfile`. Leave the base digest unchanged.
- [x] 2.2 Set `tested.cli` in `agent/policies/default.json` to `2.1.325`, with the inventory note and date. The revision stays unless task 3.3 finds a changed required host.
- [x] 2.3 In `tests/test_image_pins.py`, update the diverging-CLI mutation (`2.1.325` to `2.1.326`) and the OpenSpec version-range mutation. In `tests/test_network_runtime.py`, update the expected version.

## 3. Build and inventory

- [x] 3.1 Rebuild with `CLAUDE_CONTAINER_NETWORK=unrestricted CLAUDE_CONTAINER_MAINTENANCE=1 ./claude-container.sh --container-build`. The image must report `claude --version` 2.1.325 and `openspec --version` 2.0.0.
- [x] 3.2 Check the native controls. `claude --help` must list `--dangerously-skip-permissions`, and a string scan of the installed binary must find every name in `AGENT_PROVIDER_ENV`.
- [x] 3.3 Run the static endpoint inventory of 2.1.325 with the 2026-11-08 method and compare it with the old table. If a required host changed, stop and agree with the user on a `network-egress` delta and a new policy revision.
- [x] 3.4 In provider mode, run `claude -p` with a dummy key under the logging proxy. Record every destination it attempts, and confirm the guard denies anything outside the profile.

## 4. Suites

- [x] 4.1 Run the full credential-free suite (unit, shared, setup, setup-runtime, qualification, network, guard and default runtime). Classify any failing old test with the gate and resolve it before going on.
- [x] 4.2 Run the offline OpenSpec round trip from the reference change in shell mode.
- [x] 4.3 Run `bash ../sandbox-container/tools/shellcheck.sh .` and `git diff --check`. Record the known agent-part findings; this change must add none.

## 5. Record

- [x] 5.1 Update `README.md` and `docs/network-contract.md` where they name the measured version, or record that 2.1.316 is kept as the original measurement.
- [x] 5.2 Add a dated entry to `docs/validation.md`. It records:
  - the version rule and the reported versions;
  - the inventory diff, the dummy-key run and the suite results;
  - the unchanged base digest.
- [x] 5.3 Run `openspec validate pin-claude-code-2-1-325 --strict`, then commit on `main`.

## Workflow follow-up

- The operator pushes `main` and reruns `--container-setup` on the three hosts.
- Archive with `/opsx:archive pin-claude-code-2-1-325`. Sync specs only if a `network-egress` delta was added.
- Real-account checks go to the deferred authenticated pass.
