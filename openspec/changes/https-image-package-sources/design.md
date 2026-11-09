# Design

## Context

See proposal.md (Why). The facts below were observed on the pinned inputs by
running them offline:

- Base `node:22-bookworm-slim@sha256:4b15…79da`:
  - apt 2.6.1 ships the `https` transport method.
  - `ca-certificates` is not installed, and `/etc/ssl/certs` does not exist.
  - Sources live in `/etc/apt/sources.list.d/debian.sources` (deb822).
    `deb.debian.org/debian` and `deb.debian.org/debian-security` both use
    `http://`.
  - Node v22.23.4 exposes 116 bundled root certificates through
    `tls.rootCertificates`.
- Toolchain base `alpine@sha256:c64c…483b5e` (3.20.10) already uses
  `https://dl-cdn.alpinelinux.org` and ships `ca-certificates.crt`.
- The provider proxy recipe has no `RUN`.
- `npm install` reaches `registry.npmjs.org` over HTTPS using Node's bundled
  roots. It already works on the affected host.
- Setup runs the build through the same-host service (`setup/setup.py`,
  `build_image`). The wrapper's `--container-build` builds the same
  `Containerfile` locally. Both benefit from one recipe change.

## Goals / Non-Goals

**Goals:**
- One recipe, valid on every host, that needs only outbound 443 for image
  preparation.
- Package fetches stay verified end to end. The only trust input beyond the
  base digest is the operator's existing host CA trust selection.

**Non-Goals:**
- Build-time HTTP proxy forwarding, configurable apt/npm mirrors, or a build
  CA separate from host CA trust. Each of these is a separate trust and UX
  decision for a later change.
- Passing the CA to the proxy build, which fetches nothing.
- Porting to the sibling wrappers. Their recipes are per-agent files.

## Decisions

### HTTPS always, not opt-in

Rewrite the deb822 `URIs:` from `http://deb.debian.org/` to
`https://deb.debian.org/` unconditionally, before the first `apt-get update`.

- Alternative: a setup question or build argument. Rejected. It forks the
  recipe into two image identities, adds a question to an already long setup,
  and gains nothing on hosts that allow port 80, where HTTPS works too.

### Trust bootstrap from Node's bundled roots

In the same `RUN` step:
1. Export `require('tls').rootCertificates` to a temporary PEM file. It holds only
   public roots and stays world-readable (default umask), because apt's https
   method drops privileges to the `_apt` user and must read it.
2. Run `apt-get update` and `apt-get install` with
   `-o Acquire::https::CAInfo=<that file>`.
3. Install `ca-certificates` as part of the existing package list.
4. Delete the PEM file before the step ends.

After this, apt uses the system bundle through its default configuration.

- Alternative: `COPY --from=` a CA bundle out of another pinned image, such as
  the proxy's Python base. Rejected. It couples the runtime recipe to a
  second digest that the image-pin checks would have to track.
- Alternative: `Acquire::https::Verify-Peer=false` for the bootstrap.
  Rejected. Signed `Release` files keep package integrity, but disabling
  verification undermines the repository's "preserve certificate validation"
  stance and hides interception.
- Alternative: the host CA bundle unconditionally. Rejected. Builds must not
  read host trust the operator did not opt into. See the next decision for the
  opt-in use.

Node's roots come from the Mozilla CA program, the same source as Debian's
`ca-certificates`, and they are fixed by the base digest. Integrity is still
enforced by apt's `Signed-By` keyring. TLS adds transport confidentiality and
port-443 reachability.

### Host CA trust also covers the runtime image build

Validation on the maintainer's WSL host showed HTTPS to `deb.debian.org`
intercepted by Cato Networks (`CN = Cato Networks Root CA`), so Node's roots
alone fail there, while plain HTTP had worked. Host CA trust is already the
operator's explicit, setup-captured declaration that this network needs an
extra CA.

When it is enabled, the runtime image build receives the selected bundle as
`--secret id=build-ca,src=<bundle>`. The step mounts it with
`RUN --mount=type=secret,id=build-ca,required=false`, appends it to the Node
roots in the bootstrap PEM, and removes the PEM in the same step. When it is
disabled, no secret is passed and the optional mount is empty.

