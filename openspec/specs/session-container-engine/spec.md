# session-container-engine Specification

## Purpose

Give every wrapper's sessions a private, rootless container engine that runs the operator's library images inside the session's own network and filesystem boundaries, so agents can run container-based tests without host Podman authority.

## Requirements

### Requirement: Engine for sessions with library images
A session SHALL get a private container engine when the toolchain library is mounted and its image store holds at least one image. This SHALL apply in every network mode, to application and `--container-shell` sessions alike. Otherwise the launcher SHALL create no engine, and `CONTAINER_HOST` and `DOCKER_HOST` SHALL be absent from the session.

#### Scenario: Library with an image
- **GIVEN** the operator added a toolchain with an image
- **WHEN** an offline session starts
- **THEN** the session has a running engine and `CONTAINER_HOST` names it

#### Scenario: Library without images
- **WHEN** a session starts and the library holds only file toolchains, or no toolchains
- **THEN** no engine container exists for it, and `CONTAINER_HOST` and `DOCKER_HOST` are absent

#### Scenario: Library mount disabled
- **WHEN** a session starts with `CLAUDE_CONTAINER_TOOLCHAINS=0`
- **THEN** no engine container exists for it, even if the library holds images

#### Scenario: First image added during a session
- **GIVEN** a session started without an engine because the library held no image
- **WHEN** the operator adds the first image toolchain
- **THEN** that session still has no engine, and the next session started has one

### Requirement: Loopback endpoint for the session
The session SHALL reach its engine only through a loopback TCP endpoint in the session's own network namespace. The endpoint SHALL be given as `CONTAINER_HOST=tcp://127.0.0.1:<port>` and, for Docker-API clients, as `DOCKER_HOST` with the same value. No engine or host Unix socket SHALL be mounted into the session. The endpoint SHALL serve only that session's engine.

#### Scenario: Client in the session
- **WHEN** a process in the session runs `podman info` with the provided `CONTAINER_HOST`
- **THEN** the engine answers and reports rootless operation

#### Scenario: Docker-API client
- **WHEN** a test framework in the session reads `DOCKER_HOST` and starts a container through the Docker-compatible API
- **THEN** the container runs in the session's engine

#### Scenario: Two sessions
- **WHEN** two sessions with engines run at the same time
- **THEN** each session's endpoint reaches only its own engine, and neither sees the other's containers

### Requirement: Engine shares the session network boundary
The engine and every container it runs SHALL have no network path other than the session's:
- an offline session's engine SHALL reach no external service;
- a provider session's engine SHALL reach only what the session's proxy policy allows, through that proxy;
- an unrestricted session's engine SHALL have the session's network.

#### Scenario: Offline nested container
- **WHEN** a container started by an offline session's engine tries direct DNS, TCP or UDP to an external address, or the engine tries to pull an image
- **THEN** every attempt fails, and no network path appears that the session lacks

#### Scenario: Unrestricted pull
- **WHEN** an unrestricted session's engine pulls an image that is not in the library
- **THEN** the pull uses the session's network and the image stays in the session's storage

### Requirement: Engine mounts only the workspace and the image store
The engine container SHALL mount these host paths and no other:
- the session workspace, and the worktree parent when selected, at the same absolute paths;
- the library's image store, read-only;
- the host CA bundle, read-only, when host CA trust is enabled.

It SHALL NOT mount state, configuration, credentials, the installation or any host Podman socket.

#### Scenario: Workspace bind from a nested container
- **WHEN** a process in the session runs a container that bind-mounts `$PWD` from inside the workspace
- **THEN** the nested container sees the workspace files at that path
- **AND** files that the nested container's root creates there belong to the caller

#### Scenario: Host path outside the workspace
- **WHEN** a nested container bind-mounts a path outside the workspace, such as `/home` or `/etc`
- **THEN** it sees the engine image's own files, never the host's, and no state or credential directory is reachable

### Requirement: Engine carries no secrets
The engine container SHALL receive no credential, agent variable or proxy credential. It SHALL keep `/run/secrets` masked by an empty read-only mount. It SHALL pass no host mounts to nested containers, so nested containers receive no engine-host secret either.

#### Scenario: Nested secrets directory
- **WHEN** a nested container lists `/run/secrets`
- **THEN** the directory is absent or empty

#### Scenario: Engine environment
- **WHEN** the engine container's environment is inspected
- **THEN** it contains only fixed engine settings, and no variable forwarded from the caller

### Requirement: Session-owned engine storage
The engine's writable storage SHALL belong to the session: containers, volumes, and images built, pulled or loaded during the session. It SHALL be removed with the engine when the session ends, including after failure, interruption or a stale session that a later launch cleans up. Only the library's image store SHALL persist between sessions.

#### Scenario: Image built in a session
- **WHEN** a session builds an image with its engine and a later session lists its engine's images
- **THEN** the built image is absent, and the library images are present

