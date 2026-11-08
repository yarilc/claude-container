# Proposal

## Why

Provider mode binds each tunnel to an approved hostname, but it cannot tell the
operator's credentials from attacker-supplied ones. A prompt-injected agent can
send workspace data to an allowed service with a foreign API key or account.
Examples are `api.anthropic.com` or the broader account hosts `claude.ai` and
`claude.com`. Operators are not told this at setup. The account profile also
allows hosts that the CLI does not appear to need inside the container (N21).

## What Changes

- **Setup disclosure:** selecting provider mode in `--container-setup` shows a
  residual-exfiltration notice. The operator must acknowledge it. Declining
  returns to the network-mode choice; setup never silently selects another mode.
- **Documentation:** README, the wrapper help, `docs/network-contract.md` and
  `docs/setup.md` gain the same disclosure. It states that destination binding
  cannot distinguish credentials, names each allowed host as a possible channel,
  and states that this disclosure does not mitigate the risk.
- **Narrower account profile:** **BREAKING** for installed policies.
  `anthropic-account` shrinks from four hosts to `api.anthropic.com` and
  `platform.claude.com`. The basis is the static endpoint inventory of CLI
  2.1.316: OAuth code exchange and refresh use `platform.claude.com/v1/oauth/token`,
  account calls use `api.anthropic.com`, and the authorization pages open in the
  host browser. The base profile stays exact and gets a new policy revision
  `anthropic-2026-11-08-v2`. Existing installations must rerun setup.
- **Authenticated acceptance gate:** before the reduction counts as complete,
  the operator runs login, an ordinary request and a forced refresh under the
  narrowed profile and reviews the sanitized denial records. Any failure
  restores the four-host profile with its own revision and records the measured
  denials. There is no automatic broadening.
- **Interception evaluation:** credential-injecting TLS interception is
  documented as a separately evaluated option only. In that design the proxy
  holds the credentials and the agent never sees them. It conflicts with the
  no-decryption contract and is not implemented.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `network-egress`: changes to these requirements:
  - "Separate Claude authentication profiles": the narrowed exact account inventory.
  - "Accurate provider identity documentation": the residual-exfiltration disclosure and the interception evaluation.
  - New requirement for the authenticated profile-reduction evidence.
- `container-setup`: the provider-mode residual-exfiltration acknowledgement in
  the questionnaire.

## Impact

- **Profile data:**
  - `agent/profile.json`: account hosts.
  - `agent/policies/default.json`: revision, sources, tested fields and account destinations.
- **Setup and wrapper:**
  - `setup/setup.py`: notice and acknowledgement loop.
  - `claude-container.sh`: help text.
- **Docs:** README, `docs/network-contract.md`, `docs/setup.md`, `docs/validation.md`, AGENTS.md if it lists hosts.
- **Tests:**
  - `tests/test_setup.py`: prompt sequences.
  - `tests/test_network_runtime.py` and `tests/network_tls_fixture.py`: controlled account inventory.
  - Policy tests for the exact base profile.
- **Installations:** the policy digest changes, so existing installations must
  rerun setup and requalify. Operators who need the removed hosts can define a
  separately named custom profile in an operator policy.
