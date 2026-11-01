#!/usr/bin/env bash
set -Eeuo pipefail

die() { printf 'claude-container: %s\n' "$*" >&2; exit 1; }

usage() {
    cat <<'EOF'
Usage: claude-container.sh [container option] [claude arguments...]

Runs Claude Code in a read-only Podman container. The current directory (or
its parent with --container-git-worktree) and the Claude configuration directory
are mounted read/write.

Container options:
  --container-build      build or refresh the container image before starting
  --container-shell      open a shell instead of starting Claude Code
  --container-git-worktree mount the parent of the current directory read/write
                         for Git worktrees; the container starts in the current directory
  --container-help       show this wrapper help

All other arguments are passed to Claude Code unchanged.

Environment:
  CLAUDE_CONTAINER_IMAGE  image name (default: localhost/claude-code:latest)
  CLAUDE_CONFIG_DIR       Claude configuration directory (default: ~/.claude)
  CLAUDE_CONTAINER_STATE_DIR optional isolated home; unset keeps shared configuration
  CLAUDE_CONTAINER_PODMAN_SOCKET optional absolute delegation socket override
  CLAUDE_YOLO             enable --dangerously-skip-permissions (default: disabled)
  CLAUDE_CONTAINER_PODMAN enable host Podman API access only with exact value 1
                         (default: disabled; all other values disable access)
                         requires a reachable rootless service; failed verification
                         stops startup before image operations
  CLAUDE_CONTAINER_TRUST_HOST_CA  trust a host CA bundle: 1, true, or yes (default: disabled)
  CLAUDE_CONTAINER_CA_BUNDLE      CA bundle file to trust (default: first of
                                  /etc/ssl/certs/ca-certificates.crt and
                                  /etc/pki/tls/certs/ca-bundle.crt)

Launch requires a verified Linux rootless engine, locally or via an explicit
same-host Unix CONTAINER_HOST with an absolute socket pathname beyond /.
Named connections and TCP/SSH are unsupported.
Delegation endpoint: explicit socket override, Unix CONTAINER_HOST, then
${XDG_RUNTIME_DIR:-/run/user/<uid>}/podman/podman.sock.
The socket permits host mounts beyond the workspace. YOLO changes approvals
only. Worktree mode exposes the entire parent read/write.
State directories must belong to the caller and deny group/other access.
Unset CLAUDE_CONFIG_DIR when selecting an isolated home; no state is imported.
Temporary /tmp, /run, and /var/tmp mounts are noexec, limited to 256/16/256 MiB.
EOF
}

build_image=0
shell_mode=0
git_worktree=0
args=()
for arg in "$@"; do
    case "$arg" in
        --container-help) usage; exit 0 ;;
        --container-build) build_image=1 ;;
        --container-shell) shell_mode=1 ;;
        --container-git-worktree) git_worktree=1 ;;
        *) args+=("$arg") ;;
    esac
done

boolean() {
    case "${2,,}" in
        1|true|yes) printf 1 ;;
        ''|0|false|no) printf 0 ;;
        *) die "$1 must be 0, 1, true, false, yes, or no" ;;
    esac
}
yolo=$(boolean CLAUDE_YOLO "${CLAUDE_YOLO:-}")
podman_access=0
[[ "${CLAUDE_CONTAINER_PODMAN:-}" != 1 ]] || podman_access=1
trust_host_ca=$(boolean CLAUDE_CONTAINER_TRUST_HOST_CA "${CLAUDE_CONTAINER_TRUST_HOST_CA:-}")
[[ -z "${CLAUDE_CONTAINER_STATE_DIR:-}" || -z "${CLAUDE_CONFIG_DIR:-}" ]] \
    || die 'CLAUDE_CONTAINER_STATE_DIR conflicts with CLAUDE_CONFIG_DIR; unset CLAUDE_CONFIG_DIR to isolate state'

