# Proposal

## Why

The network sandbox (`network/`) and interactive setup (`setup/`) will be copied into the Codex, Antigravity, OpenCode and Pi wrappers. They currently embed about 200 Claude-specific identifiers: environment-variable names, image names, labels, install paths, in-container paths, protocol markers, provider hosts and authentication options. Copying them as-is would turn each port into a renamed fork, and cross-project comparison with `diff -r` would be buried in naming noise. All agent-specific values must therefore live in one protected profile before the first port, so that the shared directories can be copied byte-for-byte.

## What Changes

- Add one protected, schema-validated, data-only agent profile outside `network/` and `setup/`. It declares all agent-specific values:
  - display name;
  - wrapper command and environment-variable prefix;
  - agent-native variables (configuration directory, approval-bypass flag, credential variables);
  - host image, label and installation/state names;
  - authentication assistance options;
  - provider policy profiles.
- Move the provider policy file from `network/policies/` next to the profile, so that it belongs to the agent-specific variation point.
- Make `network/`, `setup/` and the guard build read every agent-specific value from the profile. No agent-specific literal may remain in those directories.
- Replace in-container paths, the guard binary name, compile-time guard constants and the multiplex protocol marker with agent-neutral names. Examples: `/run/claude-egress` → `/run/sandbox-egress`, `/opt/claude-egress` → `/opt/sandbox-egress`, `/tmp/claude-runtime` → `/tmp/sandbox-runtime`, `claude-egress-guard` → `sandbox-egress-guard`, `CLAUDE-EGRESS` → `SANDBOX-EGRESS`.
- Keep host-visible, per-agent identities unchanged and derive them from the profile. These include the `CLAUDE_CONTAINER_*` variables, `localhost/claude-*` images, `io.claude-container.*` labels, the managed launcher, the installation directory and state paths. Wrappers can then run side by side without sharing or cleaning up each other's resources.
- Include the profile and policy file in the protected installation, the code identity and the qualification report identity.
- Make network/setup tests derive names from the profile so they can be copied with the shared directories. Wrapper-specific tests stay per project.
- Add an alignment check that fails when `network/` or `setup/` contains agent-specific literals.
- User-facing behaviour is unchanged. Because the code identity changes, existing installations must rerun `--container-setup` (or explicitly requalify) and restart sessions, as for any protected code update.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `network-egress`: Add the agent profile as a protected, validated, identity-bound input, and require agent-neutral shared sandbox components.
- `container-setup`: Require the profile and its policy file to be part of the protected installation and of the qualification inputs.

## Impact

- Code: `network/*.py`, `network/guard.c`, `network/guard_*.h`, `network/build-guard.sh`, `network/Containerfile`, `setup/*.py`, `claude-container.sh` (in-container paths and guard name), `Containerfile`.
- New files: the agent profile and the relocated provider policy file.
- Tests: network, guard, qualification, TLS, mux and setup tests use the profile; new literal-scan alignment test.
- Docs: `network/README.md`, `docs/network-contract.md`, `docs/validation.md`, `README.md` (internal path references), `AGENTS.md` (shared vs agent-specific files).
- Operations: proxy and agent images and the guard binary are rebuilt. Existing installations require setup/requalification. No change to policies, hosts, modes, defaults or security boundaries.
- Downstream: unblocks porting byte-identical `network/` and `setup/` to the other four wrappers (Wave 3).
