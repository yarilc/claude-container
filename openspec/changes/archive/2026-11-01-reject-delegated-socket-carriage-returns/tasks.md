# Tasks

## 1. Harden delegated-socket response validation

- [x] 1.1 Add a CR rejection guard after successful delegation-response capture and before LF handling or field parsing in `claude-container.sh`; preserve query-failure handling and endpoint-specific diagnostics, and verify Bash syntax with `bash -n claude-container.sh`.
- [x] 1.2 Extend `tests/test_wrapper.py` with CRLF, final CR without LF, leading CR, CR in the rootless field, CR between fields, and CR inside the reported path; verify ordinary startup and `--container-build` both fail with an endpoint-specific invalid-response error and no `image`, `build`, or `create` calls using the targeted regression tests.
- [x] 1.3 Retain or extend regression assertions for valid responses with zero/one final LF, exact mount paths containing spaces, additional-record rejection, failed queries including CR-containing stdout, and skipped socket queries with delegation disabled; verify the targeted response tests pass without changing query-error precedence.
- [x] 1.4 Update README and wrapper help to state that delegated responses containing any CR are rejected, including CRLF; verify `./claude-container.sh --container-help` succeeds and both documents agree with the delta specification.

## 2. Integration verification and completion record

- [x] 2.1 Run `python3 -m unittest discover -s tests -p test_wrapper.py -v`, `bash -n claude-container.sh`, `git diff --check`, and `openspec validate reject-delegated-socket-carriage-returns --strict`; verify all applicable checks pass. Run applicable rootless runtime checks when the built image and service are available, and record passed, failed, or unavailable checks with versions in `docs/validation.md`.
- [x] 2.2 After successful regression verification, mark the remaining item in `todo.md` complete and adjust its surrounding text to reflect that no listed work remains; verify the completion claim matches the test results and validation record.

## Workflow follow-up

- Sync the delta into the main `container-podman-access` specification through the normal sync or archive workflow when requested.