command -v podman >/dev/null || die 'Podman is required on the host'
# Unix service access also supports running this wrapper inside another container
# on the same host. TCP/SSH transports and Podman Machine are not supported.
[[ -z "${CONTAINER_CONNECTION:-}" ]] || die 'named remote connections are not supported; use local Podman or a local Unix CONTAINER_HOST'
case "${CONTAINER_HOST:-}" in
    '') ;;
    unix://*)
        launch_socket=${CONTAINER_HOST#unix://}
        [[ "$launch_socket" == /* && -n "${launch_socket//\//}" ]] \
            || die 'CONTAINER_HOST requires an absolute Unix socket path beyond /'
        ;;
    *) die 'remote TCP/SSH Podman contexts are not supported; use a local Unix socket' ;;
esac
runtime_info=$(podman info --format '{{.Host.Security.Rootless}} {{.Host.OS}} {{.Host.ServiceIsRemote}}') || die 'cannot query Podman; check the local rootless service'
[[ "$runtime_info" == "true linux false" || "$runtime_info" == "true linux true" ]] || die 'a verified Linux rootless Podman engine is required (unexpected engine response)'
read -r _ _ remote <<< "$runtime_info"
if [[ "$remote" == true && "${CONTAINER_HOST:-}" != unix:///* ]]; then
    die 'remote Podman contexts are not supported; set CONTAINER_HOST to a local Unix socket'
fi

caller_uid=$(id -u)
caller_gid=$(id -g)
socket="${CLAUDE_CONTAINER_PODMAN_SOCKET:-${XDG_RUNTIME_DIR:-/run/user/$caller_uid}/podman/podman.sock}"
if [[ -z "${CLAUDE_CONTAINER_PODMAN_SOCKET:-}" && "${CONTAINER_HOST:-}" == unix:///* ]]; then
    socket=${CONTAINER_HOST#unix://}
fi
if ((podman_access)); then
    [[ "$socket" == /* ]] || die "Podman socket must be an absolute path: $socket"
    [[ -S "$socket" && -r "$socket" && -w "$socket" ]] || die "Podman socket not accessible: $socket; enable 'systemctl --user start podman.socket' or start 'podman system service --time=0'"
    socket=$(readlink -f -- "$socket")
    socket_info=$(podman --remote --url "unix://$socket" info --format '{{.Host.Security.Rootless}} {{.Host.RemoteSocket.Path}}') || die "cannot query Podman socket: $socket; check the rootless service, permissions and SELinux policy"
    [[ "$socket_info" != *$'\n'* ]] || die "invalid Podman socket response: $socket"
    read -r socket_rootless host_socket <<< "$socket_info"
    [[ "$socket_rootless" == true ]] || die "Podman socket must serve a rootless engine: $socket"
    # A wrapper already inside a container sees a remapped Unix socket. Bind
    # sources are resolved by the service, so use its host-side socket path.
    [[ "$host_socket" == /* && "$host_socket" != *$'\n'* ]] || die "Podman socket $socket did not report an absolute host socket path"
fi

script_path=$(readlink -f -- "${BASH_SOURCE[0]}")
script_dir=$(dirname -- "$script_path")
workspace=$(pwd -P)
workspace_mount=$workspace
((git_worktree == 0)) || workspace_mount=$(dirname -- "$workspace")
image="${CLAUDE_CONTAINER_IMAGE:-localhost/claude-code:latest}"
state_dir="${CLAUDE_CONTAINER_STATE_DIR:-}"

private_directory() {
    local path=$1 mode
    [[ -d "$path" && -r "$path" && -w "$path" && -x "$path" ]] \
        || die "state directory is not accessible: $path"
    [[ $(stat -c '%u' -- "$path") == "$caller_uid" ]] \
        || die "state directory must belong to the calling user: $path"
    mode=$(stat -c '%a' -- "$path")
    (( (8#$mode & 077) == 0 )) \
        || die "state directory must be private: $path (chmod 700; use native Linux storage if permissions are not enforced)"
}

create_private_directory() (
    umask 077
    mkdir -p -- "$@"
)

state_mounts=()
if [[ -n "$state_dir" ]]; then
    create_private_directory "$state_dir"
    state_dir=$(cd -- "$state_dir" && pwd -P)
    private_directory "$state_dir"
    # Resolve before creating children so an existing parent symlink cannot
    # redirect configuration creation outside the dedicated application home.
    for relative in .claude .config/openspec; do
        resolved=$(readlink -m -- "$state_dir/$relative")
        [[ "$resolved" == "$state_dir/"* ]] \
            || die "isolated configuration escapes state home: $state_dir/$relative"
        create_private_directory "$state_dir/$relative"
    done
    private_directory "$state_dir/.claude"
    state_mounts+=(--volume "$state_dir:/claude-home:rw")
else
    claude_dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
    create_private_directory "$claude_dir"
    claude_dir=$(cd -- "$claude_dir" && pwd -P)
    private_directory "$claude_dir"
    create_private_directory "$HOME/.config/openspec"
    openspec_dir=$(cd -- "$HOME/.config/openspec" && pwd -P)
    state_mounts+=(
        --volume "$claude_dir:/claude-home/.claude:rw"
        --volume "$openspec_dir:/claude-home/.config/openspec:rw"
    )
fi

ca_bundle=""
if ((trust_host_ca)); then
    if [[ -n "${CLAUDE_CONTAINER_CA_BUNDLE:-}" ]]; then
        [[ -f "$CLAUDE_CONTAINER_CA_BUNDLE" ]] || die "CLAUDE_CONTAINER_CA_BUNDLE is not a file: $CLAUDE_CONTAINER_CA_BUNDLE"
        ca_bundle=$(readlink -f -- "$CLAUDE_CONTAINER_CA_BUNDLE")
    else
        for candidate in /etc/ssl/certs/ca-certificates.crt /etc/pki/tls/certs/ca-bundle.crt; do
            if [[ -f "$candidate" ]]; then
                ca_bundle=$candidate
                break
            fi
        done
        [[ -n "$ca_bundle" ]] || die 'no default CA bundle found; set CLAUDE_CONTAINER_CA_BUNDLE to a bundle file'
    fi
fi

if ((build_image)); then
    podman build --tag "$image" --file "$script_dir/Containerfile" "$script_dir"
elif podman image exists "$image"; then
    :
else
    image_status=$?
    [[ "$image_status" == 1 ]] || die "cannot inspect image: $image"
    podman build --tag "$image" --file "$script_dir/Containerfile" "$script_dir"
fi

container_args=(
    --rm --interactive --read-only --read-only-tmpfs=false
    --userns=keep-id --user "$caller_uid:$caller_gid"
    --workdir "$workspace"
    --tmpfs '/tmp:rw,nosuid,nodev,noexec,size=256m,mode=1777'
    --tmpfs '/run:rw,nosuid,nodev,noexec,size=16m'
    --tmpfs '/var/tmp:rw,nosuid,nodev,noexec,size=256m,mode=1777'
    --env HOME=/claude-home
    --env EDITOR=nano --env VISUAL=nano
    --env CLAUDE_CONFIG_DIR=/claude-home/.claude
    --volume "$workspace_mount:$workspace_mount:rw"
    "${state_mounts[@]}"
)
if [[ -t 0 && -t 1 ]]; then
    container_args+=(--tty)
    [[ -z "${TERM:-}" ]] || container_args+=(--env TERM)
fi
if ((podman_access)); then
    container_args+=(
        --volume "$host_socket:/run/podman/podman.sock:rw"
        --env CONTAINER_HOST=unix:///run/podman/podman.sock
    )
else
    container_args+=(--unsetenv CONTAINER_HOST)
fi
if ((trust_host_ca)); then
    container_args+=(
        --volume "$ca_bundle:/claude-home/ca/bundle.pem:ro"
        --env SSL_CERT_FILE=/claude-home/ca/bundle.pem
        --env REQUESTS_CA_BUNDLE=/claude-home/ca/bundle.pem
        --env CURL_CA_BUNDLE=/claude-home/ca/bundle.pem
        --env NODE_EXTRA_CA_CERTS=/claude-home/ca/bundle.pem
    )
fi

if ((shell_mode)); then
    container_args+=(--entrypoint /bin/bash)
    args=()
elif ((yolo)); then
    args=(--dangerously-skip-permissions "${args[@]}")
fi

prefix=${workspace##*/}
prefix=$(printf '%s' "$prefix" | sed -E 's/[^a-zA-Z0-9_.-]+/-/g; s/^[.-]+//; s/[.-]+$//')
prefix=${prefix:-claude-container}
names=$(podman ps --all --format '{{.Names}}') || die 'cannot list Podman containers'
next_index=0
while IFS= read -r name; do
    [[ "$name" == "$prefix-"* ]] || continue
    suffix=${name#"$prefix-"}
    [[ "$suffix" =~ ^[0-9]+$ && ${#suffix} -lt 10 ]] || continue
    numeric=$((10#$suffix))
    ((numeric < next_index)) || next_index=$((numeric + 1))
done <<< "$names"

# Reserve the name with create, so an actual process exit code 125 is never
# confused with a create-time naming collision. Remove only our own container.
container_id=''
client_pid=''
create_error=''
# shellcheck disable=SC2329 # Invoked by the EXIT trap.
cleanup() {
    [[ -z "$create_error" ]] || rm -f -- "$create_error"
    [[ -z "$container_id" ]] || podman rm --force --ignore "$container_id" >/dev/null 2>&1 || true
}
# shellcheck disable=SC2329 # Invoked by signal traps.
forward_signal() {
    local signal=$1 status=$2
    [[ -z "$container_id" ]] || podman kill --signal "$signal" "$container_id" >/dev/null 2>&1 || true
    [[ -z "$client_pid" ]] || wait "$client_pid" 2>/dev/null || true
    exit "$status"
}
trap cleanup EXIT
trap 'forward_signal TERM 143' TERM
trap 'forward_signal INT 130' INT
trap 'forward_signal HUP 129' HUP
create_error=$(mktemp)
for ((attempt=0; attempt<20; attempt++)); do
    name="$prefix-$next_index"
    if container_id=$(podman create --name "$name" "${container_args[@]}" "$image" "${args[@]}" 2>"$create_error"); then
        break
    else
        create_status=$?
        container_id=''
        if podman container exists "$name"; then
            next_index=$((next_index + 1))
        else
            cat -- "$create_error" >&2
            rm -f -- "$create_error"
            exit "$create_status"
        fi
    fi
done
rm -f -- "$create_error"
[[ -n "$container_id" ]] || die 'could not reserve a container name after 20 attempts'

# Explicit stdin redirection prevents Bash from replacing stdin with /dev/null
# for the background client; traps can forward signals while wait is active.
podman start --attach --interactive "$container_id" <&0 &
client_pid=$!
status=0
wait "$client_pid" || status=$?
exit "$status"
