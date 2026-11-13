# Design

## Context

See proposal.md (Why) for the motivation. The relevant parts of the current
reference are listed below.

- **`claude-container.sh`:**
  - dispatches `--container-qualify` and `--container-setup` before reading
    `CLAUDE_CONTAINER_NETWORK`, with `exec python3 -I <installation>/…`
    (around line 150);
  - creates state directories with `create_private_directory` and checks
    them with `private_directory`, which requires caller ownership and
    `0700` (around line 375);
  - builds `container_args` around line 512. Every host bind is a
    `--volume`, and the CA bundle is the only read-only one;
  - passes restricted sessions to `network/session.py` with `--writable`
    and `--mount-target`. `network/control.py` rejects mount targets that
    overlap `/tmp`, `/run` and `/var/tmp`, and requires that installation
    files are not under a writable path (`trusted_path`).
- **Shared code** is `network/` and `setup/` (`tests/test_alignment.py`
  `SHARED_DIRECTORIES`). It must not contain agent identifiers. Two lists
  matter:
  - `setup/common.py` `MANIFEST` lists the installed files;
  - `network/qualification_records.py` `SHARED_CODE` lists the files whose
    digests qualification binds.
- **Guard:** Landlock rules cover only `REFER` and `MAKE_SOCK`
  (`network/guard.c:318`). Reading and executing a read-only mount needs no
  guard change.
- **Base image:** all five wrappers build from
  `node:22-bookworm-slim@sha256:4b15…` (glibc 2.36). The runtime images
  carry no label naming their base, but the installed `Containerfile` has
  exactly one digest-pinned `FROM` line.
- **Host Python:** 3.11 on this host; Rocky Linux 9 ships 3.9. The new
  module must run on 3.9, like the rest of `setup/`.

## Goals / Non-Goals

**Goals:**
- One library for all wrappers, changed only by the operator, visible
  read-only in every session and updated live.
- Deterministic, verifiable toolchains:
  - sources pinned by digest or SHA-256;
  - a check run in the real runtime image;
  - atomic library updates.
- No change to the guard, proxy, policy or network modes.

**Non-Goals:**
- Network access for package registries. That is a separate initiative
  (proxy ACL CLI).
- Downloading archives. The operator supplies a local file. The command
  pulls only OCI images, under maintenance.
- Non-relocatable toolchains, and any toolchain built inside the runtime
  image.
- Instructing the agent automatically. Memory files and skills are never
  touched.
- SELinux and AppArmor; the sibling wrappers.

## Decisions

1. **Library layout and generated files.**

   ```
   sandbox-toolchains/            0700, caller-owned
     .lock                        flock for every change
     toolchains.md                generated, for the agent
     index.json                   generated, schema 1
     <name>/
       toolchain.json             manifest: recipe + source identity + verification
       env.sh                     generated from the manifest
       <files of the prefix>
   ```

   - **`env.sh`** contains only `export NAME=/toolchains/<name>/<rel>` lines
     and `export PATH=/toolchains/<name>/<rel>:"$PATH"`. Values are fixed
     at generation time and quoted, so sourcing it runs no command.
   - **Generated content lists only the toolchains.** `toolchains.md` and
     `index.json` contain the toolchain name, version, commands (the
     executables found in the `PATH` entries), environment, verified base
     and date. They contain no host paths.

