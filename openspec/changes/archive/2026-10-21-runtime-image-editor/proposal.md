# Proposal

## Why

Commands that open a text editor fail inside the container. Claude Code's
`/memory` command reports "Couldn't open ./AGENTS.md in an editor" because the
runtime image has no editor installed and no `EDITOR` or `VISUAL` variable set.
Users who edit memory files or other documents from a Claude session have no
working editor.

## What Changes

- The runtime image installs `nano` as a terminal editor.
- The runtime image sets `EDITOR` and `VISUAL` to `nano`, so editor-aware
  commands use it without host configuration.
- The host's `EDITOR` and `VISUAL` are not forwarded into the container. A host
  value such as `vim` would name an editor the image does not provide.

## Capabilities

### New Capabilities

### Modified Capabilities
- `runtime-image`: adds a requirement that the image provides a terminal editor
  and that `EDITOR` and `VISUAL` name it.

## Impact

- `Containerfile`: `nano` added to the `apt-get install` list; `ENV` extended
  with `EDITOR` and `VISUAL`.
- `openspec/specs/runtime-image/spec.md`: one new requirement, through a delta
  spec in this change.
- Image size grows by the size of `nano` and its dependencies.
- No change to `claude-container.sh`, mounts, or the host environment.
- Not verified yet: that `nano` is available in the Debian bookworm repository
  used by the base image. This is checked by the build task.
