#!/usr/bin/env bash
set -Eeuo pipefail

die() { printf 'claude-container: %s\n' "$*" >&2; exit 1; }

# Keep final LF bytes while retaining the query's own exit status and stderr.
capture_response() {
    local destination=$1 captured query_status
    shift
    if captured=$("$@"; query_status=$?; printf '\034'; exit "$query_status"); then
        printf -v "$destination" '%s' "${captured%$'\034'}"
    else
        return "$?"
    fi
}

usage() {
    cat <<'EOF'
Usage: claude-container.sh [container option] [claude arguments...]

Runs Claude Code in a read-only Podman container. The current directory (or
its parent with --container-git-worktree) and the Claude configuration directory
are mounted read/write.

Container options:
  --container-setup      interactively prepare a complete user installation
  --container-build      build or refresh the container image before starting
  --container-shell      open a shell instead of starting Claude Code
  --container-git-worktree mount the parent of the current directory read/write
                         for Git worktrees; the container starts in the current directory
  --container-help       show this wrapper help

All other arguments are passed to Claude Code unchanged.

Environment:
  CLAUDE_CONTAINER_NETWORK offline (default), provider, or explicit unrestricted
  CLAUDE_CONTAINER_NETWORK_PROFILE protected provider policy profile name
  CLAUDE_CONTAINER_NETWORK_POLICY absolute operator policy JSON path
  CLAUDE_CONTAINER_NETWORK_RUNTIME_DIR private native directory at its host path
  CLAUDE_CONTAINER_EGRESS_IMAGE immutable proxy image ID or registry digest
  CLAUDE_CONTAINER_MAINTENANCE authorize image preparation only with exact value 1
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
Host GNU timeout is required. Shutdown is bounded to 20 seconds, with at most
5 seconds for graceful exit before forced owned-container removal. Cleanup
failures are reported without changing the application or first signal status.
Engine verification replies must contain one record, with no terminator or a
single final LF; extra blank or nonblank records stop startup before builds.
Delegated socket verification also rejects any CR character, including CRLF.
Restricted modes reject Podman delegation, including shell and YOLO. Provider
mode uses an external CONNECT proxy; removing proxy variables cannot grant a
direct route. The trusted proxy requires initial TLS 1.2/1.3 SNI matching CONNECT
before forwarding client bytes. Missing/malformed SNI, ECH/GREASE and inspection
limits/timeouts fail closed. This does not prove exclusive Anthropic application
access: encrypted Host, shared-service routing and remote forwarding remain opaque.
Network restriction requires a protected installation outside
writable workspace/state trees and host Python 3. Initial support is the tested
same-host Unix service with rootless Netavark/server 4.9.3. Unsupported setups
fail closed. Image pulls/build RUN steps remain outside runtime filtering and
require separate maintenance authorization. Allowed services can receive data;
provider-hosted remote tools and encrypted application content are not filtered.
Restricted startup requires WSL 6.6.87.2 x86_64, usable Landlock ABI 3 and a
protected static guard and SHA-256 manifest in network/bin. The guard adds
unprivileged Landlock and restrictive seccomp, preserving the OCI profile.
New Unix services are unavailable; fixed-peer pairs may have private inert names.
See network/README.md for packaging and docs/validation.md for measured evidence.
EOF
}

# Setup must diagnose prerequisites before normal runtime configuration exists.
# Help takes precedence regardless of option order and never loads setup code.
for arg in "$@"; do
    [[ "$arg" != --container-help ]] || { usage; exit 0; }
done
for arg in "$@"; do
    if [[ "$arg" == --container-setup ]]; then
        [[ $# == 1 ]] || die '--container-setup must be used alone'
        [[ -t 0 && -t 1 ]] || die '--container-setup requires an interactive terminal'
        command -v python3 >/dev/null || die 'host Python 3 is required for interactive setup'
        setup_script=$(readlink -f -- "${BASH_SOURCE[0]}")
        exec python3 -I "$(dirname -- "$setup_script")/setup/setup.py"
    fi
done

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
network_mode=${CLAUDE_CONTAINER_NETWORK:-offline}
case "$network_mode" in
    offline|provider|unrestricted) ;;
    *) die 'CLAUDE_CONTAINER_NETWORK must be offline, provider, or unrestricted' ;;
esac
if [[ "$network_mode" != unrestricted ]] && ((podman_access)); then
    die 'restricted networking rejects CLAUDE_CONTAINER_PODMAN=1: the host API bypasses egress enforcement; select explicit unrestricted mode for delegation'
