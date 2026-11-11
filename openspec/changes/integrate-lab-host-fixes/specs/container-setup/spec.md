# Spec Delta

## ADDED Requirements

### Requirement: Wrapper-built runtime receives host CA trust
When the agent profile builds the runtime image through the wrapper and host CA trust is enabled, setup SHALL give the wrapper's build operation the trust selection and the selected bundle. The wrapper SHALL pass that bundle to its runtime build only as a non-persisted build secret. Without host CA trust, the wrapper's build SHALL receive no host CA.

#### Scenario: Wrapper-built runtime with host CA trust
- **WHEN** setup prepares the runtime image of a wrapper-built profile with host CA trust enabled
- **THEN** the wrapper's build receives the selected bundle as the `build-ca` build secret
- **AND** the built image contains neither the bundle nor its temporary copy

#### Scenario: Wrapper-built runtime without host CA trust
- **WHEN** setup prepares the runtime image of a wrapper-built profile with host CA trust disabled
- **THEN** the wrapper's build receives no build secret and no host CA bundle

#### Scenario: Recipe-built runtime keeps the setup-side secret
- **WHEN** setup prepares the runtime image from the recipe with host CA trust enabled
- **THEN** setup passes the selected bundle to the recipe build as the `build-ca` build secret
