## MODIFIED Requirements

### Requirement: Separate Claude authentication profiles
Provider mode SHALL require a named protected profile. `anthropic-api` SHALL allow only `api.anthropic.com:443` as its base destination; `anthropic-account` SHALL separately authorize only the measured account hosts needed inside the container. SSO, optional features, third-party clouds, and gateways SHALL require distinct explicit additions or profiles with dated inventories.

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

## ADDED Requirements

### Requirement: Residual exfiltration disclosure
Provider help, setup guidance, README and the network contract SHALL state that destination and SNI binding cannot distinguish the operator's credentials from attacker-supplied ones. Each allowed host can therefore receive workspace data sent with a foreign API key or account. The documentation SHALL name the hosts of each base profile and SHALL NOT present the disclosure or the host reduction as preventing this channel.

#### Scenario: Operator reads the provider limits
- **WHEN** an operator reads the provider help, README or network contract
- **THEN** the foreign-credential channel is described for `api.anthropic.com` and every other allowed host of the selected profile
- **AND** the text states that only offline mode removes the channel

### Requirement: Credential-injecting interception remains unimplemented
The network contract SHALL describe credential-injecting TLS interception as a separately evaluated option only. In that option the proxy holds the credentials and the agent never sees them. The contract SHALL state that it conflicts with the no-decryption guarantee, and that it requires an explicit operator decision and its own change before implementation. The proxy SHALL NOT decrypt, terminate or re-sign provider TLS.

#### Scenario: Interception is reviewed
- **WHEN** an operator reads the network contract
- **THEN** the option, its trade-offs (TLS termination, a local CA, credential custody and a larger trusted proxy) and its unimplemented status are stated
- **AND** provider tunnels still forward TLS end-to-end without decryption

### Requirement: Authenticated account-profile reduction evidence
An account-profile host reduction SHALL count as accepted only after operator-run checks pass through the restricted wrapper. These are a fresh isolated login, an ordinary request and a refresh after expiry, with the narrowed profile and no other change. The sanitized denial records SHALL be reviewed. Automated tests SHALL NOT use real credentials.

#### Scenario: Narrowed profile passes
- **WHEN** login, an ordinary request and a refresh succeed under the narrowed profile with no denial of an Anthropic host
- **THEN** the validation record stores the CLI version, policy revision, results and the absence of denials, without credentials, URLs or bodies

#### Scenario: Narrowed profile fails
- **WHEN** any check fails or a denial names a removed host
- **THEN** the measured denials are recorded
- **AND** the account profile is restored to its previous host set under a new revision instead of being broadened automatically at runtime
