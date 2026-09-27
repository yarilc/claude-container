# Design

## Context

The image uses Debian Bookworm slim and installs system tools in one `apt-get install --no-install-recommends` command in `Containerfile`. The launcher runs the image with a read-only root filesystem and does not add container capabilities or alter namespace settings.

## Goals / Non-Goals

**Goals:**

- Make `python3` and `bwrap` available on `PATH` in both Claude and container-shell modes.
- Keep package installation within the existing Debian apt workflow.

**Non-Goals:**

- Install Python packages or add a `python` alias.
- Change Podman security, capability, or namespace settings to enable particular Bubblewrap sandbox operations.

## Decisions

- Install the Debian `python3` and `bubblewrap` packages in the existing apt package list. This uses the distribution packages already aligned with the image's Debian base and avoids adding another package manager or a source-build step.
- Document both tools in the README's included-tools section. Refer to Bubblewrap's executable as `bwrap` so users can invoke the command directly.
- Validate the image by rebuilding it and invoking `python3 --version` and `bwrap --version` from a container. These checks verify the command-availability contract in the spec.

## Risks / Trade-offs

- Bubblewrap may be installed while namespace-dependent sandbox invocations remain unavailable under a particular host kernel or rootless Podman configuration. Keep this change scoped to package and command availability; evaluate namespace or capability changes separately if a target workflow requires them.
- The Debian package versions follow the base image repositories and can change when the image is rebuilt. This matches the current package-management approach.

## Migration Plan

Rebuild the local image with `./claude-container.sh --container-build`, then verify both commands in a running container. No host configuration or persisted data migration is required. To roll back, remove the two packages from the Containerfile and revert the README inventory entry, then rebuild the image.
