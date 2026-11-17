# Spec Delta

## MODIFIED Requirements

### Requirement: Operator-selected runtime modes
The wrapper SHALL accept `CLAUDE_CONTAINER_NETWORK=offline|provider|unrestricted` from explicit operator configuration or validated managed preferences. An ordinary launch with an unset or empty effective mode SHALL select `provider`. Without the provider settings, it SHALL stop with setup guidance before runtime preparation. Other values SHALL fail before image operations. Only explicit `unrestricted` SHALL remove the runtime destination boundary. Agent-writable configuration SHALL NOT select or broaden the outer policy.

#### Scenario: Default and invalid selection
- **WHEN** an ordinary invocation leaves the effective mode unset or empty
- **THEN** it runs in provider mode with every provider check, or receives setup guidance when the provider settings are missing
- **AND** an unknown nonempty mode fails with the invalid-mode diagnostic without image operations or agent startup

#### Scenario: Policy cannot escalate itself
- **WHEN** workspace settings, application state, or commands request a broader policy or remove proxy variables
- **THEN** the running session retains its operator-selected outer boundary

#### Scenario: Explicit offline operation
- **WHEN** an operator explicitly chooses offline mode or a validated managed launcher supplies saved offline mode
- **THEN** the wrapper applies all existing restricted platform, protected-installation, guard and qualification requirements
- **AND** the resulting session cannot reach external services, including the Claude API

#### Scenario: Explicit provider or unrestricted operation
- **WHEN** an operator explicitly chooses provider or unrestricted mode, or the validated managed launcher supplies that saved choice
- **THEN** the mode retains its existing policy, authority, prerequisite and separate maintenance requirements
- **AND** failed restricted preparation never falls back to unrestricted networking

#### Scenario: Qualification is not an ordinary session
- **WHEN** the standalone fixed qualification operation is invoked with no effective network mode
- **THEN** it qualifies the mode the launcher resolved from the profile with its protected fixtures
- **AND** neither that operation nor its internal probe admits an arbitrary application command or bypasses enforcement

### Requirement: Separate Claude authentication profiles
Provider mode SHALL require a named protected profile. `anthropic-api` SHALL allow only `api.anthropic.com:443` as its base destination. `anthropic-account` SHALL separately authorize only the measured account hosts needed inside the container. SSO, optional features, third-party clouds, and gateways SHALL require distinct explicit additions or profiles with dated inventories. A provider session SHALL forward `ANTHROPIC_API_KEY` by name only when the selected policy profile is `anthropic-api` and the variable is set.

#### Scenario: API and account inventories
- **WHEN** API authentication is selected
- **THEN** account login and unrelated development/feature hosts are denied
- **AND** the account profile allows exactly `api.anthropic.com` and `platform.claude.com` on 443, with SSO destinations only for its selected login method

#### Scenario: Removed account hosts are denied
- **WHEN** an account-profile session opens a CONNECT tunnel to `claude.ai` or `claude.com`
- **THEN** the proxy denies it with a policy reason and records only the sanitized host, port and reason
- **AND** no policy is extended automatically

#### Scenario: Operator needs a removed host
- **WHEN** an operator needs `claude.ai` or `claude.com` in a session
- **THEN** that requires a separately named profile in an operator policy
- **AND** the exact base `anthropic-account` profile cannot be extended in place

#### Scenario: Account credentials without an API key
- **WHEN** provider mode selects the account profile with usable existing account credentials and no ANTHROPIC_API_KEY
- **THEN** the wrapper does not require an API key to start that account session
- **AND** the same outer destination and IPC restrictions apply

#### Scenario: API key follows the selected profile
- **WHEN** `ANTHROPIC_API_KEY` is set on the host
- **THEN** a provider session with `anthropic-api` receives it by name
- **AND** a provider session with `anthropic-account` does not receive it, not even through `CLAUDE_CONTAINER_ENV_VARS`

### Requirement: Credential-free local enforcement qualification
Each restricted installation SHALL pass a bounded credential-free gate through its production launch and guard path before ordinary use. The qualified code identity SHALL include the shared launcher core and the agent launcher part, so a change to either invalidates the report. Required denial checks SHALL have controlled positive controls or demonstrate explicit enforcing syscall rejection. Missing fixtures, unrelated connectivity failure, skipped required checks and unavailable transport evidence SHALL fail qualification.

#### Scenario: Mandatory IP and IPC controls
- **WHEN** offline or provider mode is qualified
- **THEN** the gate verifies direct IPv4/IPv6 denial, no external DNS/UDP path, denial of existing and late external Unix endpoints and host-bind socket publication, and denial of alternate socket families and pair retargeting
- **AND** actual loopback and permitted connected-pair data exchange, descendant enforcement and ordinary caller-owned file persistence succeed
- **AND** controlled host endpoints are reachable by an unconfined positive control when the denial depends on a listening peer

