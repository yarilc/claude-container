## ADDED Requirements

### Requirement: Runtime image inputs are pinned
The image recipe SHALL install exact versions of `@anthropic-ai/claude-code` and `@fission-ai/openspec` recorded in the repository. It SHALL reference the base image by registry digest. No floating tag, `latest` specifier or version range SHALL select an image input. Agent self-update SHALL NOT change the installed version inside a session.

#### Scenario: Build uses recorded versions
- **WHEN** the image is built under explicit maintenance authorization
- **THEN** `claude --version` and `openspec --version` in the resulting image report exactly the recorded versions
- **AND** the base layer comes from the recorded digest

#### Scenario: Unpinned input is rejected by tests
- **WHEN** the recipe names a package without an exact version, uses `@latest`, or references the base image without a digest
- **THEN** the credential-free unit suite fails

### Requirement: Pinned CLI matches the tested policy version
The pinned Claude Code version SHALL equal the CLI version recorded in the protected network policy's tested metadata. A version change SHALL update both in the same change and record the tested version in the validation record.

#### Scenario: Versions diverge
- **WHEN** the pinned CLI version differs from the version in the policy's tested CLI field
- **THEN** the credential-free unit suite fails and names both versions

### Requirement: Version updates follow explicit maintenance
Documentation SHALL describe the update procedure:
- change the recorded versions or base digest;
- rebuild with exact `CLAUDE_CONTAINER_MAINTENANCE=1`;
- revalidate the endpoint inventory when the CLI changes;
- rerun setup or qualification;
- record the outcome in the validation record.

Runtime sessions SHALL NOT update the pinned inputs.

#### Scenario: Maintainer updates the CLI
- **WHEN** a maintainer follows the documented procedure to move to a new CLI version
- **THEN** the procedure requires maintenance authorization for the build, a dated validation entry and requalification of restricted installations
