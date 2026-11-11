# Tasks

## 1. Canonical table

- [x] 1.1 In claude-container `docs/network-contract.md`, replace the parity table with the canonical table (design decisions 1 and 2):
  - the Claude row `Reference (sandbox-ref-10)`, as in the siblings;
  - `Ported from sandbox-ref-10` cells;
  - the authentication cells recording the 2026-11-11 operator sessions: Claude `anthropic-account`, Codex `openai-account`, Antigravity `google-account` with policy `antigravity-2026-11-11-v2`, OpenCode `anthropic-api`, Pi `anthropic-api`;
  - the remaining checks kept as pending.

  Verify with markdownlint (no new findings except MD013).
- [x] 1.2 On one branch per sibling (`align-parity-table`), copy that table byte for byte into `docs/network-contract.md` of codex, antigravity, opencode and pi. Verify that the table extracted from all five files (from the `| Wrapper |` header to the first blank line) has one SHA-256 value, and that `git diff --check` is clean in each repository.

## 2. Validation records and propagation procedure

- [x] 2.1 In each repository's `docs/validation.md`, add a section `Operator authenticated session: 2026-11-11` with:
  - the wrapper and profile;
  - the check: an authenticated model request in the TUI, with harness tool use and the sandbox access limits reported, which passed;
  - the operator checks that remain pending;
  - a statement that full profile verification is not claimed.

  Codex's section also records the operator's earlier confirmation of the same day. The reference's section also records the five-file SHA-256 comparison. Verify with markdownlint.
- [x] 2.2 In claude-container `docs/propagation.md`, step 1 (tagging): update the reference's own `Reference (...)` and `Ported from ...` cells to the new tag in the same merge. Verify with markdownlint and `git diff --check`.

## 3. Final verification

- [x] 3.1 Run the five-file SHA-256 comparison again; it must still report one value. Check that each repository contains only documentation changes: `git diff --stat` lists only `docs/` files. Then run `openspec validate align-parity-table --strict`.

## Workflow follow-up

- `/opsx:archive` (no spec sync: `skip_specs`), then commit and merge in the five repositories; the operator pushes.
- Possible later change: an automated cross-repository parity check.
