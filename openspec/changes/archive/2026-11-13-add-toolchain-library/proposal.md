# Proposal

## Why

The runtime images carry one common toolset. When a task needs another
toolchain, such as Java 21, a restricted session cannot install it: runtime
package downloads are denied and the agent has no Podman access. The only
way out today is an unrestricted session with Podman delegation, which
discards the network boundary and the isolation this project provides.

Toolchains are data the agent executes, like the workspace. A read-only
toolchain mount adds no network, IPC or privilege capability: the guard's
Landlock ruleset restricts only `REFER` and socket creation, so binaries
under the mount run with the same restrictions as everything else. The
operator can therefore supply toolchains without widening the boundary.

## What Changes

- **Toolchain library.** A host directory shared by all wrappers, by default
  `${XDG_DATA_HOME:-$HOME/.local/share}/sandbox-toolchains`. Only the
  operator changes it.
  - A toolchain is a relocatable prefix with a manifest. Its source is either
    a subpath of a digest-pinned OCI image or a local archive with a SHA-256.
  - A recipe can require other toolchains (Maven requires Java), carry
    notes for the agent, and set literal environment values, such as caches
    under `/tmp`.
  - The library also holds generated `toolchains.md` instructions for the
    agent, an `index.json`, and an `env.sh` per toolchain.
- **Operator command `--container-toolchain`** (`add <recipe.json>`, `list`,
  `remove <name>`, `verify [<name>]`). It runs on the host, outside any
  session:
  - `add` from an image requires exact `CLAUDE_CONTAINER_MAINTENANCE=1`, because it
    may pull;
  - `add` and `verify` run the recipe's check command in the wrapper's
    runtime image, without network, before accepting a toolchain;
  - the manifest records the verified base image.
- **Launcher.**
  - Every session mounts the library read-only, `nosuid,nodev`, at
    `/toolchains`. The launcher creates the library privately when it is
    missing, so a toolchain added later appears in a running session
    without a restart.
  - New sessions receive the environment of the default toolchains
    verified for the current base. Their `PATH` entries come after the
    image's, so they never replace the agent's own `node` or `python3`.
  - `CLAUDE_CONTAINER_TOOLCHAINS=0` disables the mount.
- **Agent instructions.** The wrapper does not touch memory files or install
  skills. The operator may add one line to `CLAUDE.md`: "Read
  /toolchains/toolchains.md".
- **Shared code.** The library logic is a new agent-agnostic module,
  `setup/toolchains.py`. It is installed and qualified with the other shared
  code and released under a new reference tag. The sibling wrappers adopt it
  through their own changes.
- **Documentation and roadmap.**
  - The README gains a "Toolchains" section, with example recipes for
    Temurin 21, Maven 3.9, Go, Node.js 24, Python 3.13 and Rust. Rust is
    documented with its verified result, because linking needs a linker
    that the runtime image lacks.
  - SELinux and AppArmor are documented as not tested.
  - `todo.md` gains three roadmap entries: SELinux support, AppArmor
    support, and a proxy ACL management CLI. The ACL CLI is where network
    access for toolchain dependencies will be decided.
- **BREAKING (installation):** the launcher and the qualified shared code
  change, so restricted installations rerun `--container-setup`.

## Capabilities

### New Capabilities

- `toolchain-library`: the operator-managed toolchain library:
  - its format, sources and integrity checks;
  - the `--container-toolchain` command;
  - the generated instructions and environment files;
  - the read-only session mount and the default environment.

### Modified Capabilities

None. Existing requirements do not enumerate the session mounts exhaustively.
The new mount and the command are specified in `toolchain-library`.

## Impact

- `claude-container.sh`: the library mount, `PATH` and environment, the
  `--container-toolchain` dispatch, help text and `--mount-target
  /toolchains`.
- `setup/toolchains.py` (new); `setup/common.py` (`MANIFEST`);
  `network/qualification_records.py` (`SHARED_CODE`);
  `network/control.py` (trusted path).
- Tests: `tests/test_toolchains.py` (new, shared), `tests/test_wrapper.py`,
  `tests/test_runtime.py`, `tests/test_alignment.py` (`SHARED_TESTS`).
- `README.md`, `AGENTS.md`, `docs/setup.md`, `docs/validation.md`,
  `todo.md`.
- Out of scope:
  - network access for package registries, to be decided with the proxy ACL
    CLI;
  - non-relocatable toolchains;
  - SELinux and AppArmor;
  - the sibling wrappers.
