## ADDED Requirements

### Requirement: Provider residual exfiltration acknowledgement
When provider mode is selected, setup SHALL show a residual-exfiltration notice before authentication questions. The notice SHALL state that the allowed hosts of the selected profile can receive workspace data sent with attacker-supplied credentials. Setup SHALL require explicit acknowledgement. Declining SHALL return to the network-mode choice and SHALL NOT select another mode on the operator's behalf. The acknowledgement is not stored.

#### Scenario: Operator acknowledges the notice
- **WHEN** the operator selects provider mode and acknowledges the notice
- **THEN** setup continues with the authentication question
- **AND** the setup plan and saved preferences are otherwise unchanged

#### Scenario: Operator declines the notice
- **WHEN** the operator selects provider mode and declines the acknowledgement
- **THEN** setup asks for the network mode again, with no mode silently substituted
- **AND** no installation, image or state mutation has occurred

#### Scenario: Rerun or non-provider mode
- **WHEN** setup is rerun with saved provider mode, or offline or unrestricted mode is selected
- **THEN** a provider selection asks for the acknowledgement again
- **AND** offline and unrestricted selections do not show the provider notice
