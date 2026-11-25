#!/bin/sh
# Serves the session engine's API (design D2): on loopback TCP in the session's
# network namespace for the session, and on the rootless default Unix socket
# for nested containers that mount it, such as tests/run-runtime.sh. The engine
# runs under --init, which reaps the services' children.
#
# A process limit after the port is the session's process budget on the process
# rlimit fallback. It is set here, before the services start, and not by the
# outer engine: a limit applied at creation is shared by every container of
# the user.
set -eu
usage() {
    echo 'usage: sandbox-engine [port [process limit]]' >&2
    exit 2
}
[ "$#" -le 2 ] || usage
port=${1:-2375}
case $port in
    ''|*[!0-9]*) usage ;;
esac
if [ "$#" -eq 2 ]; then
    case $2 in
        ''|0|0*|*[!0-9]*) usage ;;
    esac
    # shellcheck disable=SC3045 # -u in Bash (the engine image's sh) and BusyBox, -p in dash
    ulimit -u "$2" 2>/dev/null || ulimit -p "$2"
fi
socket=$XDG_RUNTIME_DIR/podman/podman.sock
mkdir -p -- "${socket%/*}"
podman system service --time=0 "unix://$socket" &
exec podman system service --time=0 "tcp://127.0.0.1:$port"
