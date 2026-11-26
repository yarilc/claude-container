# Spec Delta

## ADDED Requirements

### Requirement: Measured eligibility for cgroup delegation
Each engine start SHALL measure whether the engine is eligible for cgroup delegation: its cgroup namespace is private, and its root is a cgroup v2 directory mounted read-write with `nsdelegate` and owned by the root of the engine's user namespace. Eligibility SHALL NOT be inferred from the engine host's cgroup manager, and it SHALL NOT require a host change.

#### Scenario: Native Linux with the systemd cgroup manager
- **WHEN** an engine starts on a native Linux host whose rootless Podman uses the `systemd` cgroup manager with cgroup v2
- **THEN** the engine is eligible

#### Scenario: Windows Podman machine
- **WHEN** an engine starts in a Windows Podman machine whose rootless Podman uses the `cgroupfs` cgroup manager with cgroup v2 and delegates no controller
- **THEN** the engine is eligible

#### Scenario: Engine without a suitable cgroup v2 root
- **WHEN** an engine starts on a host with cgroup v1, or its cgroup root is not owned by the root of its user namespace, or is mounted without `nsdelegate`
- **THEN** the engine is ineligible, and nothing is delegated

### Requirement: Delegated engine cgroup subtree
On every eligible engine, the engine user SHALL own the engine's cgroup subtree as the kernel's delegation model defines it. Every engine process SHALL run in a leaf below the subtree's root, and every controller available to the engine SHALL be enabled for nested containers. The files of the subtree's root that hold limits SHALL stay unwritable from the engine and from nested containers.

#### Scenario: Nested container cgroup
- **WHEN** a nested container starts on an eligible engine
- **THEN** it runs in its own cgroup below the engine's cgroup

#### Scenario: Engine limits from inside the engine
- **WHEN** a process of the engine user, or the root of a nested container that mounts the engine's cgroup namespace read-write, writes any limit file of the engine's cgroup root
- **THEN** the write fails, and the session budgets are unchanged

#### Scenario: Delegation fails
- **WHEN** an eligible engine cannot complete the delegation
- **THEN** the engine does not start, and the launch stops before the application, naming the engine

### Requirement: Engine startup step
Only the engine's startup step SHALL run as the root of the engine's user namespace and hold the ownership-change capability, which it SHALL use only to delegate the engine's cgroup subtree. It SHALL then run the engine as the engine user. Afterwards the capability SHALL stay only in the bounding set, which no-new-privileges keeps unreachable. The launcher's own commands in the engine SHALL run as the engine user.

#### Scenario: Running engine processes
- **WHEN** the processes of a running engine are listed
- **THEN** none runs as the root of the engine's user namespace, the engine's init included, and none holds the ownership-change capability in its permitted, effective or ambient set in the engine's user namespace

#### Scenario: Launcher commands in the engine
- **WHEN** the launcher runs its readiness, process limit or eligibility checks in the engine
- **THEN** they run as the engine user

### Requirement: Systemd in nested containers
On an eligible engine, a nested container started in systemd mode with a systemd image SHALL boot systemd as its PID 1 to the `running` or `degraded` state. Systemd SHALL start units and keep their journal.

#### Scenario: Rocky Linux 9 target
- **WHEN** a session runs a Rocky Linux 9 image that starts `/sbin/init` with `podman run --systemd=always` on an eligible engine
- **THEN** once boot completes, `systemctl is-system-running` reports `running` or `degraded`

#### Scenario: Amazon Linux 2023 target
- **WHEN** a session runs an Amazon Linux 2023 image that starts `/sbin/init` with `podman run --systemd=always` on an eligible engine
- **THEN** once boot completes, `systemctl is-system-running` reports `running` or `degraded`

#### Scenario: Unit and journal
- **WHEN** a test starts a unit in a running nested systemd container
- **THEN** the unit becomes active, and `journalctl` shows its output

### Requirement: Explicit limits for nested containers
On an eligible engine, explicit limits requested for a nested container SHALL apply for every controller the engine has. A request that needs a controller the engine lacks, or any request on an ineligible engine, SHALL fail without starting the container.

#### Scenario: Engine with memory and pids controllers
- **WHEN** a nested container on an eligible engine with the `memory` and `pids` controllers is started with `--memory=64m --pids-limit=32`
- **THEN** its cgroup has `memory.max` 67108864 and `pids.max` 32

#### Scenario: Engine without the controller
- **WHEN** a nested container is started with `--memory=64m` on an engine without the `memory` controller, such as an engine in the Windows Podman machine
- **THEN** the container does not start, and the run reports an error

### Requirement: Ineligible engines are announced
When an engine is ineligible, the launch SHALL announce that systemd containers and explicit nested limits are unavailable in the session, with the reason. The session SHALL otherwise start as on an eligible engine.

