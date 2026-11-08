# Design

## Context

See `proposal.md` for motivation and scope. The wrapper dispatches help, standalone qualification and interactive setup before ordinary argument parsing. It currently derives `network_mode` with `${CLAUDE_CONTAINER_NETWORK:-offline}` and then checks provider settings, host commands, engine identity, state and protected assets.

`setup/launch.py` already validates its dispatcher and release preferences, and `setup/common.py:runtime_environment` supplies the saved network mode unless the environment explicitly contains that variable. Empty overrides are deliberately preserved. The qualification coordinator has a separate offline default and supplies an explicit mode to its fixed wrapper probes.

The main network spec currently promises an unset/empty offline default, and the setup spec promises unchanged direct invocation behavior. The deltas intentionally revise those contracts. The change does not infer whether setup has completed: a nonempty mode admits further validation, not application execution.

## Goals / Non-Goals

**Goals:**

- Make first-run refusal independent of Podman, host Python, configuration directories and restricted asset availability.
- Reuse the trusted managed launch path without adding a setup marker or changing the preference schema.
- Keep manual operation, maintenance consent and fixed qualification independently enforceable.

**Non-Goals:**

- Discovering preferences beside an arbitrary invocation or under the current workspace.
- Proving readiness through a boolean flag, testing credentials or starting setup automatically.
- Changing container, policy, guard, proxy, resource or authentication behavior after mode admission.

## Decisions

### Require a nonempty effective mode for ordinary launch

Insert the missing-mode refusal after the dedicated dispatch and ordinary option parsing, before boolean/runtime validation and host prerequisite checks. Use the existing status-1 error path. The English diagnostic identifies required setup and shows `bash <wrapper-path> --container-setup`, with the invoked script pathname quoted safely for paths containing spaces. It must work from another workspace and through a script symlink without requiring Python or Podman. Diagnostic formatting must not execute shell content.

Treat unset and empty identically. Keep existing invalid-mode validation for every other nonempty value, including whitespace. `--container-build`, shell/worktree options, maintenance consent, policy paths and existing state are not substitutes for mode selection.

Alternative: retain implicit offline whenever assets happen to exist. Rejected because it leaves first-run behavior dependent on local artifacts and cannot distinguish intended manual offline use from missing configuration. Explicit `offline` retains that workflow.

### Use existing managed preference injection

An ordinary valid managed launch already supplies a mode; retain its trust checks, override precedence and transparent exec behavior. An explicit empty override reaches the wrapper as empty and is refused. Do not add a public `SETUP_COMPLETE` escape hatch, scan `setup.json` from the working directory or validate managed readiness again in Bash.

Alternative: require a managed-only installation marker. Rejected because manually prepared restricted installations and explicit unrestricted maintenance are supported workflows. All existing qualification, endpoint and policy checks remain mandatory after admission.

### Preserve dedicated dispatch and qualification

Help retains first priority, including mixed options and invalid environment settings. Setup and standalone qualification retain their existing argument and terminal checks. The ordinary refusal must not block their dispatch. Qualification retains its coordinator's offline default and fixed controls; internal probes receive explicit modes and retain protected-input authentication. Do not introduce a new missing-mode exemption that executes arbitrary application arguments.

### Document the three relevant migration stages

Before `c777b73`, the wrapper had ordinary networking without the current runtime-mode interface. The enforced-network change introduced an unset/empty offline default. N20 replaces that ordinary implicit launch with setup guidance. Setup remains mandatory onboarding for new users; explicit environment-based operation remains the documented operator alternative.

Show managed launch as the ordinary path and explicit modes for manual operations. Show maintenance with both `CLAUDE_CONTAINER_NETWORK=unrestricted` and exact `CLAUDE_CONTAINER_MAINTENANCE=1`. Explain that offline cannot reach the API and that mode selection does not establish restricted readiness.

### Verify admission separately from enforcement

Extend wrapper synthetic tests to remove the fixture's default unrestricted mode explicitly; most existing tests deliberately set it. Assert status, stderr, empty stdout, absent fake-Podman log and absent state for missing/empty mode. Cover shell/build/worktree composition, maintenance-only invocation, missing prerequisites, unrelated environment settings, and paths with spaces/symlinks.

Retain managed adapter tests using an application stand-in to verify transparent forwarding, including empty overrides. Those tests do not establish real-wrapper admission: add integration coverage with the actual wrapper and fake engine for valid saved modes and an empty override. Retain unsafe preference/dispatcher rejection. Dedicated setup and qualification checks must demonstrate their own dispatch rather than bypassing normal enforcement.

## Risks / Trade-offs

- Existing direct scripts relying on implicit offline stop -> document explicit `offline` migration and test it against the existing restricted preflight.
- A generic first-run message can hide later environment errors -> apply it only to unset/empty ordinary modes; explicit invalid modes retain their diagnostics.
- Managed validation can reject unsafe preferences before wrapper admission -> preserve that trust boundary; empty-override acceptance tests use otherwise valid managed inputs.
- A copied wrapper changes qualification fingerprints -> deploy protected code through normal setup or manual qualification; never reuse stale reports.
- Current OpenSpec 1.16.0 strict validation flags long requirements in four main capabilities -> validate this change separately and record the unrelated baseline without rewriting main specs as part of N20.

## Migration Plan

1. Implement the wrapper guard, targeted regression coverage and documentation together. Keep N20 unchecked until accepted.
2. Run wrapper and setup synthetic suites, syntax and whitespace checks, and strict change validation. Exercise existing credential-free installed setup/qualification coverage when its native protected prerequisites and prepared images are available; record passed, failed or unavailable outcomes.
3. Rerun setup to install the changed protected wrapper and regenerate qualification before activation. Manual restricted installations must likewise requalify; no new image build inputs are introduced.
4. Preserve last-working-release activation and rollback. Rolling back restores that release's prior admission behavior and still requires its matching qualification; no credential migration is needed.
