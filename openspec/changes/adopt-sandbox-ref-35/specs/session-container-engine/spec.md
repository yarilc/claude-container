## MODIFIED Requirements

### Requirement: Engine shares the session network boundary
The engine and every container it runs SHALL have no network path other than the session's:
- an offline session's engine SHALL reach no external service;
- a provider session's engine SHALL reach only what the session's proxy policy allows, through that proxy;
- an unrestricted session's engine SHALL have the session's network.

#### Scenario: Offline nested container
- **WHEN** a container started by an offline session's engine tries direct DNS, TCP or UDP to an external address, or the engine tries to pull an image
- **THEN** every attempt fails, and no network path appears that the session lacks

#### Scenario: Interfaces of a restricted session with an engine
- **WHEN** a restricted session with an engine lists the interfaces of its network namespace (`/proc/net/dev`)
- **THEN** only loopback is present, although the host's `/sys`, which Podman bind-mounts read-only into a container that joins another network namespace, lists the host's interfaces

#### Scenario: Unrestricted pull
- **WHEN** an unrestricted session's engine pulls an image that is not in the library
- **THEN** the pull uses the session's network and the image stays in the session's storage

### Requirement: Engine documentation
The README SHALL describe:
- when a session has an engine, its endpoint and how images reach it;
- its storage lifecycle, budgets and hardening exceptions;
- that a session with an engine sees the host's `/sys` read-only;
- the checks that still need a host engine, such as explicit cgroup limits for nested containers.

#### Scenario: Operator reads the documentation
- **WHEN** an operator reads the README section on container tests
- **THEN** it shows how to add an image toolchain and run it from a session, and lists the engine's limits and exceptions