#### Scenario: Provider boundary qualification
- **WHEN** provider mode is qualified
- **THEN** controlled TLS endpoints exercise matching CONNECT/SNI with certificate verification, mismatched-SNI zero-byte rejection, denied authority and fail-closed channel/proxy loss through the production guard, relay and proxy
- **AND** isolated fixture policy and certificates never modify production host inventories, private-address exclusions or CA defaults

#### Scenario: Probe or ordinary smoke is insufficient
- **WHEN** only an ABI query, socket creation result, version query or the previous smoke check succeeds
- **THEN** no successful qualification report is issued
- **AND** ordinary restricted startup remains blocked

#### Scenario: Host kernel without IPv6
- **WHEN** the engine host has no IPv6 support, observed as a missing `/proc/sys/net/ipv6` and `EAFNOSUPPORT` on `AF_INET6` socket creation
- **THEN** the gate uses an IPv4-only positive-control network and peer
- **AND** the IPv6 denial is evidenced by `EAFNOSUPPORT` on `AF_INET6` socket creation in both the unconfined control and the guarded probe
- **AND** every other required check, including the IPv4 positive controls and denials, runs unchanged

#### Scenario: Inconsistent IPv6 evidence
- **WHEN** the detected IPv6 state is neither clearly present nor clearly absent, or the fixture network, peer addresses, control or guarded probe contradict it
- **THEN** qualification fails without a report and without falling back to the other path

#### Scenario: IPv6 state is bound to the report
- **WHEN** a report was issued for one IPv6 state and the host later runs with the other state
- **THEN** the report is stale and restricted startup requires requalification

#### Scenario: Launcher core changed after qualification
- **WHEN** `launcher/core.sh` or `agent/launcher.sh` differs from the one recorded in the report
- **THEN** ordinary restricted startup requires requalification

### Requirement: Single protected agent profile
All agent-specific values used by the shared network sandbox, launcher and setup components SHALL come from one data-only agent profile and its provider policy file. The agent launcher part SHALL mirror them for the launcher and SHALL be checked against them. Examples:
- wrapper and variable names;
- images and labels;
- installation and state names;
- native configuration and credential variables;
- the in-container application path (`native.exec`) and executable temporary storage (`native.exec_tmp`);
- authentication assistance and policy profiles.

The profile SHALL NOT select who builds the runtime image. The profile SHALL be schema-validated, trusted-path checked and outside agent-writable mounts.

#### Scenario: Invalid or unprotected profile
- **WHEN** the profile is missing, malformed, has duplicate or unknown keys, fails field validation, or is reachable through a writable workspace or state mount or an escaped symlink
- **THEN** setup, qualification and restricted startup fail before the agent runs, identify the profile, and do not fall back to built-in defaults

#### Scenario: Profile not taken from the workspace
- **WHEN** the current workspace contains a file with the profile's name or layout
- **THEN** the wrapper uses only the profile in its protected installation or checkout and ignores the workspace copy

#### Scenario: Obsolete or mistyped launcher fields
- **WHEN** the profile declares `install.runtime_build`, a relative `native.exec` or a non-boolean `native.exec_tmp`
- **THEN** profile validation fails naming the field

### Requirement: Profile-bound restricted identity
The agent profile, its provider policy file, the shared launcher core and the agent launcher part SHALL be part of the protected code identity recorded in local qualification reports. Restricted preflight SHALL require each of them to be a protected file. Any change to one of them SHALL invalidate matching qualification evidence.

#### Scenario: Profile changed after qualification
- **WHEN** the installed profile or provider policy differs from the one recorded in the current qualification report
- **THEN** ordinary restricted launches are refused with setup or requalification guidance

#### Scenario: Writable launcher core
- **WHEN** `launcher/core.sh` or `agent/launcher.sh` in the installation is writable by others or reachable through a writable mount
- **THEN** restricted preflight fails naming the file

### Requirement: Residual exfiltration disclosure
Provider help, setup guidance, the README and the network contract SHALL state that destination and SNI binding cannot distinguish the operator's credentials from attacker-supplied ones. Each allowed host can therefore receive workspace data sent with a foreign API key or account. The documentation SHALL name the hosts of each base profile. It SHALL NOT present the disclosure or the host reduction as preventing this channel. The launcher core SHALL print the provider help from the profile and the default policy, so the help names the same hosts the policy allows.

#### Scenario: Operator reads the provider limits
- **WHEN** an operator reads the provider help, README or network contract
- **THEN** the foreign-credential channel is described for `api.anthropic.com` and every other allowed host of the selected profile
- **AND** the text states that only offline mode removes the channel

#### Scenario: Help follows the policy
- **WHEN** `--container-help` runs
- **THEN** the provider disclosure names `api.anthropic.com` for `anthropic-api` and `api.anthropic.com` and `platform.claude.com` for `anthropic-account`, as listed in `agent/policies/default.json`
