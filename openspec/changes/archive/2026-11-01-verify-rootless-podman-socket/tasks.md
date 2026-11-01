# Tasks

## 1. Enforce and document rootless service verification

- [x] 1.1 Add the explicit remote socket `info --format '{{.Host.Security.Rootless}}'` probe after the enabled branch's existing socket check, with checked command failure and exact `true` acceptance. Verify with controlled Podman stubs that success preserves the mount/environment and that `false`, non-zero query status, empty output, and unexpected output fail with actionable socket-specific errors before image operations or launch.
- [x] 1.2 Update wrapper help, README socket verification/setup guidance, and AGENTS testing instructions to describe the enforced reachable-rootless requirement and recovery. Verify help works without Podman, README shows the exact remote formatted query and expected `true`, and documentation retains exact-value opt-in and the fixed socket path.
- [x] 1.3 Exercise unset, empty, `0`, `true`, `yes`, `01`, and arbitrary non-`1` values with a stub and absent socket; verify no service probe, socket mount, or container `CONTAINER_HOST`. Recheck enabled missing/non-socket errors and verify an unrelated default Podman endpoint cannot replace the explicit URL used for verification. Use isolated fixtures and remove temporary artifacts.

## 2. Validate launch-mode integration

- [x] 2.1 Run a stubbed matrix covering Claude and shell modes, with build and worktree options: verify rootless success preserves image operations, argument forwarding, working directory, and mount behavior, while each service-verification failure prevents even an explicit build. Run `bash -n claude-container.sh` and `git diff --check` and require both to pass.
- [x] 2.2 When a real host rootless service is available, verify its remote formatted query returns `true`, build/start Claude, check configuration persistence, and run a child `podman run` in an enabled session; also check shell and disabled startup. Record results and any unavailable runtime coverage without provisioning a rootful service or using credentials in fixtures.