2. **Recipe file instead of command-line flags.** `add <recipe.json>` reads
   a small JSON file the operator keeps and reviews:

   ```json
   {"schema": 1, "name": "maven3.9", "version": "3.9.9",
    "source": {"image": "docker.io/library/maven@sha256:<digest>",
               "path": "/usr/share/maven"},
    "path": ["bin"],
    "env": {"MAVEN_HOME": {"toolchain": ""},
            "MAVEN_OPTS": {"value": "-Dmaven.repo.local=/tmp/m2"}},
    "requires": ["java21"],
    "notes": ["Dependency downloads are blocked unless the network policy allows the repository."],
    "check": ["mvn", "-v"], "default": true}
   ```

   - An archive source is `{"archive": "<local path>", "sha256": "<hex>",
     "strip_components": 1}`.
   - `env` values are either `{"toolchain": "<relative path>"}` or
     `{"value": "<literal>"}`. Literals cannot contain NUL or newline
     characters; `env.sh` quotes them, and they reach `--env` unexpanded.
   - `requires` names other installed toolchains. Their `env.sh` files are
     sourced first, and the dependency graph must be acyclic.
   - `notes` are short strings, rendered under the toolchain's entry in
     `toolchains.md`.
   - Unknown keys are rejected.
   - Relative values must not be absolute and must not contain `..`.
   - Alternative: flags such as `--image --path --env`. A recipe is
     reproducible, can be versioned, and keeps the command short.
   - The README ships six examples, with exact versions, digests and
     checksums fixed when they are verified:

     | Example | Source | Notes |
     | --- | --- | --- |
     | Temurin 21 | image `eclipse-temurin`, `/opt/java/openjdk` | `JAVA_HOME` |
     | Maven 3.9 | image `maven`, `/usr/share/maven` | requires `java21`; local repository under `/tmp` |
     | Go | image `golang` (bookworm), `/usr/local/go` | `GOTOOLCHAIN=local`; `GOCACHE` and `GOPATH` under `/tmp`; note: `go test`/`go run` need `GOTMPDIR` under the workspace, because `/tmp` is `noexec` |
     | Node.js 24 | archive `node-v24…-linux-x64.tar.xz` | `default: false`, because the image already has Node.js 22; npm cache under `/tmp` |
     | Python 3.13 | archive python-build-standalone `install_only` | `default: false`; virtual environments in the workspace |
     | Rust | image `rust` (bookworm), the toolchain directory under `/usr/local/rustup/toolchains` | needs a linker: verified with the musl target and `rust-lld`, or documented as unsupported without one |

3. **Extraction.**
   - **Image source:**
     1. if the image is missing, pull it only with exact
        `CLAUDE_CONTAINER_MAINTENANCE=1`;
     2. run `podman create --network=none <image>` with an inert command;
     3. stream `podman cp <cid>:<path> -` into the extractor;
     4. always remove the owned container.
   - **Archive source:** hash the file first, then extract it.
   - **Extractor:** Python `tarfile`, with each member checked by the module
     rather than through the 3.12 `filter=` argument, for 3.9
     compatibility. It rejects absolute names, `..`, device and FIFO nodes,
     and hard or symbolic links that resolve outside the root. It writes
     files as the caller, keeps the `0o755`/`0o644` executable bits, and
     clears setuid, setgid and sticky bits.
   - **Staging:** everything is written to `.staging-<name>-<random>`
     inside the library, then renamed into place. A replaced directory is
     renamed to `.old-…` and deleted after the index is regenerated.
     Running sessions keep any open files of the old version.

4. **Verification in the runtime image.**
   - The command runs
     `podman run --rm --network=none --read-only --userns=keep-id --user <uid>:<gid> --cap-drop=all --security-opt=no-new-privileges`
     with the library mounted read-only at `/toolchains`, and
     `sh -c '. /toolchains/<name>/env.sh && exec "$@"' sh <check…>`.
   - The staging directory is mounted at `/toolchains/<name>` for this run,
     so the check sees the final paths before the toolchain is published.
   - The runtime image is `CLAUDE_CONTAINER_IMAGE`, or the profile's agent
     image. A missing image fails with the setup or build guidance; the
     command never builds it.
   - The verified base is the single `FROM …@sha256:…` reference parsed
     from the installed `Containerfile`.
   - `verify` reruns the check for one or all toolchains and rewrites their
     manifests and the index.

5. **Launcher integration (wrapper-specific).**
   - **Dispatch:** `--container-toolchain` is handled before the network
     mode is read, like `--container-setup`:
     `exec python3 -I "$script_dir/setup/toolchains.py" "$@"`. It must be
     used alone, followed by its own arguments.
   - **Library checks:**
     - before building `container_args`, the launcher resolves the library,
       creates it privately when missing, and checks it with
       `private_directory`;
     - it rejects overlap, in either direction, with the workspace mount,
       the state directories and the installation;
     - with `CLAUDE_CONTAINER_TOOLCHAINS=0`, all of this is skipped;
     - other values than `0`, `1` or empty fail, using the existing
       `boolean` helper.
   - **Mount:** `--volume "$library:/toolchains:ro,nosuid,nodev"`.
     Restricted sessions also pass `--mount-target /toolchains`, so the
     shared checks see the new target.
   - **Environment:** the launcher calls
     `python3 -I setup/toolchains.py launch-env --base <FROM ref>`. It
     prints validated `NAME=VALUE` lines for the default toolchains verified
     on the current base, and one warning per toolchain verified elsewhere.
     The image `PATH` comes from
     `podman image inspect --format '{{range .Config.Env}}…'`. The launcher
     passes `--env PATH=<image PATH>:<toolchain entries>` and the other
     variables as `--env NAME=VALUE`.
   - **Why entries are appended:** Claude Code runs on the image's `node`
     (`#!/usr/bin/env node`), and image tools use its `python3`. Appended
     entries never replace them. `env.sh`, used explicitly in one command,
     puts its entries first. Names must match `[A-Z_][A-Z0-9_]*`
     and must not be variables the wrapper protects, such as `HOME`,
     `CLAUDE_CONFIG_DIR`, the proxy and CA variables, or `CONTAINER_HOST`.

