# Proposal

## Why

Every agent container and provider proxy currently requires the rootless
cgroup v2 `cpu`, `memory` and `pids` controllers. On the Rocky 9 lab host,
systemd delegates only some controllers to the user. The qualification agent
then fails with
"crun: controller `cpu` is not available under
.../user@31600276.service/...". The operator cannot change the host, and the
sandbox must work with what the engine offers.

This deliberately relaxes the project rule "never remove a budget to make a
tool work". A budget is dropped only when the engine cannot enforce it, never
to make a tool work. The drop is visible and is bound into the qualification
evidence.

## What Changes

- **BREAKING (policy):** a budget whose cgroup controller is not delegated to
  the rootless engine is not requested and not enforced. This applies to the
  agent's memory, CPU and process budgets and to the provider proxy's memory
  and process budgets. Startup and setup continue automatically. There is no
  acknowledgement question.
- **Source of truth:** controller availability comes from the verified
  engine's `Host.CgroupControllers`, already part of the qualification
  identity. A budget is enforced when its controller is listed.
- **Notice:** every launch and the setup plan print one notice naming each
  unenforced budget and its missing controller, for example "agent CPU budget
  not enforced: cgroup controller cpu is not delegated to the rootless
  engine".
- **Verification stays strict for every enforced budget:** created-container
  inspection, setup smoke, qualification probe and proxy hardening require
  the exact value. For an unenforced budget, verification requires that the
  limit is absent (no configured value, and no cgroup interface file or
  `max`). An engine reporting a controller and then failing to apply it still
  fails closed.
- **Qualification identity:** the identity records the set of enforced agent
  and proxy budgets. A host whose delegation later changes needs
  requalification.
- **Unchanged:** selection and validation of budget values (setup questions,
  variables, defaults), capability dropping, no-new-privileges, the
  lifetime limit, tmpfs sizes and every network control.
- **Documentation:** `AGENTS.md`, the README, `docs/setup.md` and the
  container-isolation and network-egress specs describe the conditional
  enforcement and its risk. An agent without a memory or process budget can
  exhaust host RAM or processes for that user.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-isolation`: agent budgets are enforced when their controller is
  delegated, and verification distinguishes enforced from absent limits.
- `network-egress`: proxy budgets follow the same conditional enforcement.
- `container-launcher`: the qualification identity binds the enforced budget
  set, and launches print the unenforced-budget notice.
- `container-setup`: the setup plan and smoke follow the enforced set.

## Impact

- Wrapper (`claude-container.sh`): reads the controllers, builds the budget
  flags conditionally, verifies the created configuration and prints the
  notice.
- Shared code: `network/agent_budgets.py` (the enforced set),
  `network/qualification_records.py` (identity),
  `network/qualification_probe.py` (effective-budget check),
  `network/session.py` and `network/proxy_hardening.py` (proxy flags and
  verification), `setup/smoke.py`, `setup/setup.py` and `setup/common.py`.
- Tests: `test_wrapper.py` (fake engine controller lists),
  `test_setup.py`, `test_qualification.py`, `test_session.py` and the
  proxy-hardening tests.
- Existing qualification reports become stale. Restricted installations
  rerun setup.
- The shared files are propagated to the sibling wrappers.
