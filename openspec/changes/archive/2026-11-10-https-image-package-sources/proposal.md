# Proposal

## Why

The runtime image build fails on hosts that block outbound port 80: the pinned
base `node:22-bookworm-slim` fetches Debian packages from `http://deb.debian.org`
and `apt-get update` times out. An operator on such a network (outbound TLS on
443 allowed, no HTTP proxy) cannot complete setup at all. Simply switching the
sources to `https://` fails too, because the slim base has no `ca-certificates`
and those certificates are themselves installed through apt. Conversely, on
networks that intercept TLS (for example Cato Networks on the maintainer's WSL
host), HTTPS fetches only verify against the operator's interception CA, which
host CA trust already captures.

## What Changes

- The runtime image recipe fetches Debian packages only over HTTPS, with full
  certificate verification, on every host. There is no operator option and no
  HTTP fallback.
- A temporary trust bundle, exported from the root certificates built into the
  pinned base image's Node.js runtime, verifies those HTTPS fetches until the
  Debian `ca-certificates` package is installed. The bundle is then removed.
  This adds no new image input, digest or download.
- When the operator enabled host CA trust, the same selected CA bundle is also
  given to the runtime image build as a build secret and appended to the
  bootstrap bundle, so TLS-intercepting networks still verify. The secret is
  never stored in an image layer. Without host CA trust, no host CA is read.
  Setup preparation and the wrapper's `--container-build` behave the same way.
- The built image keeps HTTPS Debian sources.
- Credential-free tests reject a recipe that uses plain-HTTP Debian sources or
  disables apt TLS peer verification.
- The changed recipe is a pinned-input change. It follows the documented
  maintenance procedure: rebuild, a dated validation entry, and
  requalification of restricted installations, because the runtime image
  identity changes.
- The guard toolchain recipe already uses HTTPS Alpine repositories, but its
  bundled CA fails on TLS-intercepting networks (observed: `apk` certificate
  verification failed through Cato). With host CA trust enabled, setup also
  passes the `build-ca` secret to the toolchain build. There, `apk` verifies
  against Alpine's bundle plus the secret, and the temporary bundle is
  removed in the same step. `network/.containerignore` admits
  `podman-build-secret*`.
- Not changed: the provider proxy recipe has no package-fetch step. This
  change adds no build-time proxy forwarding and no configurable mirror.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-setup`: with host CA trust enabled, setup image preparation also
  verifies the guard toolchain's package fetches against the selected bundle,
  as a non-persisted build secret.

- `runtime-image`: the pinned recipe also guarantees that Debian package
  sources use verified HTTPS during the build and in the built image,
  bootstrapped from inputs already pinned by the base digest plus, only with
  host CA trust enabled, the operator's selected CA bundle as a build secret.

## Impact

- `Containerfile`: the source rewrite and trust bootstrap are added to the
  package installation step, with an optional `build-ca` secret mount.
- `setup/setup.py` (shared) and `claude-container.sh`: the runtime image build
  passes `--secret id=build-ca,src=<bundle>` only when host CA trust is
  enabled. `tests/test_setup.py` and `tests/test_wrapper.py` cover both cases.
- `tests/test_image_pins.py`: transport and verification checks are added.
- `docs/validation.md`: a dated maintenance entry. Requalification is recorded.
- `README.md` and `docs/setup.md`: a short note that image preparation needs
  outbound HTTPS (443) to the Debian, npm and container registries, and does
  not need port 80.
- Existing installations must rebuild the runtime image and rerun setup or
  qualification. Restricted launches fail closed on the stale image identity
  until they do.
- The sibling wrappers (Codex, Antigravity, OpenCode, Pi) own their recipes
  separately. They are out of scope here, but should receive the same fix.
