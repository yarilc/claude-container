# Design

## Context

See proposal.md (Why).

`tools/propagate.py` rewrites the `Reference (...)` and `Ported from ...` cells only in sibling `docs/network-contract.md` files. Its contract (`reference-propagation`) lists these cells among the current-state references. Because the reference's own table has a different shape, nothing keeps the five copies equal. The `Real enforcement` and `Implementation` cells stay as they are; only the authentication column records new evidence.

## Goals / Non-Goals

**Goals:**

- Byte-identical parity tables in the five repositories.
- An authentication column that states exactly what operators ran, without claiming profile verification.

**Non-Goals:**

- An automated cross-repository parity check. That is a separate follow-up; a test that reads sibling checkouts would need a design of its own.
- Rewording the rest of the reference's checklist section.

## Decisions

1. **Canonical text is the siblings' table, with the authentication cells changed.**
   - The siblings already agree with each other and with what the tool writes.
   - The rejected alternative is to keep the reference's `Claude (this repository)` row: then the tool would keep producing a variant.
2. **Cell wording.**
   - The pattern is: `Operator session with tool use passed (2026-11-11, <profile>)`, then `; <remaining operator checks> pending`, then the existing synthetic-evidence clause.
   - Claude keeps its earlier `Account login, reuse and refresh passed` and its `real-key API unavailable`, and adds the session.
   - `verified` is not used. The readiness scenario reserves it for the full checklist.
3. **Copy, then compare.** The table is written once and copied into the other four files. A check extracts the table, from the `| Wrapper |` header to the first blank line, from all five files and compares their SHA-256 values. Its output is recorded in the reference's validation section.
4. **Propagation step.** `docs/propagation.md` step 1 (tagging) gains a sentence: update the reference's own `Reference (...)` and `Ported from ...` cells to the new tag in the same merge. This keeps the reference equal to what `--apply` writes in the siblings.

## Risks / Trade-offs

- [The table drifts again at the next tag] → The propagation step above, plus the comparison command in the validation record, which can be reused. An automated check remains a follow-up.
- [Readers take "passed" as full verification] → Each cell keeps the pending checks, and each validation section states that full profile verification is not claimed.
