## ADDED Requirements

### Requirement: Reference runs the adoption suites before tagging
Before a new `sandbox-ref-N` tag is created, this repository SHALL pass every runner mode that the propagation checklist names for the shared files changed since the previous tag, plus the qualification mode whenever a changed file is digested by qualification. The validation record for the tag SHALL list each of these modes with its result. A mode that cannot run SHALL be recorded as unavailable, and the tag SHALL NOT be created while a listed mode fails.

#### Scenario: Qualification inputs changed
- **WHEN** a change modifies a file that qualification digests, such as the qualification records or a setup module listed as shared code
- **THEN** `bash tests/run-runtime.sh --qualification` passes in this repository before the tag is created, and the validation record shows its result

#### Scenario: Shared test fixture misses a new shared file
- **WHEN** a change adds a file to the shared code digested by qualification, and a shared runtime fixture builds an installation without it
- **THEN** the reference's qualification mode fails before tagging, and the defect is fixed before any wrapper adopts the tag

#### Scenario: Procedure states the rule
- **WHEN** a maintainer reads the step that prepares a new tag in `docs/propagation.md`
- **THEN** it names the checklist that `tools/propagate.py` prints as the minimum set of reference runner modes, and the qualification rule
