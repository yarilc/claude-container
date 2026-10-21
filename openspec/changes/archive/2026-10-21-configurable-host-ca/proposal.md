# Proposal

## Why

The wrapper currently mounts the host's `/etc/ssl/certs/` read-write and always
exports CA bundle variables pointing at `/etc/ssl/certs/ca-certificates.crt`.
This is unconditional, hides the image's own certificates, assumes a Debian/Ubuntu
bundle path, and gives the container write access to the host trust store. Users
behind a corporate TLS proxy need to opt in to trusting their CA, and only with the
bundle they choose.

## What Changes

- Host CA trust is disabled by default. The container gets no host certificate mount
  and no CA bundle variables unless the user opts in.
- `CLAUDE_CONTAINER_TRUST_HOST_CA` enables host CA trust when set to `1`, `true`,
  `yes` (case-insensitive variants accepted, as with `CLAUDE_YOLO`). Other values
  are rejected with an actionable error.
- `CLAUDE_CONTAINER_CA_BUNDLE` selects the bundle file. When unset, the wrapper uses
  the first existing file among `/etc/ssl/certs/ca-certificates.crt` and
  `/etc/pki/tls/certs/ca-bundle.crt`. When set to a missing file, the wrapper fails
  with an error naming the variable and the path.
- When enabled, only the selected bundle file is mounted read-only at a fixed path
  inside the container. The image's certificate directory is not replaced.
- When enabled, `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE` and
  `NODE_EXTRA_CA_CERTS` point at that fixed path.
- **BREAKING**: sessions that relied on the previous always-on host certificate mount
  must set `CLAUDE_CONTAINER_TRUST_HOST_CA=1`.
- `--container-help` and `README.md` document the new variables.

## Capabilities

### New Capabilities
- `host-ca-trust`: How the wrapper decides whether to trust a host CA bundle inside
  the container, which bundle is used, and how it is mounted and exposed to tools.

### Modified Capabilities

## Impact

- `claude-container.sh`: argument/environment validation, bundle selection, mount and
  environment assembly, help text.
- `README.md`: usage and environment variable documentation.
- Container runtime: the host certificate directory is no longer mounted by default.
- No change to the `Containerfile` or to the `runtime-image` capability.
