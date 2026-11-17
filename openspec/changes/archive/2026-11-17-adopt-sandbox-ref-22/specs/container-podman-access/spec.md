# Spec Delta

## MODIFIED Requirements

### Requirement: Access policy applies across launch modes
The wrapper SHALL apply the same access policy in Claude and `--container-shell` modes, including when combined with `--container-build` or `--container-git-worktree`. Restricted modes SHALL reject exact socket opt-in in every composition, including YOLO and native permission settings. Host Podman SHALL remain required for image operations and for launching the outer container, regardless of the opt-in. A delegated session SHALL also receive private tmpfs mounts for the nested Podman client's storage:
- `/var/lib/containers`, 256 MiB;
- `/run/containers`, 64 MiB.

Both mounts SHALL be `noexec` and owned by the caller.

#### Scenario: Shell mode follows the opt-in
- **WHEN** the caller selects unrestricted networking and launches with `--container-shell`, with and without `CLAUDE_CONTAINER_PODMAN=1`
- **THEN** only the enabled launch receives the socket mount and `CONTAINER_HOST`

#### Scenario: Build and workspace options preserve the access policy
- **WHEN** the caller selects unrestricted networking and explicitly authorized maintenance with `--container-build --container-git-worktree` and a Claude argument in either access mode
- **THEN** the image build and parent workspace mount retain their existing behavior
- **AND** only the enabled launch receives the socket mount and `CONTAINER_HOST`

#### Scenario: Host Podman is missing
- **WHEN** the wrapper starts without Podman installed on the host, regardless of `CLAUDE_CONTAINER_PODMAN`
- **THEN** it fails with the existing host Podman prerequisite error

#### Scenario: Delegated storage mounts
- **WHEN** an unrestricted session starts with `CLAUDE_CONTAINER_PODMAN=1`
- **THEN** it receives the socket mount, `CONTAINER_HOST` and the two private tmpfs mounts, and a session without delegation receives none of them
