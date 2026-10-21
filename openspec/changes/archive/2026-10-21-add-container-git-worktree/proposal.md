# Proposal

## Why

Mounting only the current worktree hides Git metadata and sibling worktrees located in its parent directory. An explicit parent-directory mount lets Git commands inside the container resolve those references while Claude starts in the worktree selected by the caller.

## What Changes

- Add the boolean wrapper option `--container-git-worktree` to mount the immediate parent of the physical current directory, read/write, at the same absolute path inside the container.
- Keep the launch directory as the container working directory and the basis for container naming.
- Apply the option to both Claude and `--container-shell` sessions, consuming it instead of forwarding it to Claude.
- Select the parent directly, without detecting a Git repository or searching for a worktree root. Without the option, continue mounting the current directory.
- Update wrapper help and README usage, mount descriptions, and security boundaries. Include examples launched from `/path/to/root/main`, including shell mode, and explain sibling-directory access and references outside the selected parent.

## Capabilities

### New Capabilities

- `workspace-mounts`: Selection of the workspace bind mount, its relationship to the initial working directory, and the documented parent-directory option for worktree layouts.

### Modified Capabilities

None.

## Impact

- `claude-container.sh`: option parsing, separate mount-path selection, Podman volume arguments, and help text.
- `README.md`: examples and descriptions of writable filesystem access.
- Filesystem access expands to the selected parent and its descendants only when the caller supplies the option. Configuration and socket mounts retain their existing behavior.
- No runtime image changes or new dependencies are required. Existing `host-ca-trust` and `runtime-image` requirements are unaffected.
