# Spec Delta

## ADDED Requirements

### Requirement: Single-record delegation verification response
Enabled delegation verification SHALL accept exactly one valid rootless/socket-path response record, with no terminator or one final LF. Additional records, including blank records or extra trailing LF characters, SHALL fail before image operations or launch with an endpoint-specific error. Capture SHALL preserve record boundaries and query failure status. Disabled delegation SHALL continue to skip this separate query.

#### Scenario: Normal delegated response terminator
- **WHEN** the selected service successfully returns one valid response with no final LF or exactly one final LF
- **THEN** delegation verification accepts the response and retains its reported host-side socket path

#### Scenario: Extra blank delegated response records
- **WHEN** the selected service returns a valid first record followed by one or more blank records
- **THEN** startup fails with an invalid-response error naming the selected endpoint
- **AND** no image inspection, explicit build, or launch occurs

#### Scenario: Extra nonblank delegated response records
- **WHEN** the selected service returns a valid first record followed by another nonblank record
- **THEN** startup fails before image operations or launch with an endpoint-specific invalid-response error

#### Scenario: Delegated query fails after emitting valid data
- **WHEN** the selected service query emits valid-looking output but exits nonzero
- **THEN** startup fails with the existing endpoint-specific query-failure guidance
- **AND** the output does not establish rootless operation

#### Scenario: Disabled delegation does not introduce a query
- **WHEN** delegation is disabled, including while using a valid Unix launch endpoint
- **THEN** only mandatory launch-engine verification applies
- **AND** the wrapper performs no separate delegation-response validation or socket query
