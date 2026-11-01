# Verification

Validated on 2026-11-01.

- `bash -n claude-container.sh`: passed.
- `git diff --check`: passed.
- Temporary Python harness with an executable Podman stub and an isolated Unix socket: 108 checks passed. Only the socket assignment in a temporary script copy was redirected to the fixture. Temporary stubs, socket, and configuration directories were removed.
- The matrix covered Claude and shell modes with all build/worktree combinations; successful `true`, `false`, empty, unexpected and multiline responses, and query failure; explicit URL selection despite an unrelated default endpoint; disabled values (unset, empty, `0`, `true`, `yes`, `01`, and arbitrary text); missing/non-socket paths; image-missing automatic build; argument boundaries, mounts, working directory, and help without invoking Podman.
- Rejected service results issued no image operations, build, container listing, or launch. Disabled access performed no service query and supplied no socket mount or container `CONTAINER_HOST`.

## Real runtime coverage

No usable host rootless API service was available: `/run/user/<caller-uid>/podman/podman.sock` was absent, and no remote endpoint was configured. Local `podman info --format '{{.Host.Security.Rootless}}'` failed because `newuidmap` is unavailable. Consequently real image build, Claude startup, configuration persistence, shell startup, and child-container execution were not exercised. The conditional real-runtime task was assessed and this unavailable coverage is recorded; no rootful service or credentials were provisioned.
