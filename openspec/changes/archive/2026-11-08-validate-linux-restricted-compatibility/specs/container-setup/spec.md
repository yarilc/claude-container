# Spec Delta

## MODIFIED Requirements

### Requirement: Verified readiness with separate authentication status
Setup SHALL declare the selected sandbox ready only after installed-path checks, engine verification, artifact validation and a smoke launch succeed through the actual selected runtime path. Restricted candidates SHALL additionally pass the installation enforcement gate and publish its protected matching report before activation. Completion output SHALL separately report authentication as verified, pending or not applicable, provide the launch/rerun commands and identify PATH requirements.

#### Scenario: Sandbox smoke check succeeds
- **WHEN** the selected installation passes its smoke check
- **THEN** setup reports sandbox readiness and the resolved managed launch command
- **AND** a version or shell smoke check alone does not imply authenticated provider success

#### Scenario: Login or optional authentication check skipped
- **WHEN** the sandbox is usable but authentication was skipped, unavailable or failed
- **THEN** setup reports sandbox ready and authentication pending with the appropriate next command
- **AND** it does not claim a working authenticated model request

#### Scenario: Enforcement check fails
- **WHEN** the restricted gate cannot install required enforcement, fails a required control or cannot publish a protected matching report
- **THEN** setup reports incomplete setup, returns nonzero and does not activate the candidate installation

#### Scenario: Setup repeats qualification after relevant updates
- **WHEN** setup prepares changed kernel, engine/backend, security-policy state, protected enforcement code, container hardening or effective image/policy identities
- **THEN** it reruns qualification for the candidate and preserves the previous activation until successful report publication
- **AND** interruption or failed revalidation never replaces the previous report with an apparent pass

#### Scenario: Local qualification and measured acceptance differ
- **WHEN** a candidate passes locally on a combination without recorded full release acceptance
- **THEN** setup identifies it as locally qualified and not release-measured
- **AND** active SELinux/AppArmor is reported without guaranteeing compatibility or claiming authentication success


## ADDED Requirements

### Requirement: Protected installation qualification records
Qualification SHALL produce a versioned non-secret report outside all application-writable mounts, bound to the actual engine/host and enforcement inputs. It SHALL record required check outcomes, control evidence and environment identities. Only a complete successful result SHALL authorize the matching restricted workflow; agent-controlled settings SHALL NOT manufacture qualification.

#### Scenario: Successful atomic publication
- **WHEN** the candidate completes every mandatory gate check
- **THEN** setup publishes the protected matching report atomically before activating the candidate
- **AND** the report identifies kernel/boot, architecture, ABI, engine/backend, security policy, guard/code, images, mode/profile/policy, hardening and gate revision
- **AND** it contains no credentials, model content or authentication URLs

#### Scenario: Invalid or unsafe report
- **WHEN** a report is missing, malformed, incomplete, stale, symlink-escaped or accessible through an application-writable mount
- **THEN** it cannot establish readiness and setup reports the reason without repairing existing permissions

#### Scenario: Manual protected installation
- **WHEN** an operator prepares restricted assets without the managed setup workflow
- **THEN** an explicit qualification operation can generate the same report using only protected fixtures and disposable synthetic state
- **AND** normal application execution cannot use that operation to bypass report validation
