## ADDED Requirements

### Requirement: Agent profile in the protected installation
Setup SHALL install the agent profile and its provider policy file together with the shared sandbox components, validate them in the native installation, and use them as qualification inputs. Rollback SHALL restore the profile matching the restored installation.

#### Scenario: Installation from a checkout
- **WHEN** setup prepares a native installation from a checkout
- **THEN** it copies and validates the profile and provider policy with the other protected inputs before candidate qualification and activation

#### Scenario: Rollback after failed activation
- **WHEN** setup restores a previous installation after a failed update
- **THEN** the restored profile, policy, code and qualification report belong to the same installation
