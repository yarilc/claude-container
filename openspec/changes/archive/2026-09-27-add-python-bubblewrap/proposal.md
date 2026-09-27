# Proposal

## Why

The runtime image does not currently include Python 3 or Bubblewrap, so commands and workflows that depend on those tools cannot run directly inside the container. Adding them makes both tools available in the Claude Code environment without requiring host installations.

## What Changes

- Install the Debian `python3` and `bubblewrap` packages in the runtime image.
- Document Python 3 and Bubblewrap among the tools included in the image.

## Capabilities

### New Capabilities

- `runtime-image`: Defines the command-line tools available in the Claude Code runtime image.

### Modified Capabilities

None.

## Impact

- `Containerfile`: Adds two packages to the existing apt installation.
- `README.md`: Updates the included-tools list.
- Image build time and size increase slightly due to the added packages.
