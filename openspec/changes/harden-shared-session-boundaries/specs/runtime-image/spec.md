# Spec Delta

## ADDED Requirements

### Requirement: The image working directory exists in a layer
Every `WORKDIR` in the runtime image recipe SHALL name a directory that an earlier build step creates, so that the engine never creates or changes the ownership of the working directory when a container starts.

#### Scenario: Session on a host with a domain UID
- **WHEN** a container starts from the runtime image as a caller whose UID cannot be used for an engine-side chown under `--userns=keep-id`
- **THEN** it does not fail on the image working directory

#### Scenario: Missing directory is rejected by tests
- **WHEN** the recipe declares a `WORKDIR` that no earlier build step creates
- **THEN** the credential-free unit suite fails naming the directory
