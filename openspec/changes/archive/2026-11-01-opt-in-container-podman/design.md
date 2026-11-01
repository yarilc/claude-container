# Design

## Context

See `proposal.md` for motivation. The wrapper currently validates `/run/user/$(id -u)/podman/podman.sock` unconditionally, then includes both its mount and `CONTAINER_HOST` in the common `podman_args` array. Claude and shell modes share this array. The image already installs the Podman client. The README and repository guidance currently describe the API socket as mandatory.

## Goals / Non-Goals

**Goals:**
- Apply one consistent access decision to validation and runtime arguments.
- Allow ordinary startup without an API service while preserving the existing enabled configuration.
- Keep host image builds, container naming, workspace mounts, and argument forwarding intact.

**Non-Goals:**
- Removing the client binary or maintaining separate images.
- Adding a nested engine, new socket locations, or privileged execution.
- Blocking independently supplied remote services or sockets already exposed through user-selected workspace/configuration mounts. This change controls the host API access granted by the wrapper; it does not add network isolation or inspect arbitrary mounted content.

## Decisions

### Use an exact, fail-closed opt-in

Derive a local boolean from `${CLAUDE_CONTAINER_PODMAN:-}` using exact string equality with `1`, safe under `set -u`. All other values disable access, including `true` and `yes`. This follows the requested exact value rather than reusing the broader boolean parsing of CA trust or `CLAUDE_YOLO`. Rejecting other values would introduce an unnecessary startup failure; silently treating them as disabled grants no authority.

### Gate both validation and the authority grant

Resolve and validate the existing rootless socket only in the enabled branch. Remove the socket mount and `CONTAINER_HOST` from the unconditional array and append them together only when enabled. Keep the existing socket error actionable. One shared array ensures Claude and shell modes cannot diverge. Merely hiding the client or unsetting `CONTAINER_HOST` while still mounting the socket would leave the API accessible.

### Retain the host prerequisite and the installed client

The host `podman` executable still performs image checks, builds, container naming, and launch. Its prerequisite check remains unconditional. The installed client does not itself grant host API access, so retain the image and default filesystem restrictions. No new environment forwarding is needed; the wrapper consumes the opt-in on the host.

### Update all guidance that assumes a mandatory socket

Adjust help, the README introduction/setup/usage/security sections, and `AGENTS.md` runtime and testing guidance. Separate mandatory rootless host setup from optional API-service setup, show opt-in for child-container workflows, and explain the breaking default. Existing capability specs cover image tools, workspace mounts, and CA trust, so the API contract belongs in the new `container-podman-access` capability without modifying those specs.

## Risks / Trade-offs

- [Existing child-container workflows stop working by default] → Provide migration examples using `CLAUDE_CONTAINER_PODMAN=1`.
- [Users assume the opt-in removes all Podman binaries or blocks every possible remote endpoint] → Explain that it controls wrapper-provided access to the host API; validate absence of the socket mount and remote environment configuration.
- [Enabled access retains broad host-user authority] → Keep it explicit and document its scope without broadening mounts or adding privileges.
- [Socket validation alone cannot prove a service is listening] → Preserve the current file-type check and existing documented remote API verification for enabled access.

## Migration Plan

Ship the script and documentation changes together. Users who need child containers set `CLAUDE_CONTAINER_PODMAN=1` in their launch environment and retain the documented socket setup. Other users need only functional host Podman. No image rebuild or persistent-state migration is required specifically for this change. Rolling back the wrapper restores unconditional socket access and its mandatory socket prerequisite.
