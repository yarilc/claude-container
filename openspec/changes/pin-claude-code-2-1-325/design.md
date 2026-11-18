## Context

`docs/validation.md`, section "Updating pinned image inputs", gives the
procedure. For a new Claude Code version it requires a new provider endpoint
inventory and `tested.cli` updated in the same change. `tests/test_image_pins.py`
fails when `tested.cli` and `CLAUDE_CODE_VERSION` differ.

The 2026-11-08 inventory (policy revision `anthropic-2026-11-08-v2`) did two
things:
- scanned the installed binary for `https://` URLs on Anthropic hosts;
- sent a credential-free `GET /api/oauth/usage` through the proxy.

The Claude Code changelog for 2.1.317–2.1.325 contains two items that touch
this area:
- `claude -p` with no cached account data now waits for that data before its
  first request;
- several permission and sandbox changes in Claude Code's own Bash sandbox.
  The wrapper does not rely on that sandbox: the container is the boundary, and
  `CLAUDE_YOLO` maps to `--dangerously-skip-permissions`.

## Goals / Non-Goals

**Goals:**
- Pin 2.1.325 and OpenSpec 2.0.0 exactly. The build version checks, the pin
  tests and every credential-free suite must pass.
- Repeat the endpoint inventory with the same method and compare it with the
  2026-11-08 table, host by host.
- Confirm that every variable in `AGENT_PROVIDER_ENV` and the bypass flag still
  exist in 2.1.325:
  - `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`, `DISABLE_AUTOUPDATER`,
    `DISABLE_TELEMETRY` and the rest of `AGENT_PROVIDER_ENV`;
  - `--dangerously-skip-permissions`.

**Non-Goals:**
- Changing the base digest or any shared file.
- Real-key or real-account checks. The operator runs them after all
  repositories are done.
- Adopting Claude Code features that are new since 2.1.316.

## Decisions

- **Same inventory method as 2026-11-08.**
  - It runs offline and needs no credentials.
  - The result is a diff of the host table that a reviewer can check.
  - Alternative: a logging-proxy session with a real account. That is deferred
    to the operator.
- **Spec delta only when required hosts change.**
  - If the scan finds a new host that a profile needs, implementation stops.
  - The change then gets a `network-egress` delta and a new policy revision
    (`anthropic-2026-11-18-v1`), after the user agrees.
  - Hosts that are only optional, or that are used only by host-browser links,
    are recorded and do not change the profiles.
- **Native-flag check.**
  - `claude --help` in the image must still list
    `--dangerously-skip-permissions`.
  - A string scan of the binary must still find each name in
    `AGENT_PROVIDER_ENV`.
  - A missing name is a lost behavior. It pauses the work and goes to the user.

## Risks / Trade-offs

- [2.1.325 reaches a new host during start or `-p`] → The static scan, plus a
  `-p` launch in provider mode with a dummy key under the logging proxy, shows
  any new destination. The guard denies it, and the case is recorded.
- [A disabling variable is renamed or dropped] → The flag and variable check
  above finds it, and a lost behavior goes to the user.
- [Old tests change meaning] → The usual old-test gate applies. Each failing
  test is classified as a visible change, a lost behavior (ask the user) or
  agent-only behavior.
- [Rollback] → Revert the two pins and `tested.cli`, then rebuild.

## Migration Plan

1. The operator pushes `main`.
2. The operator reruns `--container-setup` on the three hosts.

Real-account checks follow later, in the deferred authenticated pass.
