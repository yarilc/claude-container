# Spec Delta

## ADDED Requirements

### Requirement: Shared components match the sandbox-container reference copy
The shared `network/` and `setup/` components and the shared tests SHALL stay byte-identical to the `sandbox-container` reference at the tag recorded in `tests/test_reference_copy.py`, with that tag's commit and the SHA-256 of every copied file. A shared defect SHALL be fixed in `sandbox-container` and adopted under a new tag, never edited here.

#### Scenario: Copied file changed locally
- **WHEN** a shared file differs from its SHA-256 recorded for the reference tag, or a shared directory gains an unlisted file
- **THEN** the reference-copy test fails naming the file

#### Scenario: Sibling reference checkout
- **WHEN** a `sandbox-container` checkout with the recorded tag sits next to this repository
- **THEN** the reference-copy test checks that the tag resolves to the recorded commit and that the shared files equal that tag

#### Scenario: Adoption of a new tag
- **WHEN** an operator runs `tools/propagate.py` from `sandbox-container` against this repository
- **THEN** the tool accepts it as an adopter of the recorded tag and updates the shared files, the manifest and the current-state references on a new branch
