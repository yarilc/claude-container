# Tasks

## 1. Add the parent-directory mount option and its usage documentation

- [x] 1.1 Add boolean parsing for `--container-git-worktree` and derive a separate workspace mount path from the existing physical `WORKSPACE`; update the single workspace volume while retaining `WORKSPACE` for working directory and naming. Verify `bash -n claude-container.sh` and inspect captured Podman arguments for default and enabled launches from a worktree root.
- [x] 1.2 Verify argument assembly using a temporary Podman stub and a copy of the wrapper, accommodating the existing socket preflight in that temporary harness if needed. Check direct-parent selection from a nested directory and a non-Git directory, paths containing spaces, repeated flags, preservation of working directory and naming prefix, forwarding of Claude arguments, and composition with shell and build modes. Keep stubs outside a `noexec` directory, use no credentials or remote repository, and remove the temporary harness afterward.
- [x] 1.3 Add the option to wrapper help and revise its mount summary; verify `--container-help` describes the parent mount and succeeds without starting a container.
- [x] 1.4 Update the README's recognized-option list and add a worktree section with `cd /path/to/root/main`, an absolute wrapper path or documented alias, and a shell-mode example. Verify the text states the mounted path, initial directory, lack of Git discovery, behavior from subdirectories, writable sibling access, and limitation for metadata outside the selected parent.
- [x] 1.5 Revise existing README mount and security paragraphs to describe both modes, including that selecting a parent can expose the host home directory. Review these paragraphs against the actual selected volume and run `git diff --check`.

## 2. Verify runtime integration

- [x] 2.1 When Podman is available, create a disposable local Git repository and sibling linked worktree whose shared metadata is beneath their common parent. Launch from the linked worktree with `--container-git-worktree --container-shell`; verify the initial `pwd`, successful `git status` and `git worktree list`, and creation/removal of a scratch file in the mounted parent. Confirm the source and destination volume paths match and remove the fixture afterward. If Podman is unavailable, record that limitation and the argument-assembly evidence from task 1.2 instead of claiming runtime verification.
- [x] 2.2 When Podman is available, complete the repository's wrapper regression checks: image build, default Claude startup and argument forwarding, configuration persistence, and a child `podman run` using a bind mount under the selected parent. Record outcomes and any environment limitations; use the temporary argument harness for supported checks when runtime execution is unavailable.
- [x] 2.3 Run `bash -n claude-container.sh`, `git diff --check`, and `openspec validate add-container-git-worktree --strict`; verify they pass and record the completed checks and remaining runtime limitations in this change.

## Verification Notes

- Argument assembly passed six temporary Podman-stub scenarios: default mount, parent mount, nested launch directory, non-Git directory, paths containing spaces, repeated option, preserved working directory and naming, Claude argument forwarding, and shell/build composition. The temporary stub and wrapper copy were removed.
- A real Podman shell launched from a local linked worktree. `git status` and `git worktree list` succeeded, a scratch file was created and removed under the mounted parent, and a child Alpine container saw the sibling worktree through a bind mount.
- `--container-build --help` rebuilt the runtime image and printed Claude Code help through the wrapper. A temporary host configuration directory persisted a file written from `--container-shell`.
- This environment exposes the Podman API socket to the test process at `/run/podman/podman.sock`; the wrapper's local socket preflight path was absent. For real-container checks only, a temporary wrapper copy skipped that local preflight and mounted the socket path reported by the Podman service. No repository runtime path was changed for the environment.
- An authenticated Claude session was not run; the credential-free `claude --help` invocation verified startup and argument forwarding.
- Final checks passed: `bash -n claude-container.sh`, `git diff --check`, and `openspec validate add-container-git-worktree --strict`.
