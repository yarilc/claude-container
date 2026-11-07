#!/usr/bin/env bash
# Operator-only packaging. No network or host package installation is required.
set -Eeuo pipefail
project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
[[ ${CLAUDE_CONTAINER_MAINTENANCE:-} == 1 ]] || { printf 'Guard packaging requires exact CLAUDE_CONTAINER_MAINTENANCE=1.\n' >&2; exit 1; }
[[ $# == 1 && $1 == /* ]] || { printf 'Usage: build-guard.sh /absolute/native/output-directory\n' >&2; exit 64; }
output_dir=$(realpath -e -- "$1")
[[ -d $output_dir && -O $output_dir && -w $output_dir ]] || { printf 'Output must be an existing caller-owned writable native directory.\n' >&2; exit 1; }
toolchain=$(podman image inspect --format '{{.Id}}' "${CLAUDE_GUARD_TOOLCHAIN:-localhost/claude-guard-toolchain:development}")
[[ $toolchain =~ ^(sha256:)?[a-f0-9]{64}$ ]] || { printf 'A prepared immutable toolchain image ID is required.\n' >&2; exit 1; }
artifact=$(mktemp -- "$output_dir/.guard.XXXXXXXXXXXX")
cleanup() { rm -f -- "$artifact"; }
trap cleanup EXIT
podman run --rm --network=none --read-only --userns=keep-id --user "$(id -u):$(id -g)" \
    --volume "$project_root:$project_root:ro" --volume "$output_dir:$output_dir:rw" \
    --workdir "$project_root" --env LC_ALL=C --env SOURCE_DATE_EPOCH=0 \
    "$toolchain" -std=c11 -O2 -static -Wall -Wextra -Werror -D_FORTIFY_SOURCE=2 \
    -fstack-protector-strong -fno-ident -Wl,--build-id=none \
    -I "$project_root/network" "$project_root/network/guard.c" -o "$artifact"
chmod 0555 -- "$artifact"
"$artifact" --version
mv -f -- "$artifact" "$output_dir/claude-egress-guard"
(cd -- "$output_dir" && sha256sum claude-egress-guard > claude-egress-guard.sha256)
printf 'Packaged guard with toolchain %s\n' "$toolchain" >&2
