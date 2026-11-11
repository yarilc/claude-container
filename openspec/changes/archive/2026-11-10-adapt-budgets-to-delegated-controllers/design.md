# Design

## Context

See proposal.md (Why). Budgets are applied and checked in five places today,
all assuming the `cpu`, `memory` and `pids` controllers:

- `claude-container.sh`:
  - builds `--memory/--cpus/--pids-limit` (around line 475);
  - after create, requires `HostConfig.Memory NanoCpus PidsLimit` to equal
    the selected values (around lines 790-795).
- `network/session.py` creates the proxy with `--pids-limit=128
  --memory=256m`. `network/proxy_hardening.py` `probe()` reads `pids.max`
  and `memory.max` as integers, and `verify()` requires both exactly.
- `setup/smoke.py` `hardening()` reads `memory.max`, `pids.max` and
  `cpu.max` and requires exact values.
- `network/qualification_probe.py` `effective_budgets()` does the same for
  the qualification agent.
- `network/agent_budgets.py` `agent_hardening()` produces the
  `hardening.agent` identity record. `network/control.py` validates that
  record's exact keys in the fixed qualification input.

`qualification_records.fingerprint()` already binds the server's
`cgroupControllers` (from the raw libpod info of the verified endpoint) into
`engine_configuration`. On the maintainer's host,
`podman info --format '{{.Host.CgroupControllers}}'` prints
`[cpu memory pids]`.

## Goals / Non-Goals

**Goals:**
- Start and qualify on engines that lack any of the three controllers,
  without host changes or prompts.
- Keep every enforced budget exactly verified, and make every unenforced
  budget provably absent rather than silently half-applied.
- Make the enforced set visible (a notice) and bind it into the evidence
  (the identity).

**Non-Goals:**
- Substitutes for missing controllers, such as `nice`, `ulimit` or
  application-level limits. The user chose automatic continuation.
- Changing budget values, defaults, validation or setup questions.
- The lifetime limit (`--timeout`), which needs no cgroup controller.

## Decisions

### One source of truth: the verified engine's controller list

The wrapper reads `podman info --format '{{.Host.CgroupControllers}}'` from
the already-verified launch engine. It accepts only `^\[[a-z_ ]*\]$` and fails
closed otherwise. A budget is enforced when its controller is listed:
`memory` for memory, `cpu` for CPU, `pids` for processes. This avoids jq, so
unrestricted hosts without extra tools keep working.

`network/session.py` derives the proxy set from the same engine query, so
no new argument crosses the shared boundary. `qualification_records` uses
the `cgroupControllers` it already binds.

- Alternative: probing by trial creation. Rejected. It is slow and creates
  resources, and the engine already reports the list authoritatively.

### Unenforced means requested-absent, not best effort

For an unenforced budget the wrapper passes no flag. For pids it passes
`--pids-limit=-1`, so a `containers.conf` default cannot reintroduce a
request for the missing controller.

Verification is three-valued per budget:
- an enforced budget must equal its selected value (unchanged);
- an unenforced budget must have no configured value (`Memory 0`,
  `NanoCpus 0`, `PidsLimit <= 0`);
- inside the container, the interface file must be missing or read `max`.

An engine that lists a controller and then fails to apply it still fails
closed.

### Identity and fixed input

`agent_budgets.agent_hardening(env, profile, controllers)` adds
`enforced: [...]`, a sorted subset of `memory`, `cpu` and `pids`. The proxy
part of `hardening` gains `enforced` (a subset of `memory` and `pids`).
`control.py` accepts `enforced` in the fixed qualification input, and the
probe checks it. A delegation change therefore changes the identity, so the
report goes stale.

### Notice, no prompt

Each launch writes `<wrapper>: agent <budget> budget not enforced: cgroup
controller <name> is not delegated to the rootless engine` to stderr, once
per unenforced budget. It does the same for the proxy (`proxy memory` and
`proxy process`) in provider mode. The setup plan lists the enforced set and
the smoke prints the same notice. Nothing waits for input.

### Project rule rewording

`AGENTS.md` changes "never add a capability or remove a budget to make a tool
work" to: never add a capability, and never drop a budget the engine can
enforce. Budgets whose controller the rootless engine does not delegate are
omitted, announced and bound into qualification evidence. The README and
`docs/setup.md` state the residual risk: without memory or pids limits an
agent can exhaust host memory or processes for that user.

## Risks / Trade-offs

- [Host exhaustion when `memory` or `pids` is missing] The user accepted it
  explicitly. Mitigation: the per-launch notice, documentation, and a
  qualification identity that makes the state auditable.
- [The controller list overstates availability] The engine lists a
  controller that the scope cannot use. Creation or effective verification
  then fails closed, as today.
- [The controller list understates availability] The budget is dropped
  although it could be enforced. This is accepted as engine-reported truth,
  and the notice makes it visible.
- [Shared-file drift] Sibling wrappers keep strict behavior until
  propagation. That is safe.

## Migration Plan

1. Land the change. Restricted installations rerun setup, because the
   identity changes. Unrestricted installations need nothing.
2. Rollback: revert. Hosts lacking a controller then fail as before.
