# Tasks

## 1. Remove the unconditional host CA mount

- [x] 1.1 Delete the `/etc/ssl/certs/` volume and the three `*_CA_BUNDLE`/`SSL_CERT_FILE` environment entries from `podman_args` in `claude-container.sh`, and verify with `bash -n claude-container.sh` and by inspecting that no host certificate path remains in the array
- [x] 1.2 Verify that with no CA variables set, `podman run` arguments contain no certificate mount or CA environment entries by printing the assembled array in a dry-run check (temporary, not committed)

## 2. Validate the flags and select the bundle

- [x] 2.1 Add `CLAUDE_CONTAINER_TRUST_HOST_CA` parsing modeled on `CLAUDE_YOLO`: `1`/`true`/`yes` enable, `0`/`false`/`no`/empty disable, anything else dies with a message naming the variable; verify each accepted and rejected value with a shell invocation
- [x] 2.2 Add bundle selection: explicit `CLAUDE_CONTAINER_CA_BUNDLE` (die if the file is missing), otherwise the first existing default path, otherwise die asking for `CLAUDE_CONTAINER_CA_BUNDLE`; verify all three branches
- [x] 2.3 Place these checks before the `umask`/`mkdir` block and the image build so a failure creates no directories and builds no image; verify by setting an invalid value and confirming no `podman build` runs

## 3. Mount the bundle and export the variables

- [x] 3.1 When enabled, add a read-only single-file mount of the selected bundle to `/claude-home/ca/bundle.pem` and set `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE` and `NODE_EXTRA_CA_CERTS` to that path; verify the assembled array for enabled mode contains exactly these entries
- [x] 3.2 Verify inside a container (`--container-shell` with trust enabled) that `ls -l /claude-home/ca/bundle.pem` shows the file, that writing to it fails, and that `/etc/ssl/certs/` still contains the image's own certificates

## 4. Help text and documentation

- [x] 4.1 Update the `usage()` Environment section with `CLAUDE_CONTAINER_TRUST_HOST_CA` and `CLAUDE_CONTAINER_CA_BUNDLE`, and verify `./claude-container.sh --container-help` shows them
- [x] 4.2 Document both variables in `README.md`, including the default-off behavior, the Debian/Fedora default paths, the `NODE_EXTRA_CA_CERTS` purpose, and the migration note for users who relied on the old always-on mount; verify with `git diff --check`

## 5. Final verification

- [x] 5.1 Run `bash -n claude-container.sh` and `git diff --check`, and confirm both pass
- [x] 5.2 With Podman available, verify the default start (no trust), the enabled start with a valid bundle, and a child `podman run` still works, as AGENTS.md requires; record the results in the change

## Verification results

Task 5.2, run on the host with Podman:

- Default start, no trust: no `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE` or `NODE_EXTRA_CA_CERTS` in the environment, and `/claude-home/ca/bundle.pem` absent.
- Start with `CLAUDE_CONTAINER_TRUST_HOST_CA=1`: the four variables point at `/claude-home/ca/bundle.pem`, the file is present (`-rw-r--r--`, 183661 bytes), and a child `podman run --rm docker.io/library/alpine true` succeeds.
- `./claude-container.sh --version` prints `2.1.304 (Claude Code)` in both modes.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