6. **Default conflicts and dependencies are checked at `add` and `remove`.**
   - Two default toolchains must not share a command name or an
     environment variable name.
   - The PATH order is then irrelevant, and a new session's environment
     depends only on the set of installed toolchains.
   - A second Java version is installed with `"default": false` and used
     through its `env.sh`.
   - `add` fails on a missing or cyclic `requires`. `remove` fails while
     another toolchain requires the target.
   - A default toolchain that requires a non-default one is rejected, so the
     default environment never depends on `env.sh`.

7. **Writable locations for toolchain caches.**
   - Sessions keep their current writable locations: the workspace
     (executable), `/tmp`, `/var/tmp` and `/run` (`noexec`), and the state
     directories.
   - In shared-state mode `/claude-home` itself is read-only, so recipes
     point caches to `/tmp` with literal values.
   - Tools that execute files from their temporary directory are told
     through `notes` to use a directory under the workspace, for example
     `go test` with `GOTMPDIR`.
   - No new writable or executable mount is added. Making `/tmp` executable
     would be a policy change of its own.

8. **Shared-code placement.**
   - `setup/toolchains.py` is agent-agnostic: names come from `PROFILE`.
   - It is added to `MANIFEST` and `SHARED_CODE`, so qualification binds its
     digest, and to `control.py`'s trusted installation files, because
     restricted launches execute it.
   - `tests/test_toolchains.py` is a new shared test, listed in
     `SHARED_TESTS`.
   - After the merge, a new tag `sandbox-ref-13` marks the shared state for
     propagation.

9. **Instructions for the agent.**
   - The README documents a one-line addition for the operator's
     `CLAUDE.md`: "Read /toolchains/toolchains.md before using or looking
     for build tools."
   - `toolchains.md` carries the rules, so the line stays the same as
     toolchains change.

## Risks / Trade-offs

- **A toolchain with an unsafe `env.sh`.** The file is generated from
  validated names and quoted values, never copied from the source, so a
  recipe cannot inject commands.
- **A toolchain that runs but misbehaves.** The check only proves that the
  toolchain starts. That is the same trust the operator places in any
  image; the provenance is recorded in the manifest.
- **Disk use and replacement.** Each toolchain is a full copy, about 300 MB
  for a JDK. `list` shows the sizes. An old directory is deleted only after
  the index points to the new one.
- **Hosts where the library cannot be private** (for example DrvFs without
  metadata). The library uses native Linux storage by default, and the
  launcher fails with the same guidance as for state directories.
- **Rust needs a linker.** The runtime image has no `cc` or glibc
  development files. The example is verified with the musl target linked by
  `rust-lld`, from an operator-built image that adds that target. If that
  fails, the README documents Rust as unsupported without a linker toolchain,
  and the result is recorded in the validation record.
- **Tools that need an executable temporary directory** (Go, some Gradle
  native libraries). This is documented through `notes`. Changing `/tmp` is
  out of scope.
- **SELinux and AppArmor hosts.** These are untested and documented as such;
  the operator profiles the tools.
- **Maintenance pulls are outside runtime filtering**, like image builds.
  This is already documented for maintenance.

## Migration Plan

1. Merge to `main` and tag `sandbox-ref-13`. The operator pushes.
2. Run `--container-setup` on this host, the Rocky Linux 9 lab host and the
   newer WSL host. Add the example Temurin 21 recipe with maintenance
   authorization, then check `java -version` in a provider session started
   before the `add`.
3. Record the results, then archive with the spec sync.
4. Propagate to codex, opencode, pi and antigravity through separate
   changes.

Rollback: revert the merge. The library directory remains on disk and is
ignored by an older launcher.
