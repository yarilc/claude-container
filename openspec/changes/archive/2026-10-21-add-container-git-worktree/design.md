# Design

## Context

See `proposal.md` for motivation. `claude-container.sh` currently derives `WORKSPACE` using `pwd -P` and reuses it for container naming, `--workdir`, and the workspace `--volume`. Both launch modes share one `podman_args` array. Argument parsing consumes known wrapper flags and forwards other arguments through arrays.

The existing durable specs cover host CA trust and runtime tooling, so workspace selection belongs in the new `workspace-mounts` capability. The README currently describes the current directory as the writable workspace and says the wrapper does not mount the user's full home directory. The parent option makes that latter statement conditional: a launch from a direct child of the host home directory can select the home directory itself.

This design is included because the option changes the filesystem access boundary and benefits from an explicit distinction between the mount root and launch directory.

## Goals / Non-Goals

**Goals:**

- Keep the mount selection independent of the initial working directory and container naming.
- Preserve absolute host paths so Git references and child-container bind mounts resolve consistently.
- Make the enlarged writable scope understandable before the user selects the option.

**Non-Goals:**

- Automatic Git discovery, worktree creation, or repair of Git metadata.
- Discovering a common ancestor for arbitrary worktree locations or mounting paths outside the selected parent.
- New environment settings, runtime image changes, or a configurable number of ancestor levels.

## Decisions

### Separate the workspace mount path from WORKSPACE

Keep `WORKSPACE` as the physical launch directory. Track the boolean flag using the existing parser style and derive a separate mount path after parsing: the workspace by default, or its immediate parent using `dirname --` when enabled. Use that path for both sides of the single workspace volume argument. Continue using `WORKSPACE` for `--workdir` and the naming prefix.

Reassigning `WORKSPACE` to its parent would also move the initial working directory and rename containers. Adding a second overlapping volume would be redundant. Selecting one volume root keeps those behaviors explicit and avoids both alternatives.

Use the existing quoted array construction to preserve spaces in paths. Parent selection follows the physical path already captured by `pwd -P`, including when the caller reached the directory through a symlink. No special ancestor policy is added; normal filesystem parent semantics and Podman's existing validation apply.

### Make the flag independent of Git inspection

Consume `--container-git-worktree` without a value or forwarding it to Claude. Repeated occurrences enable the same mode. Since the existing parser handles wrapper flags throughout the argument list, follow that behavior for this option as well.

Do not invoke Git on the host or require a repository. Searching for a worktree root would conflict with the confirmed immediate-parent behavior, particularly when launching from a subdirectory. Shared Podman arguments make the option work in shell mode and alongside explicit image builds.

### Keep the parent writable and at its host path

Git operations can need to update shared metadata inside the parent, so the selected parent uses `:rw`. Keeping identical source and destination paths preserves absolute references as well as child bind-mount compatibility. A read-only parent with a writable worktree overlay would prevent some metadata updates and require overlapping mounts.

Other mounts, user mapping, container root read-only mode, and CA trust behavior are outside this change.

### Document actual invocation and access scope

Add the option to wrapper help, revise the opening mount description, and add it to the README's handled-option list. Add a dedicated worktree usage section with an absolute wrapper path or the already documented `claude` alias, so examples remain runnable after changing to another project directory:

```bash
cd /path/to/root/main
/absolute/path/to/claude-container.sh --container-git-worktree
/absolute/path/to/claude-container.sh --container-git-worktree --container-shell
```

Explain the `/path/to/root` mount and `/path/to/root/main` starting directory, direct parent selection from subdirectories, writable sibling contents, and references outside the parent. Update the existing mount and security paragraphs to account for this mode, including the possibility that the selected parent is the caller's home directory. The recommended usage starts from a worktree root whose required metadata resides beneath its parent.

## Risks / Trade-offs

- Parent and sibling files become writable, potentially including unrelated files or the host home directory. Mitigation: keep the option explicit and document the exact scope and the launch-directory requirement.
- Git metadata can reside outside the selected parent. Mitigation: explain the layout limitation; do not promise arbitrary worktree discovery or add extra mounts.
- Launching from a nested subdirectory selects a different parent than launching from the worktree root. Mitigation: specify this behavior and include a corresponding argument-assembly check.
- A Git smoke check alone would not prove default isolation or argument forwarding. Mitigation: inspect assembled Podman arguments in both modes, then use a local Git worktree fixture for integration when Podman is available.

## Migration Plan

No image rebuild or data migration is required for the wrapper change itself. Existing invocations retain the default workspace mount. Users opt in from their worktree root using the new flag. Rollback consists of reverting the wrapper and documentation changes and removing the option from invocations.
