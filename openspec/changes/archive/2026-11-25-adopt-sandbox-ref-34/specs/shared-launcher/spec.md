# Spec Delta

## MODIFIED Requirements

### Requirement: Claude launcher tests cover only Claude's part
Claude's launcher behavior SHALL be tested by the shared `tests/test_launcher.py` and `tests/fake_podman.py`, copied unchanged from the reference tag. `tests/test_wrapper.py` SHALL test only:
- Claude's hooks;
- Claude's agent data;
- its credential and provider settings;
- its shipped policy inventories;
- the real image.

A Claude launcher case that the shared tests do not cover SHALL be added to the reference before this wrapper adopts it, not kept as a wrapper copy.

#### Scenario: Wrapper runtime tests
- **WHEN** `bash tests/run-runtime.sh --wrapper` runs
- **THEN** it runs both `tests/test_launcher.py` and `tests/test_wrapper.py` against this checkout

#### Scenario: Approval bypass combinations
- **WHEN** `tests/test_wrapper.py` runs `CLAUDE_YOLO` enabled and disabled in unrestricted shared and isolated modes
- **THEN** only `CLAUDE_YOLO` determines the `--dangerously-skip-permissions` argument, and no combination mounts a Podman socket
