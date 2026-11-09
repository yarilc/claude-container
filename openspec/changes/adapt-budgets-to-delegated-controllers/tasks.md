# Tasks

## 1. Enforced-set model

- [x] 1.1 In `network/agent_budgets.py`, add a parser for the engine's
  controller list (`[a … z_ ]` form only) and an `enforced` computation for
  the agent (`memory`, `cpu`, `pids`) and the proxy (`memory`, `pids`).
  Extend `agent_hardening()` to take the controllers and record `enforced`.
  Verify with unit tests: all three, each one missing, an empty list,
  malformed input rejected, and deterministic ordering.

## 2. Wrapper

- [x] 2.1 In `claude-container.sh`:
  - read `{{.Host.CgroupControllers}}` from the verified engine, validating
    its format and failing closed otherwise;
  - build only the enforced budget flags, adding `--pids-limit=-1` when
    pids is unenforced;
  - print one notice per unenforced budget;
  - verify the created configuration: an enforced budget equals its value,
    and an unenforced one is absent.

  Verify with `tests/test_wrapper.py` cases where the fake engine reports
  each controller set (flags, notice, verification success, and failure
  when a listed controller is ignored), plus `bash -n claude-container.sh`.
- [x] 2.2 Update the wrapper help and `README.md` (budgets section) with the
  conditional enforcement, the notice and the residual exhaustion risk.
  Verify with `git diff --check`.

## 3. Proxy

- [x] 3.1 In `network/session.py`, derive the proxy's enforced set from the
  engine. Pass only enforced flags (`--pids-limit=-1` when pids is
  unenforced) and print the proxy notice. In `network/proxy_hardening.py`:
  - `probe()` reports `None` for a missing or `max` interface;
  - `verify()` takes the enforced set, and requires exact values for
    enforced budgets and absence for the others.

  Verify with `tests/test_session.py` and proxy-hardening unit tests for
  every subset, including an enforced budget that is not applied.

## 4. Smoke and qualification

- [x] 4.1 In `setup/smoke.py` `hardening()` and
  `network/qualification_probe.py` `effective_budgets()`, require exact
  values for enforced budgets and a missing or `max` interface for the
  others. Pass the enforced set through the existing smoke arguments and
  qualification budgets. Verify with unit tests that run the functions on
  synthetic cgroup directories for each subset.
- [x] 4.2 In `network/qualification_records.py`, compute the agent and
  proxy enforced sets from the bound `cgroupControllers` and store them in
  `hardening`. In `network/control.py`, accept and validate `enforced` in the
  fixed input. Verify with `tests/test_qualification.py`: a report goes
  stale when the enforced set changes, and invalid `enforced` values are
  rejected.
- [x] 4.3 In `setup/setup.py`, show the enforced set and the unenforced
  notice in the setup plan without a new question. Verify with a
  `tests/test_setup.py` case using a fake engine without `cpu`.

## 5. Policy documentation and regression

- [x] 5.1 Reword the budget rule in `AGENTS.md` and update `docs/setup.md`
  (hardening section) and `docs/network-contract.md`, if it mentions proxy
  budgets, to match the design. Verify with `git diff --check`.
- [x] 5.2 Run `test_wrapper.py`, `test_setup.py`, `test_qualification.py`,
  `test_session.py`, `test_network_policy.py`, `test_alignment.py` and
  `test_image_pins.py` against `main` with the same runner. Verify that
  there are no new failures, and record any environment-only ones.
- [x] 5.3 On this WSL host (all controllers delegated), run
  `bash tests/run-runtime.sh --qualification`. Verify that it passes with
  every budget enforced and that no notice is printed.
- [ ] 5.4 On the lab host, have the operator rerun `--container-setup`
  (provider, refresh). Verify that it reaches `Sandbox: ready` with the CPU
  notice. Then add a dated `docs/validation.md` entry, and close the open
  operator tasks of `https-image-package-sources` (4.2, 4.3) and
  `qualify-ipv6-disabled-kernels` (5.4).

## Workflow follow-up

- Propagate the shared files to the sibling wrappers.
- Sync the deltas and archive the three changes after review.
