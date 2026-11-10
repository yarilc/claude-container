# Spec Delta

## ADDED Requirements

### Requirement: Host CA trust covers setup package fetches
When host CA trust is enabled, setup SHALL give the selected CA bundle to the runtime image and guard toolchain builds only as a non-persisted build secret, so their HTTPS package fetches verify on TLS-intercepting networks. Without host CA trust, setup SHALL pass no host CA to any build. The proxy build SHALL never receive it.

#### Scenario: Toolchain build on a TLS-intercepting network
- **WHEN** setup prepares the guard toolchain with host CA trust enabled and a bundle containing the interception CA
- **THEN** the toolchain package fetches verify against that bundle and the build completes
- **AND** the toolchain image contains neither the bundle nor its temporary copy

#### Scenario: Host CA trust disabled
- **WHEN** setup prepares images with host CA trust disabled
- **THEN** no build receives a host CA bundle, and the toolchain build verifies only against the base image's certificates
