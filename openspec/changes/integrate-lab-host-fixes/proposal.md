# Proposal

## Why

The branch `test/podman5-socket-url` holds the fixes that made the sandbox
work on a Rocky Linux 9 lab host and on a newer WSL host. These are Podman 5
socket URLs, undelegated cgroup controllers, kernels without IPv6, the RHEL
`/run/secrets` mount, crun 1.27 terminals and HTTPS-only package fetches. The
branch forked at `sandbox-ref-2`, while `main` has since reached
`sandbox-ref-10`. A plain merge stops on three conflicts and two failing setup
tests, so the fixes cannot reach `main` or the sibling wrappers yet.

## What Changes

- Merge `test/podman5-socket-url` into `main` and keep the branch behavior
  as it is. Its five archived changes and the main specs they synced
  come in with the merge:
  - `adapt-budgets-to-delegated-controllers`
  - `allow-terminal-on-read-only-dev`
  - `https-image-package-sources`
  - `mask-engine-default-run-secrets`
  - `qualify-ipv6-disabled-kernels`

  The Podman 5 `unix://` socket fix also comes in with the merge.
  - **BREAKING (policy, from the branch):** budgets whose cgroup
    controller is not delegated are not enforced.
  - **BREAKING (from the branch):** the qualification identity, the code
    digests and the runtime image identity change. Restricted
    installations must rebuild and rerun setup or qualification.
- Resolve the conflicts:
  - `setup/setup.py`: keep the `main` runtime-build dispatch, which builds
    from the recipe or through the wrapper, and add the branch's host CA
    build secret to the recipe path;
  - `openspec/specs/container-setup/spec.md`: keep the `main` requirements
    and the branch requirements;
  - `tests/test_setup.py`: keep both sets of tests, adapted to the merged
    runtime-build call.
- Fix the two setup smoke tests that fail on the branch, which predate the
  engine controller query in the smoke. Only the tests change.
- Name the contract for wrapper-built runtimes: when host CA trust is
  enabled, the wrapper's build operation receives the selected bundle and
  passes it to its build as a non-persisted secret.
- Record the validation and publish the merge as annotated tag
  `sandbox-ref-11`, so it can be propagated with `tools/propagate.py`.
- **Not changed:** the guard's acceptance of a read-only tmpfs at
  `/run/secrets` stays exactly as on the branch. A stricter check (fresh,
  empty mount) is deferred until the operator has run the host tests.
- **Not in scope:** adopting the tag in the Codex, OpenCode, Pi and
  Antigravity wrappers, and porting their launcher and `Containerfile`
  adaptations. Each wrapper gets its own follow-up change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-setup`: adds the host CA build-secret contract for profiles
  whose runtime image is built by the wrapper. All other requirement
  changes arrive with the merged branch's already-synced main specs.

## Impact

- Shared code (`network/`, `setup/`, shared tests). This is the branch
  content plus the conflict resolution in `setup/setup.py` and
  `tests/test_setup.py`.
- Wrapper: `claude-container.sh`, `Containerfile`, `tests/test_wrapper.py`,
  `tests/test_image_pins.py`. These come from the branch unchanged.
- Docs: `AGENTS.md`, `README.md`, `docs/setup.md`,
  `docs/network-contract.md` (the parity table moves to `sandbox-ref-11`),
  `docs/validation.md` (a new section for `sandbox-ref-11`).
- Existing installations on every host must rebuild the images and rerun
  setup.
- The sibling wrappers adopt `sandbox-ref-11` later, in their own changes.