fi
if [[ "$network_mode" == provider ]]; then
    [[ -n "${CLAUDE_CONTAINER_NETWORK_PROFILE:-}" && -n "${CLAUDE_CONTAINER_NETWORK_POLICY:-}" ]] \
        || die 'provider mode requires CLAUDE_CONTAINER_NETWORK_PROFILE and CLAUDE_CONTAINER_NETWORK_POLICY'
    [[ -n "${CLAUDE_CONTAINER_NETWORK_RUNTIME_DIR:-}" && -n "${CLAUDE_CONTAINER_EGRESS_IMAGE:-}" ]] \
        || die 'provider mode requires a private host-path CLAUDE_CONTAINER_NETWORK_RUNTIME_DIR and immutable CLAUDE_CONTAINER_EGRESS_IMAGE'
fi
[[ -z "${CLAUDE_CONTAINER_STATE_DIR:-}" || -z "${CLAUDE_CONFIG_DIR:-}" ]] \
    || die 'CLAUDE_CONTAINER_STATE_DIR conflicts with CLAUDE_CONFIG_DIR; unset CLAUDE_CONFIG_DIR to isolate state'

command -v podman >/dev/null || die 'Podman is required on the host'
command -v timeout >/dev/null && [[ $(timeout --version 2>/dev/null) == *'GNU coreutils'* ]] \
    || die 'GNU timeout is required on the host; install GNU coreutils'
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
capture_response runtime_info podman info --format '{{.Host.Security.Rootless}} {{.Host.OS}} {{.Host.ServiceIsRemote}}' \
    || die 'cannot query Podman; check the local rootless service'
