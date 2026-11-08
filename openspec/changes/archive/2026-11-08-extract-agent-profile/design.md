# Design

## Context

See proposal.md for motivation. The current coupling falls into four groups:

1. **Host-visible per-agent identities.** These are `CLAUDE_CONTAINER_*` variables, the `localhost/claude-code`, `localhost/claude-egress` and `localhost/claude-guard-toolchain` images, the `io.claude-container.{session,egress,qualification}` labels, the `~/.local/{bin,lib}/claude-container` managed launcher/installation and `~/.local/state/claude-egress`.
2. **In-container and protocol internals.** These are `/run/claude-egress`, `/opt/claude-egress`, `/tmp/claude-runtime`, the `claude-egress-guard` binary, the `CLAUDE-EGRESS` multiplex marker and the C header guards.
3. **Agent-native behaviour.**
   - Configuration: `CLAUDE_CONFIG_DIR`, `~/.claude` and its shared/private state layout with `.config/openspec`.
   - Approval bypass: `CLAUDE_YOLO`.
   - Credentials: `ANTHROPIC_API_KEY`.
   - Login assistance: `auth login --claudeai`.
   - Policy profile naming: the `anthropic-` + authentication-mode mapping.
4. **Provider policy.** `network/policies/default.json` and the Anthropic host references in `network/policy.py`.

Protected code identity (`network/qualification_records.py` `CODE`) and the guard source identity (`setup/common.py` `GUARD_INPUTS`) enumerate files by path. The wrapper `claude-container.sh` is agent-specific and is not copied between projects.

## Goals / Non-Goals

**Goals:**
- After this change, `network/` and `setup/` contain no agent-specific literal, so a port copies them unchanged.
- The compiled guard is agent-neutral, so all wrappers can share an identical guard source identity.
- Every agent-specific value has exactly one source: the profile directory.

**Non-Goals:**
- Extracting a shared package, submodule or cross-repository dependency (operator decision: copy, do not share).
- Making the per-agent wrapper script generic.
- Changing policies, hosts, modes, defaults, budgets, hardening or qualification checks.
- Porting to any other wrapper (Wave 3).
- Moving wrapper-only tests.

## Decisions

### D1 — Data-only JSON profile in a dedicated `agent/` directory

Layout: `agent/profile.json` and `agent/policies/default.json`. `network/policies/` is removed.

**Alternatives considered:**
- *Python module (`agent_profile.py`).* Rejected. It would make the variation point executable code loaded by protected setup/qualification paths, and it is harder to validate as an input.
- *Profile inside `network/`.* Rejected. `diff -r network/` would never be empty.
- *Environment file.* Rejected. It has no structure for authentication methods or state layout.

### D2 — Closed-schema loader in shared code

`network/agent_profile.py` loads the profile with the same rules as the existing policy loader:
- duplicate-key rejection (`unique_object`);
- a closed schema with a version field;
- type and pattern validation, for example the environment prefix must match `^[A-Z][A-Z0-9_]*$` and image names must match `^localhost/[a-z0-9][a-z0-9.-]*$`;
- trusted-path checks.

Unknown keys fail. All derived names are computed in one place:
- variables are built from the prefix plus a fixed suffix set (`_NETWORK`, `_NETWORK_PROFILE`, `_STATE_DIR`, `_MAINTENANCE`, …);
- label keys are built from the label namespace plus `session`, `egress` and `qualification`.

Proposed fields:

| Field | Claude value |
|---|---|
| `schema` | `1` |
| `display_name` | `Claude Code` |
| `wrapper` | `claude-container.sh` |
| `env_prefix` | `CLAUDE_CONTAINER` |
| `label_namespace` | `io.claude-container` |
| `images.agent` / `images.proxy` / `images.toolchain` | `localhost/claude-code` / `localhost/claude-egress` / `localhost/claude-guard-toolchain` |
| `install.name` | `claude-container` (launcher, lib and share paths) |
| `install.state_name` | `claude-egress` |
| `native.config_dir_env` | `CLAUDE_CONFIG_DIR` |
| `native.approval_bypass_env` | `CLAUDE_YOLO` |
| `state.home_dir` | `.claude` |
| `state.shared_dirs` | `[".claude", ".config/openspec"]` |
| `state.private_dirs` | `[".claude"]` |
| `auth.methods` | `account`: policy profile `anthropic-account`, login args `["auth","login","--claudeai"]`; `api`: policy profile `anthropic-api`, credential env `ANTHROPIC_API_KEY` |

Implementation may add, remove or rename fields as the code requires. The constraint is fixed: every value used by shared code comes from the profile.

