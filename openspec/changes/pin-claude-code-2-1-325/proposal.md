## Why

The image pins Claude Code 2.1.316 (2026-10-31) and OpenSpec 1.16.0. On
2026-11-18 the six repositories agreed on a rule: pin the newest stable
release that was at least 72 hours old at that time. That gives Claude Code
**2.1.325** (2026-11-13) and OpenSpec **2.0.0** (2026-11-11). Later releases
(2.1.326, 2.1.327) were too new. The npm `stable` dist-tag (2.1.311) is older
than the current pin, so it is not used.

## What Changes

- **`Containerfile`**:
  - `CLAUDE_CODE_VERSION` moves from `2.1.316` to `2.1.325`;
  - `OPENSPEC_VERSION` moves from `1.16.0` to `2.0.0`;
  - the base image digest is unchanged.
- **`agent/policies/default.json`**:
  - `tested.cli` becomes 2.1.325, with the date of the new inventory;
  - if the allowed hosts change, the policy gets a new revision.
- **Tests:**
  - `tests/test_image_pins.py`: the diverging-CLI mutation follows the new
    pin, as does the OpenSpec version-range mutation;
  - `tests/test_network_runtime.py`: the version check expects `2.1.325`.
- **Documentation:**
  - `README.md` and `docs/network-contract.md`: the measurement notes name the
    version that was measured;
  - `docs/validation.md`: a dated entry with the endpoint inventory and the
    results.
- **Revalidation:** a new endpoint inventory of 2.1.325 for `anthropic-api` and
  `anthropic-account`, plus the existing credential-free and real-engine
  suites.
- **BREAKING (inside the image):** OpenSpec 2.0 no longer generates `/opsx:*`
  command files. Claude Code sessions in the image use the OpenSpec skills
  (`/openspec-*`) that the project itself installs. The operator's workspace
  migrates at the end of the six-repository effort.

No shared launcher file changes, and the change creates no new reference tag.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None expected. The `network-egress` profiles stay as long as the inventory
finds the same required hosts. If it finds a new required host, the change
gains a `network-egress` delta before implementation goes on; design.md
explains this. Until then `skip_specs: true` applies.

## Impact

- **Files:**
  - `Containerfile` and `agent/policies/default.json`;
  - `tests/test_image_pins.py` and `tests/test_network_runtime.py`;
  - `README.md`, `docs/network-contract.md` and `docs/validation.md`.
- **Image identity:** the image changes. The operator reruns
  `--container-setup` on the three hosts.
- **Deferred checks:** authenticated checks with a real key or account stay
  with the operator, after every repository is done.
