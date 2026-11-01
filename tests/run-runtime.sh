#!/usr/bin/env bash
# Run tests without host Python, using disposable native Linux state.
set -Eeuo pipefail
project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
image=${CLAUDE_CONTAINER_IMAGE:-localhost/claude-code:latest}
rootless=$(podman info --format '{{.Host.Security.Rootless}}')
[[ "$rootless" == true ]] || { printf 'A rootless engine is required.\n' >&2; exit 1; }
socket=$(podman info --format '{{.Host.RemoteSocket.Path}}')
[[ "$socket" == /* ]] || { printf 'Start the rootless Unix Podman service first.\n' >&2; exit 1; }
pattern=test_runtime.py
if [[ "${1:-}" == --wrapper ]]; then
    pattern=test_wrapper.py
    shift
fi
volume=''
cleanup() {
    [[ -z "$volume" ]] || podman volume rm --force "$volume" >/dev/null
}
trap cleanup EXIT
volume=$(podman volume create)
native_state=$(podman volume inspect --format '{{.Mountpoint}}' "$volume")
podman run --rm --interactive --userns=keep-id --user "$(id -u):$(id -g)" \
    --volume "$project_root:$project_root:rw" \
    --volume "$native_state:$native_state:rw" \
    --volume "$socket:/run/podman/podman.sock:rw" \
    --workdir "$project_root" \
    --env CONTAINER_HOST=unix:///run/podman/podman.sock \
    --env CLAUDE_RUNTIME_TESTS=1 \
    --env "CLAUDE_CONTAINER_IMAGE=$image" \
    --env "CLAUDE_TEST_STATE_ROOT=$native_state" \
    --entrypoint python3 "$image" \
    -m unittest discover -s tests -p "$pattern" -v "$@"