**Where the rules apply.** The proxy image does not contain the profile. Trusted host-side code (control, qualification, setup) applies the agent-specific policy rules (required hosts per authentication method, exact base profiles) before it writes the read-only session snapshot. Inside the proxy, the snapshot is revalidated for structure only. Values that in-container helpers need (agent command, home, configuration variable) are passed by host code: through the validated qualification input and through the setup smoke arguments.

### D3 — Agent-neutral internals, per-agent host identities

Internals that never leave the container or the proxy pair become fixed neutral names in shared code:

| Current | Neutral |
|---|---|
| `/run/claude-egress` | `/run/sandbox-egress` |
| `/opt/claude-egress` | `/opt/sandbox-egress` |
| `/tmp/claude-runtime` | `/tmp/sandbox-runtime` |
| `claude-egress-guard` | `sandbox-egress-guard` |
| `CLAUDE-EGRESS` | `SANDBOX-EGRESS` |

The same applies to the C header guards.

Host-visible identities (images, labels, variables, installation and state paths) stay per-agent and come from the profile. Concurrent wrappers then never share images at different revisions, and their ownership labels never match another wrapper's resources, so cleanup cannot cross wrappers.

**Alternative considered:** fully neutral host names. Rejected. Two wrappers could adopt or clean up each other's containers, and an image update in one project would silently change another project's qualified image identity.

### D4 — Agent-native behaviour as declarative data, interpreted by shared code

Authentication assistance, credential forwarding and the shared/private state layout are expressed as profile data. Shared code interprets that data without branching on the agent. If a future agent needs behaviour the schema cannot express, the schema and shared code are extended in the reference project first and then propagated. No agent-specific code path is added to `network/` or `setup/`.

**Alternative considered:** per-agent hook functions. Rejected because it reintroduces divergence inside the copied directories.

### D5 — Profile is protected, installed and identity-bound

`agent/profile.json` and `agent/policies/default.json` are added to:
- installation copying;
- the trusted-path checks;
- the qualification `CODE` identity.

The guard source identity (`GUARD_INPUTS`) remains limited to neutral guard sources, so it is identical across wrappers. The wrapper resolves the profile from its protected installation, never from the workspace or current directory.

### D6 — Wrapper consistency is tested, not generated

`claude-container.sh` keeps its literal names, for readability and because it is a per-agent file. A test asserts that the variable names, images, labels and in-container paths it uses match the profile and the neutral constants.

**Alternative considered:** having the wrapper read the profile at runtime. Rejected because it adds a JSON parse to every launch's shell path for no portability gain.

### D7 — Literal-scan alignment check

A test fails if any file under `network/`, `setup/` or the shared network/setup tests matches the agent-specific identifiers declared in the profile, case-insensitively. Explicitly allow-listed documentation lines are the only exception. This is the guard rail that keeps future reference changes copyable.

### D8 — Shared tests use the profile

Network policy, guard, mux, TLS, platform, qualification, setup and profile tests (plus their fixtures and `tests/sandbox_profile.py`) derive names from the loaded profile, so they can be copied with the shared directories. Test-harness controls use neutral `SANDBOX_*` names (`SANDBOX_TEST_TMPDIR`, `SANDBOX_TEST_STATE_ROOT`, `SANDBOX_RUNTIME_TESTS`, `SANDBOX_GUARD_TESTS`, `SANDBOX_GUARD_TOOLCHAIN`, `SANDBOX_IDLE_TESTS`).

The following remain agent-specific because they drive the production wrapper end to end and contain agent checks such as optional-traffic variables or a real tool call:
- `test_wrapper.py`, `test_runtime.py`;
- `test_network_runtime.py` with `network_tls_fixture.py`;
- `test_setup_runtime.py`;
- `run-runtime.sh`, `image-smoke.sh`.

They receive only the renamed internal paths and markers.

## Risks / Trade-offs

- [Neutral marker and path renames silently break a component missed by the rename] → Rebuild both images and the guard, then run the full synthetic and real WSL guard/network/qualification/setup acceptance. Any mismatch fails closed at bootstrap.
- [Profile becomes a new tampering target] → Same protection, ownership and identity binding as the policy file; launches fail closed on any mismatch.
- [Schema too narrow for the other agents (for example Antigravity's keyring session or OpenCode's multi-provider profiles)] → Accepted. Extend the schema in claude first when a port needs it (D4). The first port validates the schema.
- [Existing installations stop launching until requalified] → Same as any protected code update. Documented in README migration notes and in setup's update message.
- [Literal scan produces false positives in prose] → Narrow allow-list kept in the test, reviewed with each change.

## Migration Plan

1. Implement on a branch and rebuild the guard, proxy and agent images.
2. Run the full acceptance and record results in `docs/validation.md`.
3. Users rerun `./claude-container.sh --container-setup`. The previous installation is retained by the existing rollback mechanism. Restricted launches with a stale qualification are refused with setup guidance.
4. Rollback: revert the commit and rerun setup. No persistent state format changes.
