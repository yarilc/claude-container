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
    --volume "$socket:/run/podman/podman.sock"
)

if ((shell_mode)); then
    podman_args+=(--entrypoint /bin/bash)
    podman run "${podman_args[@]}" "$IMAGE"
else
    podman run "${podman_args[@]}" "$IMAGE" "${claude_args[@]}"
fi
