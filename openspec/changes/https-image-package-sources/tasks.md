# Tasks

## 1. Transport checks

- [x] 1.1 Add the transport check to `tests/test_image_pins.py`. It requires
  the HTTPS source rewrite before the first `apt-get update`, and rejects any
  `http://deb.debian.org` URI and any apt `Verify-Peer`/`Verify-Host` set to
  false. Verify it fails against the current `Containerfile` and that the
  mutated-recipe cases (plain HTTP restored, verification disabled, rewrite
  placed after `apt-get update`) are rejected.
- [x] 1.2 Extend `tests/image-smoke.sh` to assert that every `URIs:` line in
  `/etc/apt/sources.list.d/debian.sources` is `https://`, that the bootstrap
  PEM path is absent, and that `/etc/ssl/certs/ca-certificates.crt` exists.
  Verify with `bash -n tests/image-smoke.sh`.

## 2. Recipe

- [x] 2.1 Change the `Containerfile` install step:
  - export Node's `tls.rootCertificates` to a temporary, world-readable PEM (public roots only; apt's `_apt` sandbox user reads it);
  - rewrite the deb822 `URIs:` to `https://deb.debian.org/`;
  - pass `-o Acquire::https::CAInfo=<pem>` to `apt-get update` and
    `apt-get install`;
  - delete the PEM in the same `RUN` step.

  Keep the version pins and the header comment. Verify with
  `python3 -m unittest discover -s tests -p test_image_pins.py -v`, which
  should pass, including 1.1.
- [x] 2.2 Rebuild under maintenance:
  `CLAUDE_CONTAINER_NETWORK=unrestricted CLAUDE_CONTAINER_MAINTENANCE=1 ./claude-container.sh --container-build`.
  Then run the image smoke test through the wrapper shell. Verify that the
  smoke test passes and that `claude --version` and `openspec --version`
  report 2.1.316 and 1.16.0.
- [x] 2.3 Document that image preparation needs outbound HTTPS (443) to the
  container registry, Debian and npm, and does not need port 80, in
  `README.md` and `docs/setup.md`, next to the existing statement that host
  pulls and build `RUN` steps are outside runtime network filtering. Verify
  with `git diff --check`.

## 3. Host CA trust for the runtime build

- [x] 3.1 Add the optional `build-ca` secret mount to the `Containerfile` step
  and append the secret, when present, to the bootstrap PEM. Extend the
  `tests/test_image_pins.py` transport check: it requires the secret mount to
  be `type=secret` and optional, and rejects any `COPY` or `ADD` of a CA
  bundle. Verify the image-pin suite passes and the mutated cases fail.
- [x] 3.2 In `setup/setup.py`, pass `--secret id=build-ca,src=<ca_bundle>` to
  the runtime `Containerfile` build only when `trust_ca` is enabled, never to
  the proxy build (task 5.2 extends it to the toolchain build). Verify with new `tests/test_setup.py` cases
  covering trust on and off.
- [x] 3.3 In `claude-container.sh`, pass the same secret to both
  `--container-build` and missing-image `podman build` paths only under host
  CA trust. Verify with new `tests/test_wrapper.py` cases covering trust on
  and off, plus `bash -n claude-container.sh`.
- [x] 3.4 Document in `README.md` and `docs/setup.md` (host CA trust section)
  that the selected bundle also verifies the runtime image build's package
  fetches as a non-persisted build secret, and is the remedy for
  TLS-intercepting networks. Verify with `git diff --check`.
- [x] 3.5 On this TLS-intercepted WSL host, build the runtime image under a
  test tag with the `build-ca` secret. Verify that the build succeeds, the
  image smoke checks pass, and no CA material remains under `/tmp` or
  `/run/secrets`. Then build without the secret and verify that it fails
  closed with a certificate error.

## 5. Host CA trust for the guard toolchain build

- [x] 5.1 In `network/guard-build.Containerfile`, add the optional `build-ca`
  secret mount. Build `/tmp/apk-bootstrap-ca.pem` from Alpine's bundle plus
  the secret, run `apk add` with `SSL_CERT_FILE` pointing at it, and remove
  it in the same step, keeping the package pins. Admit
  `podman-build-secret*` in `network/.containerignore`. Verify with a static
  test that the toolchain recipe keeps its pins, mounts the secret only as
  an optional `type=secret`, and removes the bundle.
- [x] 5.2 In `setup/setup.py`, pass the host CA to the toolchain build under
  `trust_ca` (still never to the proxy build). Update the `tests/test_setup.py`
  host-CA case and verify it passes.
- [x] 5.3 On this TLS-intercepted WSL host, build the toolchain with the
  secret. Verify that the build succeeds and that the image contains no
  bootstrap bundle and no "Cato" material. Then build without the secret and
  verify that it fails closed with a certificate error.

## 4. Integration and validation record

- [x] 4.1 Run `python3 -m unittest discover -s tests -p test_wrapper.py -v`
  and `python3 -m unittest discover -s tests -p test_setup.py -v`, with
  `SANDBOX_TEST_TMPDIR` on executable native storage outside the workspace.
  Verify that there are no new failures compared to `main`, and record any
  environment-only failures as such.
- [ ] 4.2 On a host with outbound port 80 blocked, run `--container-setup`
  in provider mode with refresh approved. Verify that the build, guard,
  proxy and qualification complete, and that a managed provider launch
  reaches readiness. If no such host can be exercised, record this as
  operator-reported or unavailable.
- [ ] 4.3 Add a dated entry to `docs/validation.md`. It records the recipe
  change, the unchanged pins and digest, the new runtime image ID, the
  smoke, pin and suite results, the port-80-blocked host outcome, and the
  requirement that restricted installations rerun setup or qualification.
  Verify that the entry lists every check as passed, failed or unavailable.

## Workflow follow-up

- Apply the same recipe fix to the sibling wrappers' `Containerfile`s
  (Codex, Antigravity, OpenCode, Pi) in their own changes.
- Sync the `runtime-image` delta and archive the change after review.
