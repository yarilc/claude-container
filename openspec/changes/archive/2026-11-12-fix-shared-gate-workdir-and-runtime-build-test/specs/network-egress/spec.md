# Spec Delta

## ADDED Requirements

### Requirement: Qualification containers do not depend on the image working directory
Every container that local enforcement qualification starts from the runtime image SHALL set its working directory to `/` explicitly. This covers the gate's certificate, control and peer containers and the security-identity probe. The engine SHALL therefore never create or change the ownership of an image working directory for these containers, whatever `WORKDIR` the runtime image declares.

#### Scenario: Runtime image with a WORKDIR missing from its layers
- **WHEN** a wrapper's runtime image declares `WORKDIR /workspace` without creating it in a build step, and qualification runs
- **THEN** the qualification containers start in `/` and the engine does not create `/workspace` in them

#### Scenario: Host with a domain UID under keep-id
- **WHEN** qualification runs as a caller whose UID cannot be used for an engine-side chown under `--userns=keep-id`
- **THEN** no qualification container fails on a working-directory chown

#### Scenario: Probe behavior unchanged
- **WHEN** the control probe, peer and security probe run in `/`
- **THEN** they reach their fixtures by absolute paths and produce the same evidence as before
