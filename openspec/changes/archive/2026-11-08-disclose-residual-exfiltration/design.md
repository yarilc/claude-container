# Design

## Context

- **Profile sources:** `agent/profile.json` declares each authentication
  method's hosts. `agent/policies/default.json` holds the dated policy.
- **Exact base profiles:** `policy.validate` requires every base profile to
  match the agent-profile hosts exactly. A custom profile with the same
  authentication method must include those hosts. Extensions therefore need a
  new profile name and cannot narrow a base profile.
- **Evidence binding:** qualification records bind the policy digest and the
  selected profile name. Any policy edit forces requalification, which setup
  already performs.
- **Logging:** the proxy records only sanitized denials (host, port, reason) and
  prints the last 20 on exit. A denial is the only measurement signal that does
  not decrypt traffic.
- **Static endpoint inventory of CLI 2.1.316.** The method was a `grep` of the
  installed binary for `https://` URLs on Anthropic hosts. No credentials were
  used and no requests were made.
  - `platform.claude.com/v1/oauth/token` handles code exchange and refresh.
  - `platform.claude.com/oauth/authorize` and `claude.com/cai/oauth/authorize`
    are the authorization pages, opened in the host browser.
  - `api.anthropic.com/api/oauth/...` handles the profile, roles and API key
    creation.
  - `claude.ai` and `claude.com` URLs are otherwise user-facing links (settings,
    upgrade, downloads, docs) or features disabled by `disable_optional_traffic`
    (remote code, connectors).

## Goals / Non-Goals

**Goals:**
- Make the foreign-credential channel visible at setup and in every provider
  document. Setup gets an acknowledgement, not only a printed line.
- Reduce the account profile to the measured hosts, keeping one exact,
  versioned base profile.

**Non-Goals:**
- Detecting or blocking foreign credentials. This is impossible without TLS
  decryption.
- A separate login-only profile, unless the authenticated checks show it is needed.
- Implementing credential-injecting interception.
- Changing the `anthropic-api` profile, which is already a single host.

## Decisions

### D1. Narrow the single account profile instead of adding a login profile

`anthropic-account` becomes `api.anthropic.com` plus `platform.claude.com`.

- **Why one profile is enough:** the static inventory shows that login in the
  container needs only the token endpoint and the API host; the browser steps
  happen on the host. One profile serves login, refresh and ordinary sessions.
- **Why not a login profile:** a second login-only profile would need its own
  qualification record, because records are bound to the profile name. It would
  also need a profile switch in `setup.authenticate` and a new agent-profile
  schema field.
- **Alternative rejected:** keeping four hosts and documenting only. This leaves
  `claude.ai` and `claude.com`, which accept uploads from any account, open
  without need.

### D2. Version the reduction

- **Policy:** the revision becomes `anthropic-2026-11-08-v2` and `source_date`
  becomes `2026-11-08`.
- **Sources:** keep the official network-config page and add the static
  inventory, described in `tested` as "CLI 2.1.316 static endpoint inventory;
  authentication pending operator checks".
- **Agent profile:** the hosts change to match.
- **Unchanged:** profile names, so `setup.json` keeps working. The digest still
  changes, which forces requalification.

### D3. Gate the reduction on operator checks, with a fixed fallback

The user authorized operator-run authenticated checks. They mirror the earlier
`ACCOUNT_*_OK` checks:
- a fresh isolated login through `--container-setup`;
- an ordinary request;
- a refresh forced by editing the stored expiry in an isolated test state;
- review of the exit denial records.

If any check fails because of a removed host:
- restore the four-host set under `anthropic-2026-11-08-v3`;
- record the denials;
- keep the disclosure work.

A login-only profile would then be a new change. The runtime never broadens a
profile automatically.

### D4. Acknowledgement inside network-mode selection

- **Helper:** a single `choose_network(default)` helper wraps
  `ask('Network mode', ...)` and is used both in the first question and in the
  delegation-conflict loop. Every path into provider mode is therefore covered.
- **Loop:** in provider mode it prints the notice and calls
  `yes('Acknowledge ...?', False)`. On `no` it loops back to the mode question.
- **Not saved:** the acknowledgement is not saved. The disclosure belongs to
  each review of the setup, and keeping it out of `setup.json` avoids a schema
  change.
- **Alternative rejected:** a stored flag. It adds migration and says nothing
  about the current profile's hosts.
- **Notice content:** generated from `PROFILE.auth[...]['hosts']` for every
  method, so the text cannot drift from the profile.

### D5. One shared disclosure wording

- **Help and setup:** the wrapper help and setup print a short form.
- **README and `docs/network-contract.md`:** both carry the full section.
  - It covers the channel, the hosts of each profile and the fact that only
    offline mode removes the channel.
  - The contract adds the interception evaluation:
    - **proxy role:** the proxy terminates TLS with a local CA and injects
      credentials;
    - **trade-offs:** credential custody moves to the proxy and the trusted
      proxy code grows;
    - **conflict:** it breaks the no-decryption contract and end-to-end
      certificate validation by the client;
    - **status:** not implemented; it needs an explicit operator decision and
      its own change.
- **`docs/setup.md`:** describes the acknowledgement prompt.

## Risks / Trade-offs

- **[The static inventory misses a runtime host]** The authenticated checks and
  their denial review are the gate. The fallback in D3 is fixed in advance.
- **[A future CLI version moves the token endpoint]** The policy records the
  tested version. A failure shows up as a policy denial, never as a silent
  broadening. A requalification with a new CLI is a new inventory review.
- **[The reduction is partial]** `api.anthropic.com` and `platform.claude.com`
  remain channels, which the disclosure states explicitly.
- **[Setup test prompt sequences change]** Update the `pty_run` answer lists and
  the patched `input` sequences in `tests/test_setup.py`.

## Migration Plan

1. Existing installations rerun `--container-setup`. The new policy digest
   invalidates the qualification records, and the next ordinary launch reports
   that requalification is required.
2. Operators who need `claude.ai` or `claude.com` define a custom profile in
   an operator policy under a new name.
3. Rollback: revert the policy and agent-profile commit and rerun setup.