#### Scenario: Ineligible engine
- **WHEN** a session starts with an ineligible engine
- **THEN** the launch prints the notice with the reason before the application starts, and the application runs

#### Scenario: Eligible engine
- **WHEN** a session starts with an eligible engine
- **THEN** no such notice is printed

### Requirement: Engine image declares its capabilities
The engine image SHALL declare in its `io.containers.capabilities` label exactly the capabilities that the engine container is started with: `SETUID`, `SETGID`, `SYS_CHROOT` and `CHOWN`. Starting an engine SHALL therefore report no capability error. The label SHALL NOT add a capability to the engine: its capabilities stay the fixed hardening exceptions.

#### Scenario: Engine started by a session
- **WHEN** a session starts its engine through a Podman engine that reads the image's capability label
- **THEN** Podman reports no `Capabilities requested by user or image are not allowed by default` error, and the engine's bounding set is `SETUID`, `SETGID`, `SYS_CHROOT` and `CHOWN`

#### Scenario: Label and options drift apart
- **WHEN** the engine recipe's capability label differs from the capabilities of the engine container options
- **THEN** the shared engine recipe check fails, naming the difference

## MODIFIED Requirements

### Requirement: Engine budgets
The engine container SHALL receive the session's memory, CPU and process budgets. Their enforcement, fallback, verification and announcement SHALL follow the agent container's rules. Where the engine's cgroup is enforced, the budgets SHALL bound the engine and all its nested containers together.

#### Scenario: Delegated controllers
- **WHEN** the rootless engine delegates `memory`, `cpu` and `pids` with the systemd cgroup manager
- **THEN** the engine container's effective limits equal the session budgets, and the launch verifies them

#### Scenario: Cgroupfs engine
- **WHEN** the rootless engine uses the cgroupfs cgroup manager
- **THEN** the launch announces the engine's unenforced budgets with the same reasons as the agent's, and applies the process rlimit fallback where the rules allow it

### Requirement: Fixed engine hardening exceptions
The engine container SHALL run as an unprivileged user after its startup step. Over the standard policy it SHALL relax only what nested containers and image operations need:
- the user-namespace helper capabilities;
- the chroot capability, for layer extraction and builds;
- the FUSE and TUN devices;
- an unmasked procfs;
- disabled SELinux labelling;
- `sethostname` and `setdomainname` over the host's default seccomp profile;
- the startup step that delegates its cgroup subtree.

The wrapper SHALL NOT widen these for a nested tool.

#### Scenario: Engine container inspected
- **WHEN** an engine container is inspected
- **THEN** its configured user, capabilities, devices, masks, labels and seccomp profile match exactly the documented exceptions, and its running processes run as the engine user with the ownership-change capability only in their bounding set

#### Scenario: Image operations in a session
- **WHEN** a session builds an image with a `RUN` step, or loads an image whose layers its engine does not have
- **THEN** the operation succeeds within these exceptions

#### Scenario: Tool needs more
- **WHEN** a nested tool fails because it needs a privilege outside these exceptions
- **THEN** the wrapper adds nothing, and the limitation is recorded in the validation record

### Requirement: Engine containment is qualified
Restricted local qualification SHALL include engine containment checks:
- no route outside the session;
- private procfs and UTS for nested containers;
- a read-only image store;
- no secrets;
- workspace-only mounts;
- unwritable limit files of the engine's cgroup root;
- on an eligible engine, nested cgroups below the engine's.

A restricted session SHALL NOT start an engine on an installation whose current qualification lacks them.

#### Scenario: Qualified installation
- **WHEN** qualification runs on an installation with the engine image
- **THEN** the report records the engine containment results and the engine's eligibility, bound to the engine image identity

#### Scenario: Qualification without engine checks
- **WHEN** a restricted session would start an engine and the installation's qualification predates the engine checks or failed them
- **THEN** the launch stops before the application with requalification guidance

#### Scenario: Ineligible engine host
- **WHEN** qualification runs where the engine is ineligible
- **THEN** the report records the engine as ineligible, the delegation check is not required, and the other engine checks still apply

### Requirement: Engine documentation
The README SHALL describe:
- when a session has an engine, its endpoint and how images reach it;
- its storage lifecycle, budgets and hardening exceptions;
- that a session with an engine sees the host's `/sys` read-only;
- systemd containers and explicit nested limits: the engines where they work, the delegation exception, and what a test cannot exercise on an engine without controllers.

#### Scenario: Operator reads the documentation
- **WHEN** an operator reads the README section on container tests
- **THEN** it shows how to add an image toolchain and run it from a session, and lists the engine's limits and exceptions

#### Scenario: Systemd containers documented
- **WHEN** an operator reads the README section on container tests
- **THEN** it shows how to run a systemd image from a session, names the platforms where it works, and states that resource-control unit settings have no effect on an engine without controllers
