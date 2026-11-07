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
guard_environment=()
if [[ "${1:-}" == --wrapper ]]; then
    pattern=test_wrapper.py
    shift
elif [[ "${1:-}" == --setup ]]; then
    pattern=test_setup.py
    shift
elif [[ "${1:-}" == --setup-runtime ]]; then
    pattern=test_setup_runtime.py
    shift
elif [[ "${1:-}" == --network-feasibility ]]; then
    pattern=test_network_feasibility.py
    shift
elif [[ "${1:-}" == --network ]]; then
    pattern=test_network_runtime.py
    shift
elif [[ "${1:-}" == --network-policy ]]; then
    pattern=test_network_policy.py
    shift
elif [[ "${1:-}" == --mux ]]; then
    pattern=test_mux.py
    shift
elif [[ "${1:-}" == --guard ]]; then
    pattern=test_guard.py
    guard_toolchain=$(podman image inspect --format '{{.Id}}' "${CLAUDE_GUARD_TOOLCHAIN:-localhost/claude-guard-toolchain:development}")
    guard_environment=(--env CLAUDE_GUARD_TESTS=1 --env "CLAUDE_GUARD_TOOLCHAIN=$guard_toolchain")
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
    "${guard_environment[@]}" \
    --entrypoint python3 "$image" \
    -m unittest discover -s tests -p "$pattern" -v "$@"
