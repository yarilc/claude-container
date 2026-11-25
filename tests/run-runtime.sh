#!/usr/bin/env bash
# Run tests without host Python, using disposable native Linux state.
set -Eeuo pipefail
project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
image=${CLAUDE_CONTAINER_IMAGE:-localhost/claude-code:latest}
rootless=$(podman info --format '{{.Host.Security.Rootless}}')
[[ "$rootless" == true ]] || { printf 'A rootless engine is required.\n' >&2; exit 1; }
# Inside a session, CONTAINER_HOST names the session container engine over
# loopback TCP. The engine also serves its API on its user's Unix socket, which
# the test containers bind (launcher/engine/entrypoint.sh).
if [[ "${CONTAINER_HOST:-}" == tcp://127.0.0.1:2375 ]]; then
    socket=/run/user/1000/podman/podman.sock
else
    socket=$(podman info --format '{{.Host.RemoteSocket.Path}}')
    socket=${socket#unix://}
fi
[[ "$socket" == /* ]] || { printf 'Start the rootless Unix Podman service first.\n' >&2; exit 1; }
pattern=test_runtime.py
guard_environment=()
if [[ "${1:-}" == --wrapper ]]; then
    # The shared launcher tests and this wrapper's own: test_launcher.py, test_wrapper.py.
    pattern='test_[lw][ar][au]*.py'
    shift
elif [[ "${1:-}" == --setup ]]; then
    pattern=test_setup.py
    shift
elif [[ "${1:-}" == --setup-runtime ]]; then
    pattern=test_setup_runtime.py
    shift
elif [[ "${1:-}" == --qualification ]]; then
    pattern=test_qualification.py
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
elif [[ "${1:-}" == --guard || "${1:-}" == --guard-idle ]]; then
    pattern=test_guard.py
    guard_toolchain=$(podman image inspect --format '{{.Id}}' "${SANDBOX_GUARD_TOOLCHAIN:-localhost/claude-guard-toolchain:development}")
    guard_environment=(--env SANDBOX_GUARD_TESTS=1 --env "SANDBOX_GUARD_TOOLCHAIN=$guard_toolchain")
    if [[ "$1" == --guard-idle ]]; then
        guard_environment+=(--env SANDBOX_IDLE_TESTS=1)
        set -- "$1" -k test_guarded_multiplex_idle_resume "${@:2}"
    fi
    shift
fi
# Wrapper fixtures need private, executable temporary storage: the image's
# /tmp is world-writable, and the toolchain library refuses such ancestors.
volume=''
copy_volume=''
cleanup() {
    [[ -z "$volume" ]] || podman volume rm --force "$volume" >/dev/null
    [[ -z "$copy_volume" ]] || podman volume rm --force "$copy_volume" >/dev/null
}
trap cleanup EXIT
volume=$(podman volume create)
native_state=$(podman volume inspect --format '{{.Mountpoint}}' "$volume")
# A checkout that group or other can write, such as a Windows drive under WSL
# (mode 777), fails the protected-path checks: run the tests on a copy of it in
# a disposable native volume, without the local test state.
checkout=$project_root
if (( 8#$(stat -c %a -- "$project_root") & 8#022 )); then
    copy_volume=$(podman volume create)
    checkout=$(podman volume inspect --format '{{.Mountpoint}}' "$copy_volume")
    tar -C "$project_root" --exclude=./.test-state -cf - . \
        | podman run --rm --interactive --network=none --userns=keep-id --user "$(id -u):$(id -g)" \
            --volume "$checkout:$checkout:rw" --entrypoint tar "$image" -C "$checkout" -xf -
fi
podman run --rm --interactive --userns=keep-id --user "$(id -u):$(id -g)" \
    --volume "$checkout:$checkout:rw" \
    --volume "$native_state:$native_state:rw" \
    --volume "$socket:/run/podman/podman.sock:rw" \
    --mount type=tmpfs,destination=/sandbox-test-tmp,tmpfs-mode=0700,U=true,tmpfs-size=1g \
    --env SANDBOX_TEST_TMPDIR=/sandbox-test-tmp \
    --workdir "$checkout" \
    --env CONTAINER_HOST=unix:///run/podman/podman.sock \
    --env SANDBOX_RUNTIME_TESTS=1 \
    --env "CLAUDE_CONTAINER_IMAGE=$image" \
    --env "SANDBOX_TEST_STATE_ROOT=$native_state" \
    "${guard_environment[@]}" \
    --env "SANDBOX_TOOLCHAIN_EXAMPLES=${SANDBOX_TOOLCHAIN_EXAMPLES:-0}" \
    --entrypoint python3 "$image" \
    -m unittest discover -s tests -p "$pattern" -v "$@"