runtime_info=${runtime_info%$'\n'}
[[ "$runtime_info" != *$'\n'* ]] || die 'invalid Podman engine response: expected one record with at most one final LF'
[[ "$runtime_info" == "true linux false" || "$runtime_info" == "true linux true" ]] || die 'a verified Linux rootless Podman engine is required (unexpected engine response)'
read -r _ _ remote <<< "$runtime_info"
if [[ "$remote" == true && "${CONTAINER_HOST:-}" != unix:///* ]]; then
    die 'remote Podman contexts are not supported; set CONTAINER_HOST to a local Unix socket'
fi
if [[ "$network_mode" != unrestricted ]]; then
    command -v python3 >/dev/null || die 'host Python 3 is required for restricted network policy validation'
    [[ "$remote" == true ]] || die 'restricted networking currently requires the tested same-host Unix service; local-engine enforcement is unverified'
    capture_response network_backend podman info --format '{{.Host.NetworkBackend}}' \
        || die 'cannot verify restricted network backend'
    capture_response network_version podman version --format '{{.Server.Version}}' \
        || die 'cannot verify restricted network server version'
    [[ "${network_backend%$'\n'}" == netavark && "${network_version%$'\n'}" == 4.9.3 ]] \
        || die 'unsupported restricted network backend/version: tested support requires rootless Netavark server 4.9.3'
    capture_response network_platform podman info --format '{{json .Host}}' \
        || die 'cannot verify restricted platform security policy'
    printf '%s' "$network_platform" | python3 -I -c '
import json,sys
try:
    host=json.load(sys.stdin); security=host["security"]
    valid=(host["kernel"]=="6.6.87.2-microsoft-standard-WSL2" and host["arch"]=="amd64"
           and security["seccompEnabled"] is True and security["selinuxEnabled"] is False
           and security["apparmorEnabled"] is False)
except (ValueError,KeyError,TypeError): valid=False
sys.exit(0 if valid else 1)
' || die 'unsupported restricted platform: verified WSL 6.6.87.2 x86_64, standard OCI seccomp, SELinux/AppArmor disabled required; no policy is disabled automatically'
    # Mandatory native confinement is installed again inside the agent before
    # any interpreter/application runs. ABI 3 is supported on the tested WSL host.
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
    capture_response socket_info podman --remote --url "unix://$socket" info --format '{{.Host.Security.Rootless}} {{.Host.RemoteSocket.Path}}' \
        || die "cannot query Podman socket: $socket; check the rootless service, permissions and SELinux policy"
    [[ "$socket_info" != *$'\r'* ]] || die "invalid Podman socket response: $socket"
    socket_info=${socket_info%$'\n'}
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
    if ((trust_host_ca)); then
        # Prevent the engine from creating a nested CA mount parent owned by a
        # subordinate mapped UID inside the writable isolated home.
        create_private_directory "$state_dir/ca"
        private_directory "$state_dir/ca"
    fi
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

network_preflight=()
if [[ "$network_mode" != unrestricted ]]; then
    network_preflight=(--installation "$script_dir" --writable "$workspace_mount"
        --mount-target "$workspace_mount" --mount-target /claude-home)
    if [[ -n "$state_dir" ]]; then
        network_preflight+=(--writable "$state_dir")
    else
        network_preflight+=(--writable "$claude_dir" --writable "$openspec_dir")
    fi
    if [[ "$network_mode" == provider ]]; then
        network_preflight+=(--policy "$CLAUDE_CONTAINER_NETWORK_POLICY"
            --profile "$CLAUDE_CONTAINER_NETWORK_PROFILE" --proxy-image "$CLAUDE_CONTAINER_EGRESS_IMAGE"
            --runtime "$CLAUDE_CONTAINER_NETWORK_RUNTIME_DIR")
    fi
    python3 -I "$script_dir/network/control.py" preflight "${network_preflight[@]}"
    guard_identity=$(<"$script_dir/network/bin/claude-egress-guard.sha256")
    guard_digest=${guard_identity%% *}
    "$script_dir/network/bin/claude-egress-guard" --probe >&2
fi

if ((build_image)); then
    [[ "${CLAUDE_CONTAINER_MAINTENANCE:-}" == 1 ]] || die 'image refresh requires exact CLAUDE_CONTAINER_MAINTENANCE=1; host pulls/build RUN steps are outside runtime filtering'
    podman build --tag "$image" --file "$script_dir/Containerfile" "$script_dir"
elif podman image exists "$image"; then
    :
else
    image_status=$?
    [[ "$image_status" == 1 ]] || die "cannot inspect image: $image"
    [[ "${CLAUDE_CONTAINER_MAINTENANCE:-}" == 1 ]] || die 'image is absent; prepare it with exact CLAUDE_CONTAINER_MAINTENANCE=1 (build traffic is outside runtime filtering)'
    podman build --tag "$image" --file "$script_dir/Containerfile" "$script_dir"
fi
if [[ "$network_mode" == provider ]]; then
    if podman image exists "$CLAUDE_CONTAINER_EGRESS_IMAGE"; then
        :
    else
        image_status=$?
        [[ "$image_status" == 1 ]] || die 'cannot inspect immutable egress proxy image'
        [[ "${CLAUDE_CONTAINER_MAINTENANCE:-}" == 1 && "$CLAUDE_CONTAINER_EGRESS_IMAGE" == *@sha256:* ]] \
            || die 'proxy image is absent; prepare the pinned artifact under explicit operator maintenance authorization'
        podman pull "$CLAUDE_CONTAINER_EGRESS_IMAGE"
    fi
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
if [[ "$network_mode" != unrestricted ]]; then
    container_args+=(--network=none --pid=private --ipc=private
        --volume "$script_dir/network/bin/claude-egress-guard:/opt/claude-egress/guard:ro"
        --volume "$script_dir/network/resolv.conf:/etc/resolv.conf:ro")
    for variable in HTTP_PROXY HTTPS_PROXY NO_PROXY ALL_PROXY http_proxy https_proxy no_proxy all_proxy; do
        container_args+=(--unsetenv "$variable")
    done
fi
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
diagnostics_pid=''
diagnostics_fd=''
create_pid=''
session_dir=''
session_token=''
cid_file=''
create_output=''
creation_pending=0
shutdown_deadline=0
ownership_label=io.claude-container.session
proxy_label=io.claude-container.egress
proxy_id=''
proxy_pending=0
proxy_cid=''
proxy_output=''

cleanup_warning() {
    printf 'claude-container: cleanup %s (container=%s proxy=%s session=%s); inspect the Podman engine for remaining session containers\n' \
        "$*" "${container_id:-unknown}" "${proxy_id:-unknown}" "${session_token:-unknown}" >&2
}

# All shutdown engine calls share a deadline and reserve time for local clients.
control() {
    local remaining=$((shutdown_deadline - SECONDS - 2)) duration status
    if ((remaining < 2)); then
        cleanup_warning "deadline exhausted before $1"
        return 124
    fi
    duration=$((remaining - 1))
    ((duration <= 2)) || duration=2
    if timeout --kill-after=1s "${duration}s" podman "$@"; then
        return 0
    else
        status=$?
        cleanup_warning "$1 failed or timed out (status $status)"
        return "$status"
    fi
}

# Consult Bash's child table, so a recycled PID cannot select another process.
child_running() {
    local child=$1 running
    [[ -n "$child" ]] || return 1
    while IFS= read -r running; do
        [[ "$running" != "$child" ]] || return 0
    done < <(jobs -pr)
    return 1
}

reap_client() {
    local child=$1 until
    [[ -n "$child" ]] || return 0
    if child_running "$child"; then
        kill -TERM "$child" 2>/dev/null || true
        until=$((SECONDS + 1))
        while child_running "$child" && ((SECONDS < until && SECONDS < shutdown_deadline - 1)); do
            sleep 0.05
        done
        if child_running "$child"; then
            kill -KILL "$child" 2>/dev/null || true
        fi
    fi
    while child_running "$child" && ((SECONDS < shutdown_deadline)); do
        sleep 0.05
    done
    if child_running "$child"; then
        cleanup_warning "local client $child did not terminate within the deadline"
    else
        wait "$child" 2>/dev/null || true
    fi
}

recover_container() {
    local candidate='' owner ids
    [[ -z "$container_id" && "$creation_pending" == 1 ]] || return 0
    if [[ -s "$cid_file" ]]; then
        candidate=$(<"$cid_file")
    elif [[ -s "$create_output" ]]; then
        candidate=$(<"$create_output")
    fi
    if [[ ! "$candidate" =~ ^[a-f0-9]{64}$ ]]; then
        if ! ids=$(control ps --all --no-trunc --filter "label=$ownership_label=$session_token" --format '{{.ID}}'); then
            return 1
        fi
        candidate=$ids
    fi
    [[ -n "$candidate" ]] || return 0
    [[ "$candidate" =~ ^[a-f0-9]{64}$ ]] || { cleanup_warning 'invalid recovered container identity'; return 1; }
    if owner=$(control inspect --type container --format "{{index .Config.Labels \"$ownership_label\"}}" "$candidate") \
        && [[ "$owner" == "$session_token" ]]; then
        container_id=$candidate
    else
        cleanup_warning 'could not confirm recovered container ownership'
        return 1
    fi
}

recover_proxy() {
    local candidate='' owner
    [[ -z "$proxy_id" && "$proxy_pending" == 1 ]] || return 0
    if [[ -s "$proxy_cid" ]]; then
        candidate=$(<"$proxy_cid")
    elif [[ -s "$proxy_output" ]]; then
        candidate=$(<"$proxy_output")
    fi
    if [[ ! "$candidate" =~ ^[a-f0-9]{64}$ ]]; then
        candidate=$(control ps --all --no-trunc --filter "label=$proxy_label=$session_token" --format '{{.ID}}') || return 1
    fi
    [[ -n "$candidate" ]] || return 0
    [[ "$candidate" =~ ^[a-f0-9]{64}$ ]] || { cleanup_warning 'invalid recovered proxy identity'; return 1; }
    if owner=$(control inspect --type container --format "{{index .Config.Labels \"$proxy_label\"}}" "$candidate") \
        && [[ "$owner" == "$session_token" ]]; then
        proxy_id=$candidate
    else
        cleanup_warning 'could not confirm recovered proxy ownership'
        return 1
    fi
}

# Keep collision reconciliation interruptible just like the create request.
creation_lookup() {
    local lookup_status=0
    podman "$@" >"$session_dir/lookup" &
    create_pid=$!
    wait "$create_pid" || lookup_status=$?
    create_pid=''
    return "$lookup_status"
}

# shellcheck disable=SC2329 # Invoked by EXIT and signal traps.
shutdown() {
    local primary_status=$1 signal=${2:-} graceful_until diagnostics_until
    trap - EXIT
    trap '' TERM INT HUP
    set +e
    shutdown_deadline=$((SECONDS + 20))
    if [[ -n "$diagnostics_fd" ]]; then
        exec {diagnostics_fd}>&-
        diagnostics_fd=''
    fi
    if [[ -n "$session_dir" ]]; then
        recover_container
        recover_proxy
        if [[ -n "$signal" && -n "$container_id" && -n "$client_pid" ]]; then
            control kill --signal "$signal" "$container_id" >/dev/null
            graceful_until=$((SECONDS + 5))
            while child_running "$client_pid" && ((SECONDS < graceful_until && SECONDS < shutdown_deadline - 6)); do
                sleep 0.05
            done
        fi
        [[ -z "$container_id" ]] || control rm --force --time 0 --ignore "$container_id" >/dev/null
        reap_client "$create_pid"
        reap_client "$client_pid"
        # Drain the final client log before reaping its owned stderr adapter.
        diagnostics_until=$((SECONDS + 1))
        while child_running "$diagnostics_pid" && ((SECONDS < diagnostics_until && SECONDS < shutdown_deadline - 1)); do
            sleep 0.01
        done
        reap_client "$diagnostics_pid"
        # Cancellation can race with the server publishing its create result.
        if ((creation_pending)) && [[ -z "$container_id" ]]; then
            recover_container
            if [[ -n "$container_id" ]]; then
                control rm --force --time 0 --ignore "$container_id" >/dev/null
            elif [[ -n "$signal" ]]; then
                cleanup_warning 'interrupted creation could not be reconciled'
            fi
        fi
        [[ -z "$proxy_id" ]] || control rm --force --time 0 --ignore "$proxy_id" >/dev/null
        if ((proxy_pending)) && [[ -z "$proxy_id" ]]; then
            recover_proxy
            [[ -z "$proxy_id" ]] || control rm --force --time 0 --ignore "$proxy_id" >/dev/null
        fi
        if [[ -f "$session_dir/logs/denials.jsonl" ]]; then
            printf 'claude-container: recent protected egress diagnostics (sanitized)\n' >&2
            tail -n 20 -- "$session_dir/logs/denials.jsonl" >&2
        fi
        rm -rf -- "$session_dir"
    fi
    exit "$primary_status"
}
trap 'shutdown "$?"' EXIT
trap 'shutdown 143 TERM' TERM
trap 'shutdown 130 INT' INT
trap 'shutdown 129 HUP' HUP
if [[ "$network_mode" == provider ]]; then
    session_dir=$(umask 077; mktemp -d -- "$CLAUDE_CONTAINER_NETWORK_RUNTIME_DIR/session.XXXXXXXXXXXX")
else
    session_dir=$(umask 077; mktemp -d)
fi
session_token=${session_dir##*/}
printf 'claude-container: network mode=%s\n' "$network_mode" >&2
if [[ "$network_mode" == provider ]]; then
    policy_identity=$(python3 -I "$script_dir/network/control.py" snapshot "${network_preflight[@]}" --session "$session_dir")
    printf 'claude-container: network profile=%s policy=%s\n' "$CLAUDE_CONTAINER_NETWORK_PROFILE" "$policy_identity" >&2
    printf 'claude-container: egress session=%s diagnostics=%s/logs/denials.jsonl\n' "$session_token" "$session_dir" >&2
    proxy_cid=$session_dir/proxy.cid
    proxy_output=$session_dir/proxy.stdout
    proxy_pending=1
    podman create --name "claude-egress-$session_token" --cidfile "$proxy_cid" \
        --label "$proxy_label=$session_token" --read-only --read-only-tmpfs=false \
        --userns=keep-id --user "$caller_uid:$caller_gid" \
        --volume "$session_dir/config:/config:ro" \
        --volume "$session_dir/transport:/transport:rw" \
        --volume "$session_dir/logs:/logs:rw" \
        --env "EGRESS_PROFILE=$CLAUDE_CONTAINER_NETWORK_PROFILE" --env "EGRESS_SESSION=$session_token" \
        "$CLAUDE_CONTAINER_EGRESS_IMAGE" >"$proxy_output" &
    create_pid=$!
    wait "$create_pid"
    create_pid=''
    proxy_id=$(<"$proxy_output")
    [[ "$proxy_id" =~ ^[a-f0-9]{64}$ ]] || die 'invalid egress proxy container ID'
    proxy_pending=0
    podman start "$proxy_id" >"$session_dir/proxy.start" &
    create_pid=$!
    wait "$create_pid"
    create_pid=''
    proxy_deadline=$((SECONDS + 10))
    while [[ ! -f "$session_dir/transport/ready" || ! -S "$session_dir/transport/proxy.sock" ]]; do
        ((SECONDS < proxy_deadline)) || die 'egress proxy unavailable: readiness deadline expired; check immutable image and policy'
        sleep 0.05
    done
    [[ $(<"$session_dir/transport/ready") == "$policy_identity guard=$guard_digest mux=1 tls=tls-clienthello-sni-v1" ]] || die 'egress proxy policy/bootstrap/protocol identity mismatch'
    container_args+=(--volume "$session_dir/transport:/run/claude-egress:ro"
        --volume "$script_dir/network/relay.py:/opt/claude-egress/relay.py:ro"
        --volume "$script_dir/network/mux.py:/opt/claude-egress/mux.py:ro")
    for variable in HTTP_PROXY HTTPS_PROXY http_proxy https_proxy; do
        container_args+=(--env "$variable=http://127.0.0.1:18080")
    done
    container_args+=(--env NO_PROXY=localhost,127.0.0.1,::1 --env no_proxy=localhost,127.0.0.1,::1
        --env CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 --env DISABLE_AUTOUPDATER=1
        --env DISABLE_TELEMETRY=1 --env DISABLE_ERROR_REPORTING=1
        --env ENABLE_CLAUDEAI_MCP_SERVERS=false --env CLAUDE_CODE_DISABLE_ARTIFACT=1
        )
    [[ -z "${ANTHROPIC_API_KEY:-}" ]] || container_args+=(--env ANTHROPIC_API_KEY)
    if ((shell_mode)); then
        args=(/usr/bin/python3 -I /opt/claude-egress/relay.py /bin/bash)
    else
        args=(/usr/bin/python3 -I /opt/claude-egress/relay.py /usr/local/bin/claude "${args[@]}")
    fi
fi
if [[ "$network_mode" != unrestricted ]]; then
    container_args+=(--entrypoint /opt/claude-egress/guard)
    if [[ "$network_mode" == provider ]]; then
        args=(--provider -- "${args[@]}")
    elif ((shell_mode)); then
        args=(--offline -- /bin/bash)
    else
        args=(--offline -- /usr/local/bin/claude "${args[@]}")
    fi
    printf 'claude-container: guard=%s abi-min=3 filter=native-x86_64-v1 mux=1\n' "$guard_digest" >&2
fi
for ((attempt=0; attempt<20; attempt++)); do
    name="$prefix-$next_index"
    cid_file=$session_dir/$attempt.cid
    create_output=$session_dir/$attempt.stdout
    create_error=$session_dir/$attempt.stderr
    creation_pending=1
    podman create --name "$name" --cidfile "$cid_file" --label "$ownership_label=$session_token" \
        "${container_args[@]}" "$image" "${args[@]}" >"$create_output" 2>"$create_error" &
    create_pid=$!
    if wait "$create_pid"; then
        create_pid=''
        container_id=$(<"$create_output")
        [[ "$container_id" =~ ^[a-f0-9]{64}$ ]] || die 'invalid container ID returned by Podman create'
        creation_pending=0
        break
    else
        create_status=$?
        create_pid=''
        if [[ ! -s "$cid_file" && ! -s "$create_output" ]] && creation_lookup container exists "$name" \
            && creation_lookup inspect --type container --format "{{index .Config.Labels \"$ownership_label\"}}" "$name" \
            && [[ $(<"$session_dir/lookup") != "$session_token" ]]; then
            creation_pending=0
            next_index=$((next_index + 1))
        else
            cat -- "$create_error" >&2
            exit "$create_status"
        fi
    fi
done
[[ -n "$container_id" ]] || die 'could not reserve a container name after 20 attempts'

# Explicit stdin redirection prevents Bash from replacing stdin with /dev/null
# for the background client; traps can forward signals while wait is active.
if [[ -f "$script_dir/setup/diagnostics.py" ]] && command -v python3 >/dev/null; then
    # Optional for legacy unrestricted installs without host Python. Only the
    # exact successful Podman 4.3 restart-check line changes level; errors pass.
    mkfifo -- "$session_dir/diagnostics.pipe"
    python3 -I "$script_dir/setup/diagnostics.py" <"$session_dir/diagnostics.pipe" >&2 &
    diagnostics_pid=$!
    exec {diagnostics_fd}>"$session_dir/diagnostics.pipe"
    podman start --attach --interactive "$container_id" <&0 2>&"$diagnostics_fd" {diagnostics_fd}>&- &
    client_pid=$!
    exec {diagnostics_fd}>&-
    diagnostics_fd=''
else
    podman start --attach --interactive "$container_id" <&0 &
    client_pid=$!
fi
status=0
wait "$client_pid" || status=$?
exit "$status"
