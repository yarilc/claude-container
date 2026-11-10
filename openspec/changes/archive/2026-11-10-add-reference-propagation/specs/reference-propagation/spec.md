## ADDED Requirements

### Requirement: Documented propagation procedure
The repository SHALL document how a change to the shared components reaches the other wrappers: when a new `sandbox-ref-N` tag is needed, how to create it, how to adopt it in each wrapper, which suites to run, how to record the results, and how to update the five-wrapper parity table. A defect found during adoption SHALL be fixed in this repository first and published under a new tag; the other wrappers SHALL NOT carry a fork.

#### Scenario: Maintainer prepares a new reference
- **WHEN** a maintainer changes a shared file and reads the procedure
- **THEN** it states that the change needs a new annotated tag, lists the adoption steps for Codex, OpenCode, Pi and Antigravity, and names the tool that performs the mechanical part

#### Scenario: Adoption reveals a shared defect
- **WHEN** a wrapper's suites fail because of shared code during adoption
- **THEN** the procedure directs the fix to this repository under a new tag, followed by a new adoption, instead of an edit in the wrapper

### Requirement: Verified adoption preconditions
The propagation tool SHALL refuse to change a target checkout unless:
- its git tree is clean;
- its `tests/test_reference_copy.py` names the old tag and that tag's commit in this repository;
- both tags exist here;
- every file in the target's manifest equals the old tag.

Each refusal SHALL name the failed condition and change nothing.

#### Scenario: Target has local edits
- **WHEN** the target checkout has uncommitted changes
- **THEN** the tool exits nonzero naming the dirty tree and writes nothing

#### Scenario: Target is on another reference
- **WHEN** the target's manifest names a tag or commit different from the requested old tag
- **THEN** the tool exits nonzero naming both values and writes nothing

#### Scenario: Target carries a fork
- **WHEN** a copied file in the target differs from the old tag
- **THEN** the tool exits nonzero naming the file and writes nothing

### Requirement: Exact propagation within the adopted scope
The tool SHALL compute the shared files (as listed by the new tag's `tests/test_alignment.py`) modified, added or removed between the tags, limited to the target's adopted scope: its manifest files and additions under a directory it already adopts. A dry run SHALL only print the plan. An applied run SHALL write each file from the new tag byte for byte, delete removed files, and rewrite `REFERENCE_TAG`, `REFERENCE_COMMIT` and the manifest hashes.

#### Scenario: Dry run
- **WHEN** the tool runs without `--apply`
- **THEN** it prints the files to update, add and remove and the documents to touch, and the target is unchanged

#### Scenario: Applied adoption
- **WHEN** the tool runs with `--apply` on a valid target
- **THEN** it creates the branch `adopt-<new tag>`, the target's shared files equal the new tag, and the target's `tests/test_reference_copy.py` passes

#### Scenario: Partially adopted target
- **WHEN** a target has adopted `network/` but not yet `setup/common.py` and the new tag changes `setup/common.py`
- **THEN** the tool leaves `setup/common.py` absent and reports it as outside the adopted scope

### Requirement: Current-state references only
An applied run SHALL replace the old tag and commit with the new ones only in current-state documents:
- the README, `AGENTS.md`, `CONTRIBUTING.md` and `docs/setup.md`;
- the reference line and the `Ported from` and `Reference` parity cells of `docs/network-contract.md`.

It SHALL NOT change `docs/validation.md`, `CHANGELOG.md`, `todo.md` or archived OpenSpec changes, which record history.

#### Scenario: Historical record keeps the old tag
- **WHEN** the target's validation record and changelog mention the old tag
- **THEN** those files are unchanged after the applied run, while the README and the network contract name the new tag

### Requirement: Verification checklist after adoption
After a run, the tool SHALL print the target runner modes to execute (from those its `tests/run-runtime.sh` offers): always the shared suite and the reference-copy check, plus the setup, qualification, network and guard modes when files they exercise changed. It SHALL also print a validation-record template and a commit message. It SHALL NOT run the suites, commit, merge or push.

#### Scenario: Setup files changed
- **WHEN** the propagated files include `setup/setup.py`
- **THEN** the checklist names the target's `--setup` mode, and `--setup-runtime` when the target offers it

#### Scenario: No version-control side effects
- **WHEN** an applied run finishes
- **THEN** the target has an uncommitted working tree on `adopt-<new tag>`, and no commit, merge, tag or push was made
