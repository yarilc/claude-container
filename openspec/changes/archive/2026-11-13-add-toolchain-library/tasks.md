# Tasks

## 1. Library module, test first

- [x] 1.1 On a branch `add-toolchain-library`, add the shared
  `tests/test_toolchains.py` and list it in `SHARED_TESTS`. Cover, with
  synthetic archives and a fake engine:
  - recipe validation: unknown keys, names, relative paths, tag-only
    images, literal values with NUL or newline;
  - `requires`: missing, cyclic, a default requiring a non-default, and
    `remove` of a required toolchain;
  - `notes` rendering;
  - archive SHA-256 mismatch;
  - unsafe members: absolute paths, `..`, devices, escaping links;
  - setuid and setgid clearing, and file permissions;
  - staging and atomic replace or remove, and the library lock;
  - default conflicts;
  - the generated `env.sh`, `toolchains.md` and `index.json`, with no host
    paths;
  - `launch-env` output, with entries appended after the image `PATH`,
    protected variable names, and the warning for a different base;
  - unsafe library ownership, mode and overlap.

  Verify that the suite fails because `setup/toolchains.py` does not exist.
- [x] 1.2 Implement `setup/toolchains.py` with the `add`, `list`, `remove`,
  `verify` and `launch-env` operations (design decisions 1–4, 6 and 7). It
  must run on Python 3.9 and contain no agent identifiers. Verify that
  `tests/test_toolchains.py` and `tests/test_alignment.py` pass.
- [x] 1.3 Add `setup/toolchains.py` to `setup/common.py` `MANIFEST`, to
  `network/qualification_records.py` `SHARED_CODE`, and to the trusted
  installation files in `network/control.py`. Verify that
  `tests/test_setup.py` and `tests/test_qualification.py` pass, updating
  their expected file lists.

## 2. Launcher

- [x] 2.1 In `tests/test_wrapper.py`, add the following cases with the fake
  engine:
  - `--container-toolchain` dispatch: used alone, before the network mode;
  - the library mount with `ro,nosuid,nodev` at `/toolchains`;
  - private creation when the library is missing;
  - unsafe library rejection before any container operation;
  - overlap with the workspace and state in both directions;
  - `CLAUDE_CONTAINER_TOOLCHAINS=0`, and invalid values of it;
  - `--mount-target /toolchains` in restricted modes;
  - the `PATH` from `launch-env`, appended after the image's, the
    `--env` values, and the single warning for a different base.

  Verify that the new cases fail on the current launcher.
- [x] 2.2 Implement design decision 5 in `claude-container.sh`, including
  the help text. Verify that `bash -n claude-container.sh` passes and that
  `tests/test_wrapper.py` passes.

## 3. Real-engine checks

- [x] 3.1 Add runtime tests to `tests/test_runtime.py`, credential-free and
  without network for the toolchain sources:
  - an archive-sourced toolchain (a shell-script command) added with the
    real command, then used through `env.sh` and by name in a new session;
  - an image-sourced toolchain from a locally built `FROM scratch` image,
    pinned by its local digest;
  - a check command that fails, leaving the library unchanged;
  - an offline-mode session started before `add`, which sees the new
    toolchain without a restart and still has no network;
  - writes under `/toolchains` failing inside the session;
  - a default toolchain that provides `node` and `python3`, with both still
    resolving to the image's versions in a new session.

  Verify that `bash tests/run-runtime.sh` passes with the current runtime
  image.

## 4. Documentation and roadmap

- [x] 4.1 Add a README "Toolchains" section:
  - the library, the recipe format, the commands and maintenance;
  - the six example recipes: Temurin 21, Maven 3.9 (requires `java21`),
    Go, Node.js 24, Python 3.13 and Rust;
  - `requires`, `notes` and literal values, with cache locations under
    `/tmp` and the `GOTMPDIR` note;
  - the one-line `CLAUDE.md` instruction;
  - the default environment and conflict rule;
  - the base verification;
  - the note that SELinux and AppArmor are untested.

  Update the help-related README parts, `AGENTS.md` (the shared module),
  and `docs/setup.md` (requalification). Verify that every
  `CLAUDE_CONTAINER_TOOLCHAINS*` variable and every `--container-toolchain`
  operation is documented in both the help text and the README.
- [x] 4.2 Add three roadmap entries to `todo.md`, in a new section dated
  2026-11-13: SELinux support, AppArmor support, and a proxy ACL management
  CLI. The ACL CLI entry names network access for toolchain dependencies as
  its first use case. Verify that the entries are unchecked and reference
  this change.

## 5. Validation and publication

- [x] 5.1 Run the full unit discovery on executable, private, native
  temporary storage. Verify that there are no failures, apart from known
  timing-sensitive tests that pass on a rerun, which are recorded as such.
- [x] 5.2 Verify the six example recipes manually, with
  `CLAUDE_CONTAINER_MAINTENANCE=1` and pulled, digest-pinned images or
  checksummed archives. Fix their exact versions, digests and SHA-256s in
  the README. For each example:
  - `add` succeeds;
  - its check runs in an offline session through `env.sh`;
  - default toolchains also run by name in a new session.

  Also check:
  - `mvn -v` through `env.sh` loads Java;
  - `go test` passes on a sample module with `GOTMPDIR` under the
    workspace;
  - for Rust, `cargo build` of a sample crate with the musl target and
    `rust-lld`. If it fails, document Rust as unsupported without a linker.

  Remove the toolchains afterwards and record each source identity and
  result.
- [x] 5.3 Add a dated validation record to `docs/validation.md` with the
  results of 1.1–5.2 and the operator setups as pending. Verify that
  `git diff --check` is clean and that
  `openspec validate add-toolchain-library --strict` passes.
- [x] 5.4 Commit on the branch with the co-author trailer, merge into
  `main` with `--no-ff`, and create the annotated tag `sandbox-ref-13` on
  the merge. Verify that `git log --oneline -3` shows the merge and that
  `git tag -l sandbox-ref-13` lists the tag.

## Workflow follow-up

- The operator pushes `main` and the tag, then runs `--container-setup` on
  this host, the Rocky Linux 9 lab host and the newer WSL host. They add the
  Temurin 21 recipe and check `java -version` in a provider session started
  before the `add`. The results are added to `docs/validation.md`.
- Sync the delta specs and archive this change.
- Propagate `sandbox-ref-13` to codex, opencode, pi and antigravity through
  separate changes.
