# Design

## Context

The runtime image is built from `Containerfile` on `node:22-bookworm-slim`. Its
package list is in a single `apt-get install` step, and its environment is set
with `ENV` near the top. The image has no editor: `less` and `patch` are the only
text tools that are not general-purpose editors. The container runs with
`--read-only`, and the only writable mounts are the workspace and `~/.claude`
(`/claude-home/.claude`). See `specs/runtime-image/spec.md` for the requirements.

## Goals / Non-Goals

**Goals:**
- Editor-aware commands work inside the container without host configuration.
- The editor needs no writable home directory and no `/tmp` space.

**Non-Goals:**
- Installing a full IDE or language servers.
- Changing `claude-container.sh`, mounts, or host environment handling.

## Decisions

**`nano` over `vim` or `vim-tiny`.** `nano` writes edits directly to the file and
needs no scratch space. `vim` creates swap and state files under `$HOME`, which
resolves to `/claude-home`, a read-only path in the container apart from the
mounted `.claude` directory. `vim-tiny` avoids the size problem but keeps the
same write behavior, so it was rejected for this use.

**Default set in `Containerfile` `ENV`, not forwarded from the host.** Setting
`EDITOR=nano` and `VISUAL=nano` in the image keeps the behavior fixed and
reproducible. Forwarding the host's values would make the editor depend on the
host, and a host value naming an editor the image lacks would reproduce the
original failure.

**Disable nano's history log in `/etc/nanorc`.** Debian's `/etc/nanorc` sets
`historylog`, and nano then fails to create `~/.local/share/nano` on the read-only
home, printing a warning on every start. Appending `unset historylog` in the image
removes the warning without a new mount. The alternative, a tmpfs on
`/claude-home/.local`, adds a mount that AGENTS.md asks to avoid. The cost is that
search history is not kept between sessions, which the container does not need.

**Install in the existing `apt-get` step.** One added package keeps the layer
count and cache cleanup unchanged.

## Risks / Trade-offs

- **`nano` missing from the bookworm repository** -> the build fails visibly.
  Mitigation: the build task checks `nano --version` in the built image.
- **Image size grows** -> `nano` and its dependencies add a small amount.
  Mitigation: installed with `--no-install-recommends`, as the rest of the list.
- **Users who want `vim` must install it themselves or set `EDITOR`** -> they can
  set `EDITOR` in their own Claude settings; the image default does not restrict
  that.

## Migration Plan

Rebuild the image with `./claude-container.sh --container-build`. No data or
mount changes. Rollback is reverting the `Containerfile` change and rebuilding.
