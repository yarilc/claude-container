# Design

## Context

`claude-container.sh` builds the `podman run` argument array in one place. Today it
always adds a read-write mount of `/etc/ssl/certs/` and three CA variables pointing at
`/etc/ssl/certs/ca-certificates.crt`. The image installs `ca-certificates` (see
`Containerfile`), so the directory mount hides the image's bundle. The behavior
requirements are in `specs/host-ca-trust/spec.md`.

The script already validates a boolean-like environment variable (`CLAUDE_YOLO`) with
`case` and `die`, and uses `CLAUDE_CONFIG_DIR`/`CLAUDE_CONTAINER_IMAGE` as overridable
defaults. The new options follow the same patterns.

## Goals / Non-Goals

**Goals:**
- Opt-in host CA trust with a user-selectable bundle file.
- Never expose the host certificate directory, and never make it writable.
- Keep the image's certificate store intact in all modes.

**Non-Goals:**
- Building or modifying the image's CA store (no `update-ca-certificates` at build time).
- Importing individual certificate files or directories; one bundle file only.
- Changing the `runtime-image` capability.

## Decisions

**Opt-in flag plus separate path variable.** `CLAUDE_CONTAINER_TRUST_HOST_CA` decides
whether anything is mounted; `CLAUDE_CONTAINER_CA_BUNDLE` only selects the file. A path
alone would enable trust implicitly, which the default-off requirement rules out.

**Fixed in-container path, e.g. `/claude-home/ca/bundle.pem`.** Mounting a single file
read-only avoids replacing `/etc/ssl/certs/`. `/claude-home` is already a writable
volume, so no new top-level mount point is needed. Alternative considered: mounting
over `/etc/ssl/certs/ca-certificates.crt` itself. Rejected: it depends on the image's
file layout and would still replace the bundle the image ships.

**Bundle detection order.** Explicit `CLAUDE_CONTAINER_CA_BUNDLE` wins. Otherwise the
first existing of `/etc/ssl/certs/ca-certificates.crt` (Debian/Ubuntu) and
`/etc/pki/tls/certs/ca-bundle.crt` (Fedora/RHEL). Detection happens only when trust is
enabled, so the default path does no filesystem checks.

**Four variables, one fixed path.** `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`,
`CURL_CA_BUNDLE` and `NODE_EXTRA_CA_CERTS` all point at the mounted file. Node ignores
`SSL_CERT_FILE`, so `NODE_EXTRA_CA_CERTS` is required for Claude Code itself. It adds
the bundle to Node's built-in roots rather than replacing them, which is the intended
behavior for a corporate CA.

**Validation before any side effects.** Flag and bundle checks run before the image
build and before the `mkdir` calls. An invalid setting fails fast without creating
directories or building the image.

**Leave `:z` and the `~/.config/openspec` mount unchanged.** They are not part of host
CA trust, so this change does not touch them; see Open Questions.

## Risks / Trade-offs

- **Breaking default** → Sessions that depended on the old always-on mount stop
  trusting the host CA. Mitigation: call it out in the proposal and README, and set
  `CLAUDE_CONTAINER_TRUST_HOST_CA=1` in the migration note.
- **Bundle missing on an unusual distro** → Startup fails with an explicit error.
  Mitigation: the error names `CLAUDE_CONTAINER_CA_BUNDLE`.
- **Bundle contents go stale** → The mount is a host file, so host updates apply on
  the next start. No copy is made.
- **Mount-point creation on a read-only root** → Podman creates the target before
  remounting read-only; this must be verified with `--container-shell` in the tasks.

## Open Questions

- Should the `:z` label and the `~/.config/openspec` writable mount be reviewed in a
  separate change? They are unrelated to CA trust and broaden mounts without a
  documented need.
