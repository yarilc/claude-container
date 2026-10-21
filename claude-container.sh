#!/usr/bin/env bash
set -Eeuo pipefail

IMAGE="${CLAUDE_CONTAINER_IMAGE:-localhost/claude-code:latest}"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-${HOME}/.claude}"
WORKSPACE="$(pwd -P)"

usage() {
    cat <<'EOF'
Usage: claude-container.sh [container option] [claude arguments...]

Runs Claude Code in a read-only Podman container. The current directory and
the Claude configuration directory are mounted read/write.

Container options:
  --container-build      build or refresh the container image before starting
  --container-shell      open a shell instead of starting Claude Code
  --container-help       show this wrapper help

All other arguments are passed to Claude Code unchanged.

Environment:
  CLAUDE_CONTAINER_IMAGE  image name (default: localhost/claude-code:latest)
  CLAUDE_CONFIG_DIR       Claude configuration directory (default: ~/.claude)
  CLAUDE_YOLO             enable --dangerously-skip-permissions (default: disabled)
  CLAUDE_CONTAINER_TRUST_HOST_CA  trust a host CA bundle: 1, true, or yes (default: disabled)
  CLAUDE_CONTAINER_CA_BUNDLE      CA bundle file to trust (default: first of
                                  /etc/ssl/certs/ca-certificates.crt and
                                  /etc/pki/tls/certs/ca-bundle.crt)
EOF
}

die() { printf 'claude-container: %s\n' "$*" >&2; exit 1; }

container_prefix="${WORKSPACE##*/}"
container_prefix="$(printf '%s' "$container_prefix" | sed -E 's/[^[:alnum:]_.-]+/-/g; s/^[.-]+//; s/[.-]+$//')"
[[ -n "$container_prefix" ]] || container_prefix="claude-container"

container_name() {
    local highest=-1 name suffix
    while IFS= read -r name; do
        [[ "$name" == "$container_prefix"-* ]] || continue
        suffix="${name#"$container_prefix"-}"
        [[ "$suffix" =~ ^[0-9]+$ ]] || continue
        if (( suffix > highest )); then
            highest="$suffix"
        fi
    done < <(podman ps --format '{{.Names}}')
    printf '%s-%d\n' "$container_prefix" "$((highest + 1))"
}

build_image=0
shell_mode=0
args=()
while (($#)); do
    case "$1" in
        --container-build) build_image=1; shift ;;
        --container-shell) shell_mode=1; shift ;;
        --container-help) usage; exit 0 ;;
        *) args+=("$1"); shift ;;
    esac
done

command -v podman >/dev/null || die "podman is not installed on the host"

trust_host_ca=0
case "${CLAUDE_CONTAINER_TRUST_HOST_CA:-}" in
    1|true|TRUE|yes|YES) trust_host_ca=1 ;;
    ''|0|false|FALSE|no|NO) ;;
    *) die "CLAUDE_CONTAINER_TRUST_HOST_CA must be 0, 1, true, false, yes, or no" ;;
esac

ca_bundle=""
if ((trust_host_ca)); then
    if [[ -n "${CLAUDE_CONTAINER_CA_BUNDLE:-}" ]]; then
        [[ -f "$CLAUDE_CONTAINER_CA_BUNDLE" ]] || die "CLAUDE_CONTAINER_CA_BUNDLE is not a file: $CLAUDE_CONTAINER_CA_BUNDLE"
        ca_bundle="$(readlink -f -- "$CLAUDE_CONTAINER_CA_BUNDLE")"
    else
        for candidate in /etc/ssl/certs/ca-certificates.crt /etc/pki/tls/certs/ca-bundle.crt; do
            if [[ -f "$candidate" ]]; then
                ca_bundle="$candidate"
                break
            fi
        done
        [[ -n "$ca_bundle" ]] || die "no default CA bundle found; set CLAUDE_CONTAINER_CA_BUNDLE to a bundle file"
    fi
fi

umask 077
mkdir -p \
    "${HOME}/.claude" \
    "${HOME}/.local/share" \
    "${HOME}/.config/openspec" \
    "${HOME}/.cache"

[[ -d "$CLAUDE_DIR" ]] || mkdir -p "$CLAUDE_DIR"

claude_args=("${args[@]}")
case "${CLAUDE_YOLO:-}" in
    1|true|TRUE|yes|YES)
        ((shell_mode)) || claude_args=(--dangerously-skip-permissions "${args[@]}")
        ;;
    ''|0|false|FALSE|no|NO) ;;
    *) die "CLAUDE_YOLO must be 0, 1, true, false, yes, or no" ;;
esac

runtime_dir="/run/user/$(id -u)"
socket="${runtime_dir}/podman/podman.sock"
[[ -S "$socket" ]] || die "Podman socket not found: $socket (start 'podman system service --time=0' or enable podman.socket)"

if ((build_image)) || ! podman image exists "$IMAGE"; then
    podman build --tag "$IMAGE" --file "$SCRIPT_DIR/Containerfile" "$SCRIPT_DIR"
fi

podman_args=(
    --rm --interactive --tty
    --name "$(container_name)"
    --read-only
    --userns=keep-id
    --user "$(id -u):$(id -g)"
    --workdir "$WORKSPACE"
    --tmpfs /tmp:rw,nosuid,nodev,noexec,size=256m
    --tmpfs /run:rw,nosuid,nodev,noexec,size=16m
    --env HOME=/claude-home
    --env CLAUDE_CONFIG_DIR=/claude-home/.claude
    --env CONTAINER_HOST=unix:///run/podman/podman.sock
    --volume "$WORKSPACE:$WORKSPACE:rw"
    --volume "$CLAUDE_DIR:/claude-home/.claude:rw"
    --volume "${HOME}/.config/openspec:/claude-home/.config/openspec:rw,z"
    --volume "$socket:/run/podman/podman.sock"
)

if ((trust_host_ca)); then
    podman_args+=(
        --volume "$ca_bundle:/claude-home/ca/bundle.pem:ro"
        --env "SSL_CERT_FILE=/claude-home/ca/bundle.pem"
        --env "REQUESTS_CA_BUNDLE=/claude-home/ca/bundle.pem"
        --env "CURL_CA_BUNDLE=/claude-home/ca/bundle.pem"
        --env "NODE_EXTRA_CA_CERTS=/claude-home/ca/bundle.pem"
    )
fi

if ((shell_mode)); then
    podman_args+=(--entrypoint /bin/bash)
    podman run "${podman_args[@]}" "$IMAGE"
else
    podman run "${podman_args[@]}" "$IMAGE" "${claude_args[@]}"
fi