#### Scenario: Interrupted session
- **WHEN** a session with an engine ends abnormally
- **THEN** its engine container and storage are removed by the session-owned cleanup that applies to the session's other resources

### Requirement: Library images run offline from a read-only store
The engine SHALL resolve library images by their recorded references, including digest references, without network and without copying them into session storage. It SHALL NOT be able to change the store. An image added to the library during a session SHALL be usable by that session's engine without restart.

#### Scenario: Offline run by digest
- **WHEN** an offline session runs a library image by its `@sha256:` reference
- **THEN** the container starts without a pull

#### Scenario: Store is read-only to the engine
- **WHEN** the session asks its engine to remove a library image
- **THEN** the engine refuses, and the library is unchanged

#### Scenario: Image added during a session
- **WHEN** the operator adds an image toolchain while a session with an engine runs
- **THEN** that session's engine lists and runs the new image without a restart

### Requirement: Nested containers have private process and host-name views
Every nested container SHALL have its own procfs, showing only its own PID namespace. It SHALL have its own UTS namespace whose host name defaults to its container ID, as with a host engine.

#### Scenario: Process view
- **WHEN** a nested container started with a private PID namespace lists `/proc`
- **THEN** its PID 1 is its own process, and no process of the engine or of another nested container is visible

#### Scenario: Host name
- **WHEN** a nested container prints its host name
- **THEN** it is the container's short ID

### Requirement: Engine budgets
The engine container SHALL receive the session's memory, CPU and process budgets. Their enforcement, fallback, verification and announcement SHALL follow the agent container's rules. Where the engine's cgroup is enforced, the budgets SHALL bound the engine and all its nested containers together. Explicit limits requested for nested containers are not guaranteed.

#### Scenario: Delegated controllers
- **WHEN** the rootless engine delegates `memory`, `cpu` and `pids` with the systemd cgroup manager
- **THEN** the engine container's effective limits equal the session budgets, and the launch verifies them

#### Scenario: Cgroupfs engine
- **WHEN** the rootless engine uses the cgroupfs cgroup manager
- **THEN** the launch announces the engine's unenforced budgets with the same reasons as the agent's, and applies the process rlimit fallback where the rules allow it

### Requirement: Fixed engine hardening exceptions
The engine container SHALL run as an unprivileged user. Over the standard policy it SHALL relax only what nested containers and image operations need:
- the user-namespace helper capabilities;
- the chroot capability, for layer extraction and builds;
- the FUSE and TUN devices;
- an unmasked procfs;
- disabled SELinux labelling;
- `sethostname` and `setdomainname` over the host's default seccomp profile.

The wrapper SHALL NOT widen these for a nested tool.

#### Scenario: Engine container inspected
- **WHEN** an engine container is inspected
- **THEN** its user, capabilities, devices, masks, labels and seccomp profile match exactly the documented exceptions

#### Scenario: Image operations in a session
- **WHEN** a session builds an image with a `RUN` step, or loads an image whose layers its engine does not have
- **THEN** the operation succeeds within these exceptions

#### Scenario: Tool needs more
- **WHEN** a nested tool fails because it needs a privilege outside these exceptions
- **THEN** the wrapper adds nothing, and the limitation is recorded in the validation record

### Requirement: Engine lifecycle follows the session
The launcher SHALL start the engine before the application runs and verify that it answers as a rootless engine. A failure SHALL stop the launch before the application starts, naming the engine. The engine SHALL be stopped and removed when the session ends, and it SHALL never serve another session.

#### Scenario: Engine fails to start
- **WHEN** the engine container cannot start or does not answer within its timeout
- **THEN** the launch exits nonzero before the application runs, and no engine or session resource remains

#### Scenario: Session ends
- **WHEN** the application exits
- **THEN** the engine container and its storage are removed before the wrapper returns the application's status

### Requirement: Engine containment is qualified
Restricted local qualification SHALL include engine containment checks:
- no route outside the session;
- private procfs and UTS for nested containers;
- a read-only image store;
- no secrets;
- workspace-only mounts.

A restricted session SHALL NOT start an engine on an installation whose current qualification lacks them.

#### Scenario: Qualified installation
- **WHEN** qualification runs on an installation with the engine image
- **THEN** the report records the engine containment results, bound to the engine image identity

#### Scenario: Qualification without engine checks
- **WHEN** a restricted session would start an engine and the installation's qualification predates the engine checks or failed them
- **THEN** the launch stops before the application with requalification guidance

### Requirement: Engine documentation
The README SHALL describe:
- when a session has an engine, its endpoint and how images reach it;
- its storage lifecycle, budgets and hardening exceptions;
- the checks that still need a host engine, such as explicit cgroup limits for nested containers.

#### Scenario: Operator reads the documentation
- **WHEN** an operator reads the README section on container tests
- **THEN** it shows how to add an image toolchain and run it from a session, and lists the engine's limits and exceptions