Setup passes the stored `ca_bundle` for the `Containerfile` build only. The
wrapper's `--container-build` passes its resolved `ca_bundle` under
`CLAUDE_CONTAINER_TRUST_HOST_CA`.

Probed on Podman 4.9.3 through a 4.3.1 remote client:
- an absent optional secret builds;
- a present secret is mode 0400 inside the step, so it is copied into the
  world-readable bootstrap PEM for apt's `_apt` method user;
- nothing remains under `/run/secrets` in the image.

A remote Podman client, which setup always uses, uploads each `--secret` file
inside the build context as `podman-build-secret<random>`. The admit-only
`.containerignore` (`**`) dropped it, and the server failed with "rename …
no such file or directory". Admitting `!podman-build-secret*` fixes this. The
file stays in the context tarball only, and no `COPY` references it. If a
future Podman renames it, the build fails closed with the same explicit error.
Local builds read the secret directly.

- Alternative: `COPY` the bundle. Rejected. It persists in a layer and in
  the build context.
- Alternative: a build argument carrying the PEM. Rejected. Build arguments
  are recorded in image history.

### The guard toolchain build takes the same opt-in CA

A 2026-11-09 attempt to build `network/guard-build.Containerfile` on the
maintainer's WSL host failed with `apk`: "certificate verify failed" through
Cato. A restricted setup there would therefore stop at the toolchain even
with host CA trust enabled.

The recipe's `RUN` gains the same optional `build-ca` secret mount:
1. Copy `/etc/ssl/certs/ca-certificates.crt` (Alpine's bundle) into
   `/tmp/apk-bootstrap-ca.pem`.
2. Append the secret when it is present.
3. Run `apk add` with `SSL_CERT_FILE` pointing at that bundle. This was
   probed: `apk` honors it through OpenSSL.
4. Remove the bundle in the same step.

The pinned package versions are unchanged. Setup passes the secret to the
toolchain build under the same `trust_ca` condition as the runtime build.
`network/.containerignore` admits `podman-build-secret*`. These are shared
files, so they are propagated to the sibling wrappers.

### Keep HTTPS sources in the built image

No rewrite back to `http://`. Agents running `apt-get` in unrestricted
sessions then work on the same networks. Runtime network policy is
unaffected.

### Static and image checks

- `tests/test_image_pins.py` gains a transport check. The recipe must rewrite
  the sources to HTTPS before any `apt-get update`, must not contain an
  `http://deb.debian.org` URI, and must not contain `Verify-Peer` or
  `Verify-Host` set to false. Mutated recipes must be rejected, following the
  existing `test_mutated_recipes_are_rejected` pattern.
- `tests/image-smoke.sh` asserts that every `URIs:` line is `https://`, that
  the bootstrap PEM is absent, and that `/etc/ssl/certs/ca-certificates.crt`
  exists.

## Risks / Trade-offs

- [Node's root set differs from the CA chain of the `deb.debian.org` CDN]
  The bootstrap fetch fails closed with a TLS error. No unverified fallback
  exists. Mitigation: a base-digest bump that changes the roots follows
  maintenance and must pass the rebuild acceptance.
- [Networks with TLS interception, host CA trust disabled] The build fails
  closed with a certificate error. On such networks plain HTTP previously
  worked, so this is a regression unless the operator enables host CA trust.
  Mitigation: the error is explicit, and the docs and validation entry name
  host CA trust as the remedy.
- [Selected bundle lacks the interception CA] The build fails closed. The
  operator selects a bundle that includes the CA.
- [Image identity changes] Restricted installations hold a stale qualified
  identity and fail closed until setup or qualification reruns. This is
  intended and must be documented in the validation entry.
- [Package mirror redirects] `deb.debian.org` may redirect over HTTPS to
  other mirrors. Their certificates are verified by the same bootstrap
  bundle.

## Migration Plan

1. Land the recipe change and tests. Rebuild under exact
   `CLAUDE_CONTAINER_MAINTENANCE=1`.
2. Run the image smoke test. On the affected host (port 80 blocked), rerun
   `--container-setup` with refresh, which rebuilds and requalifies. Record
   both results in `docs/validation.md`.
3. Rollback: revert the recipe and rebuild. The setup's last-working-release
   rollback restores the previous activated launcher. Its image identity
   remains valid only where the old image still exists locally.
