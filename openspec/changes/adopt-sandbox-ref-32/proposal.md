# Proposal

## Why

Claude runs on `sandbox-ref-28`, where container-based tests need host Podman
delegation. Delegation gives the session host engine authority, and works only
in unrestricted mode. `sandbox-ref-32` replaces it with a private session
container engine: the operator adds the images that tests need as toolchains,
and restricted sessions can use them too. The tag also lets the toolchain
command add catalog recipes by name, without maintenance consent.

## What Changes

- **Adopt the tag.** `tools/propagate.py` adopts `sandbox-ref-32` from
  `sandbox-ref-28`. The 2026-11-24 dry run gave this plan:
  - update 18 shared files;
  - add 14: `launcher/engine/`, `setup/engine.py`, `setup/toolchain-catalog/`
    and `tests/test_engine.py`;
  - rewrite 11 tag references in `docs/network-contract.md`;
  - move the manifest.

  The thin Windows entry and `.gitattributes` are unchanged.
- **BREAKING: host Podman delegation is removed.**
  - `CLAUDE_CONTAINER_PODMAN=1` stops every launch with migration guidance.
  - Saved delegation stops the Windows bootstrap.
  - Setup migrates saved preferences to schema 3, without the setting.
- **Session container engine.** A session gets a private rootless engine when
  the toolchain library holds an image. The session reaches it at
  `CONTAINER_HOST` and `DOCKER_HOST=tcp://127.0.0.1:2375`. Setup builds
  `localhost/claude-code-engine`.
- **Toolchain recipes.** Schema 2 recipes can:
  - have several sources;
  - list digest-pinned or local images;
  - be added by catalog name.

  The examples in `docs/toolchains/` are replaced by the release catalog.
- **Claude's own tests.** The delegation cases become refusal or engine cases.
  `tests/run-runtime.sh` can run from inside a session, against its engine.
- **Claude's documentation.** The following are adapted to Claude:
  - `README.md`, `AGENTS.md`, `docs/setup.md`;
  - the launcher documents;
  - the parity row in `docs/network-contract.md`.

## Capabilities

### New Capabilities

- `session-container-engine`: the private per-session engine, as specified in
  `sandbox-container`:
  - when it starts, and its endpoint;
  - its mounts, image store, storage, budgets and hardening exceptions;
  - its cleanup and qualification.

### Modified Capabilities

- `toolchain-library`: catalog names, several sources, archive downloads,
  recipes outside writable mounts, Windows drive paths, image entries, the
  read-only image store and image removal.
- `container-isolation`: no Podman socket in sessions. The approval rule and
  the capability rule are restated without delegation, with the engine client
  in place of the delegated client.
- `container-launcher`: removes delegation from engine verification, launch
  contexts and image operations, and refuses a leftover delegation opt-in.
- `container-setup`:
  - drops the delegation choice and migrates saved delegation;
  - adds the engine image to preparation;
  - applies the saved worktree scope only to sessions;
  - re-verifies the toolchain library.
- `network-egress`: engine containment replaces delegation rejection in the
  credential-free bypass evidence.
- `shared-launcher`: Claude's approval-bypass combinations no longer include
  delegation.
- `windows-launcher`: the delegation refusal is the common migration refusal.
  The engine works in the Podman machine.
- `container-podman-access`: retired. All its requirements are removed.

## Impact

- **Shared files:** as the tag's dry run lists them. A defect in shared code
  pauses this change for a fix in `sandbox-container`.
- **Claude's tests:**
  - `tests/run-runtime.sh`, `test_runtime.py` and `test_network_runtime.py`;
  - `test_wrapper.py`, `test_setup_wrapper.py` and `test_setup_runtime.py`.
- **Operators:**
  - Rerun `claude-container --container-setup` after updating. It builds the
    engine image and migrates saved delegation.
  - Add the images that tests need with `--container-toolchain add`.
- **Images:** a new `localhost/claude-code-engine` image, from a digest-pinned
  `quay.io/podman/stable`. Claude's runtime image is unchanged.
