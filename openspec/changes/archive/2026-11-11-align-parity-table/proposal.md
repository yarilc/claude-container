# Proposal

## Why

The five-wrapper parity table in `docs/network-contract.md` is meant to read the same in all five repositories, but on 2026-11-11 it does not:

- **The four siblings** carry identical copies. `tools/propagate.py` rewrote their `Reference (...)` and `Ported from ...` cells to `sandbox-ref-10`.
- **The reference** keeps a hand-written variant: a different Claude row (`Claude (this repository)`, other wording) and `Ported from sandbox-ref-9` for every sibling. The tool never touches the reference's own table.
- **The authentication column is stale everywhere.** It says `Pending operator ...` for Codex, Antigravity, OpenCode and Pi. Yet on 2026-11-11 the operator ran an authenticated session in every wrapper, with its setup-default profile. In each session the model used the harness tools and reported the sandbox's access limits, and every check passed.

The network-egress readiness scenario allows a profile to be called *verified* only when operator evidence covers its whole checklist: model requests, streaming, long-lived requests, WebSockets, the TUI, sign-in, token reuse and refresh, CA behavior and shell mode. These sessions cover a part of it, so the table must record what passed without claiming full verification.

## What Changes

- **One canonical table**, the siblings' layout with the Claude row `Reference (sandbox-ref-10)`, written identically into the five `docs/network-contract.md` files.
- **The authentication column records the 2026-11-11 operator sessions**, per wrapper and per profile, and keeps the remaining checks as pending:

  | Wrapper | Profile |
  | --- | --- |
  | Claude | `anthropic-account` |
  | Codex | `openai-account` |
  | Antigravity | `google-account` (policy `antigravity-2026-11-11-v2`) |
  | OpenCode | `anthropic-api` |
  | Pi | `anthropic-api` |

- **A short `docs/validation.md` section in each repository** records the date, the profile, what was checked (an authenticated model request in the TUI, with harness tool use and the sandbox limits reported) and what stays pending. For Codex this also records the operator's earlier confirmation.
- **`docs/propagation.md`** gains one step: when a new tag is created, update the reference's own parity cells, because the tool only rewrites the siblings.
- **Unchanged:** no shared file, so no new reference tag; no requirement change (`skip_specs: true`).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This change is documentation only. It brings the documents in line with the existing parity and readiness requirements without changing them.

## Impact

- `docs/network-contract.md` and `docs/validation.md` in claude, codex, antigravity, opencode and pi; `docs/propagation.md` in claude-container.
- One branch, commit and merge per repository. The operator pushes.
- No code, tests, profiles or policies change. Qualification is unaffected.
