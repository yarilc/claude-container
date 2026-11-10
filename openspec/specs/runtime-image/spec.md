# runtime-image Specification

## Purpose

The runtime image provides the command-line tools needed by Claude Code sessions and commands run inside the container.

## Requirements

### Requirement: Python 3 is available in the runtime image
The runtime image SHALL provide the Python 3 interpreter through the `python3` command.

#### Scenario: Invoke Python 3
- **WHEN** a user runs `python3 --version` in a container started from the runtime image
- **THEN** the Python 3 interpreter reports its version and exits successfully

### Requirement: Bubblewrap is available in the runtime image
The runtime image SHALL provide Bubblewrap through the `bwrap` command.

#### Scenario: Invoke Bubblewrap
- **WHEN** a user runs `bwrap --version` in a container started from the runtime image
- **THEN** Bubblewrap reports its version and exits successfully

### Requirement: A terminal editor is available in the runtime image
The runtime image SHALL provide the `nano` terminal editor through the `nano` command.

#### Scenario: Invoke nano
- **WHEN** a user runs `nano --version` in a container started from the runtime image
- **THEN** nano reports its version and exits successfully

### Requirement: The runtime image sets the default editor
The runtime image SHALL set the `EDITOR` and `VISUAL` environment variables to `nano`, so commands that open an editor use it without further configuration.

#### Scenario: Editor variables inside the container
- **WHEN** a user runs `echo "$EDITOR" "$VISUAL"` in a container started from the runtime image
- **THEN** both values are `nano`

#### Scenario: Host editor is not forwarded
- **WHEN** the host sets `EDITOR` to an editor that the runtime image does not provide
- **THEN** the container still sets `EDITOR` and `VISUAL` to `nano`

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

### Requirement: Image package sources use verified HTTPS
The runtime image recipe SHALL fetch Debian packages only from `https://` sources, with TLS peer verification enabled for every fetch. The build SHALL NOT require outbound port 80 and SHALL NOT fall back to plain HTTP. The built image SHALL keep HTTPS Debian sources.

#### Scenario: Host blocks outbound port 80
- **WHEN** the runtime image is built under maintenance authorization on a host where outbound TCP 80 is blocked and HTTPS to the Debian, npm and container registries is reachable
- **THEN** the build completes and the image reports the recorded Claude Code and OpenSpec versions

#### Scenario: Built image keeps HTTPS sources
- **WHEN** a user inspects the Debian source configuration inside a container started from the runtime image
- **THEN** every Debian source URI uses `https://`

#### Scenario: Insecure transport is rejected by tests
- **WHEN** the recipe uses a plain-HTTP Debian source or disables apt TLS peer or host verification
- **THEN** the credential-free unit suite fails and names the violation

### Requirement: Package-source trust bootstrap uses pinned inputs and opt-in host CA
Before Debian `ca-certificates` is installed, the recipe SHALL verify HTTPS package fetches with roots from the digest-pinned base image, plus the operator's selected CA bundle only when host CA trust is enabled. It SHALL add no image, digest or download input. It SHALL remove the bootstrap bundle in the same build step, and the built image SHALL contain Debian `ca-certificates`.

#### Scenario: No bootstrap residue
- **WHEN** a user lists the bootstrap bundle path inside a container started from the runtime image
- **THEN** the file does not exist
- **AND** the Debian `ca-certificates` package is installed

#### Scenario: Host CA trust disabled
- **WHEN** setup or `--container-build` builds the runtime image with host CA trust disabled
- **THEN** the build receives no host CA bundle and verifies only against the base image's roots

#### Scenario: TLS-intercepting network with host CA trust
- **WHEN** setup or `--container-build` builds the runtime image with host CA trust enabled and a CA bundle that includes the network's interception CA
- **THEN** the build receives that bundle only as a build secret, the HTTPS package fetches verify against it, and the build completes

#### Scenario: Host CA bundle is not persisted
- **WHEN** a user searches a container started from an image built with host CA trust enabled
- **THEN** neither the bootstrap bundle nor the build secret is present in the image
