# workspace-mounts Specification

## Purpose

Define how the wrapper exposes host workspace directories inside the container, including an explicit parent-directory mount for Git worktree layouts while preserving the launch directory.

## Requirements

### Requirement: Default workspace mount
Without `--container-git-worktree`, the wrapper SHALL mount the physical current directory read/write at its same absolute path inside the container.

#### Scenario: Default launch from a worktree
- **WHEN** the caller launches the wrapper from `/path/to/root/main` without `--container-git-worktree`
- **THEN** the workspace volume is `/path/to/root/main:/path/to/root/main:rw`
- **AND** the wrapper does not add a workspace volume for `/path/to/root`

### Requirement: Parent-directory workspace mount
With `--container-git-worktree`, the wrapper SHALL replace the current-directory workspace mount with a read/write mount of its immediate physical parent at the same absolute path. It SHALL select that parent directly, without detecting or requiring a Git repository.

#### Scenario: Parent selected from the launch directory
- **WHEN** the caller launches the wrapper from `/path/to/root/main` with `--container-git-worktree`
- **THEN** the workspace volume is `/path/to/root:/path/to/root:rw`
- **AND** the wrapper does not add a separate workspace volume for `/path/to/root/main`

#### Scenario: Launch from a worktree subdirectory
- **WHEN** the caller launches the wrapper from `/path/to/root/main/src` with `--container-git-worktree`
- **THEN** the workspace volume is `/path/to/root/main:/path/to/root/main:rw`
- **AND** the wrapper does not search for the worktree root to select `/path/to/root`

#### Scenario: Launch outside a Git repository
- **WHEN** the caller launches the wrapper from a directory outside a Git repository with `--container-git-worktree`
- **THEN** the wrapper selects that directory's immediate physical parent without Git validation

#### Scenario: Directory path contains spaces
- **WHEN** the caller launches the wrapper from `/path/to/project root/main` with `--container-git-worktree`
- **THEN** the workspace volume is passed as a single argument with value `/path/to/project root:/path/to/project root:rw`

### Requirement: Launch directory is preserved
The wrapper SHALL use the physical current directory as the container working directory and the basis for container naming, whether or not `--container-git-worktree` is present.

#### Scenario: Claude starts in the selected worktree
- **WHEN** the caller launches from `/path/to/root/main` with `--container-git-worktree`
- **THEN** the container working directory is `/path/to/root/main`
- **AND** the container name uses `main` as its prefix under the existing naming rules

### Requirement: Wrapper option composition
The wrapper SHALL consume `--container-git-worktree` as a boolean option without forwarding it to Claude. It SHALL support this option with `--container-shell` and `--container-build` and preserve other Claude arguments under the existing forwarding rules.

#### Scenario: Claude arguments are forwarded
- **WHEN** the caller launches with `--container-git-worktree -p "inspect this worktree"`
- **THEN** Claude receives `-p` and `inspect this worktree` as separate arguments
- **AND** Claude does not receive `--container-git-worktree`

#### Scenario: Shell mode uses the parent mount
- **WHEN** the caller launches from `/path/to/root/main` with `--container-shell --container-git-worktree`
- **THEN** the shell starts in `/path/to/root/main` with `/path/to/root` mounted read/write at its host path

#### Scenario: Explicit image build and parent mount
- **WHEN** the caller launches with `--container-build --container-git-worktree`
- **THEN** the wrapper builds the image before starting the container with the parent-directory workspace mount

### Requirement: Git metadata within the parent is accessible
With the parent-directory option, Git commands in the container SHALL be able to access shared metadata and sibling worktrees contained within the mounted parent, subject to existing filesystem permissions.

#### Scenario: Worktree points at metadata under the parent
- **GIVEN** `/path/to/root/main` is a worktree whose Git metadata resolves within `/path/to/root`
- **WHEN** the caller starts the container from that worktree with `--container-git-worktree` and runs `git status` and `git worktree list`
- **THEN** Git resolves the shared metadata and lists the worktrees without errors caused by those paths being outside the workspace mount

### Requirement: Document parent-directory usage and access scope
Wrapper help SHALL list `--container-git-worktree` and explain the parent mount. The README SHALL show usage from a worktree root, shell-mode composition, the mounted and initial paths, direct parent selection, writable sibling access, and the limitation for Git references outside that parent.

#### Scenario: Read documented worktree usage
- **WHEN** a user reads the README instructions for `--container-git-worktree`
- **THEN** an example changes directory to `/path/to/root/main` and invokes the wrapper using an absolute script path or the documented alias
- **AND** the text explains that `/path/to/root` is mounted read/write while Claude starts in `/path/to/root/main`
- **AND** it explains that sibling contents become writable, no Git root detection occurs, and references outside the parent are not exposed by this option
- **AND** an example combines the option with `--container-shell`

#### Scenario: Discover the option in wrapper help
- **WHEN** the caller runs `--container-help`
- **THEN** help lists `--container-git-worktree` and describes mounting the parent of the current directory
