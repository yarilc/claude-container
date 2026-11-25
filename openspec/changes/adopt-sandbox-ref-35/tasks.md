# Tasks

## 1. Adopt `sandbox-ref-35`

- [ ] 1.1 Check that `sandbox-ref-35` exists in `sandbox-container`, then commit this change directory on `main`. From `sandbox-container`, run `python3 -I tools/propagate.py ../claude-container sandbox-ref-34 sandbox-ref-35` (dry run), then `--apply`.

  Verify:
  - the plan lists the files in proposal "What Changes", with 5 references in `docs/network-contract.md`;
  - the tool switched to `adopt-sandbox-ref-35`;
  - `claude-container.ps1` and `.gitattributes` need no copy, because the tag does not change them;
  - `python3 -m unittest tests.test_reference_copy tests.test_alignment` passes, including the shared list with `tests/guard_terminal_probe.py` and the agent-literal scan.

## 2. Claude's tests and documentation

- [ ] 2.1 Make the budget test of `tests/test_network_runtime.py` follow the shared budget rule (design decision 1).
  - **Helper:** `engine_budgets()` returns the delegated controllers and the process mechanism from `Host.CgroupControllers`, `Host.CgroupManager` and `Host.Kernel`, through `agent_budgets.delegated()` and `process_mechanism()`. `test_proxy_starts_beside_containers_holding_more_than_its_budget` uses it instead of its inline copy.
  - **Check:** in `test_agent_budgets_are_effective_and_lifetime_cleans_owned_proxy`, each offline and provider subtest receives both values:
    - a delegated controller's file holds the budget;
    - an undelegated one reads `max` or is absent;
    - on the `rlimit` mechanism, `/proc/self/limits` holds the process budget.

    The lifetime and proxy cleanup part is unchanged.
  - **Verify:** `bash tests/run-runtime.sh --network -k test_agent_budgets_are_effective_and_lifetime_cleans_owned_proxy` passes on WSL, checking all three limits, and on Rocky, where `cpu` is not delegated.
- [ ] 2.2 Run the terminal case of `test_guarded_arguments_stdin_status_and_tty_both_state_modes` in its own subtest (design decision 1).
  - **Where:** in each state mode, `subTest(terminal=True, isolated=bool(state))` calls `terminal_skip_reason(IMAGE)` from `tests/guard_terminal_probe.py` and skips with its reason. The piped case still runs in both state modes.
  - **Verify:**
    - on WSL, `bash tests/run-runtime.sh --network -k test_guarded_arguments_stdin_status_and_tty_both_state_modes` passes, with both terminal cases run;
    - on Rocky it passes, with both terminal cases skipped with the engine's error.
- [ ] 2.3 Fix the CA case and the tag cleanup of `tests/test_setup_runtime.py` (design decision 1).
  - **CA:** for the CA case, `answers()` copies `/etc/ssl/certs/ca-certificates.crt` to `self.base / 'ca-bundle.pem'` and answers the prompt with that path.
  - **Tags:** `clean_tags` adds, for each `releases/*/setup.json`, `REAL_PROFILE.image(kind, 'setup-' + release)` for `engine`, `toolchain` and `proxy`, beside the recorded `image`. `REAL_PROFILE` comes from `sandbox_profile`.
  - **Verify:** `bash tests/run-runtime.sh --setup-runtime` passes both tests on Rocky, where the bundle is at the RHEL path. On each host, compare `podman images --format '{{.Repository}}:{{.Tag}}'` before and after the mode:
    - no `:setup-` tag of the test's releases remains;
    - the operator's tags, such as `localhost/claude-code-engine:latest`, are still present.
- [ ] 2.4 Update the Testing Guidelines of `AGENTS.md` (design decision 4).
  - **Terminal check:** add the reference's paragraph. Where no terminal attaches to a `--read-only` container through the runner's client, the guarded terminal tests skip with the engine's error (`tests/guard_terminal_probe.py`), and validation records them as unavailable. The operator's interactive session on that host is the evidence for the `container-isolation` scenario "Terminal attaches on an engine that mounts /dev read-only".
  - **Home path:** the policy path rule names `/claude-home` instead of `/codex-home`.
  - **Verify:**
    - the paragraph names the skip, the unavailable record and the manual session;
    - `grep -n codex-home AGENTS.md` finds nothing;
    - `git diff --check` passes.
- [ ] 2.5 Run the repository checks, then commit the adoption on `adopt-sandbox-ref-35`, without merging.
  - **Checks:**
    - `python3 -m unittest discover -s tests`, with `SANDBOX_TEST_TMPDIR` on executable storage when `/tmp` is `noexec`;
    - `openspec validate adopt-sandbox-ref-35 --strict`;
    - `git diff --check`.
  - **Verify:** all pass, and the runtime suites skip without an engine.

## 3. Validation on the native hosts

- [ ] 3.1 Have the operator run the modes on WSL, from the branch (design decision 3).
  - **Before:** check that the runner's images exist, and build missing ones from the branch:
    - `localhost/claude-code:latest` and `localhost/claude-code-engine:latest`;
    - `localhost/claude-guard-toolchain:development`.
  - **Modes:**
    - the unit discovery;
    - `python3 -m unittest tests.test_reference_copy tests.test_alignment`;
    - `--network-feasibility`, `--guard`, `--network` and `--setup-runtime`.
  - **Expected:**
    - every mode passes;
    - the terminal tests of `--guard` and the terminal cases of `--network` run, and no test skips because of the probe.
- [ ] 3.2 Have the operator run the same modes on the Rocky 9 lab host.
  - **Before:** check the images of task 3.1 and the free space in `/home`.
  - **Discovery:** run the unit discovery in the runtime image, because host Python 3.9 is too old.
  - **Manual evidence:** the operator opens an offline `claude-container --container-shell` session with the host's client, recorded with `script`. In it, the terminal attaches on `/dev/pts`, and `/dev/shm` is read-only and empty.
  - **Expected:**
    - every mode passes, except `test_terminal_interrupt_is_delivered_once`, `test_terminal_interrupt_reaches_an_application_without_a_handler` and the two terminal cases of task 2.2. These skip with the probe's reason;
    - `--network-feasibility` and `--guard` pass without IPv6;
    - the budget test finds `cpu` undelegated.

  A failure in shared code pauses the change for a fix in `sandbox-container` under a new tag. A Claude-only failure is recorded with its log and proposed before it is fixed (design, Risks).

## 4. Record, merge and parity

- [ ] 4.1 Record the adoption and merge it.
  - **Record:** add the `sandbox-ref-35` adoption section to `docs/validation.md`, from the tool's template, with every result of tasks 2 and 3:
    - the terminal cases on Rocky as unavailable, with the engine's error;
    - the manual session as their evidence.
  - **Parity:**
    - set the real enforcement cell of Claude's row with the results of task 3;
    - copy the reference row from `sandbox-container`.
  - **Merge:** commit with the tool's message and the co-author trailer, then merge into `main`.
  - **Verify:** `python3 -m unittest tests.test_reference_copy tests.test_alignment` passes on `main`.
- [ ] 4.2 Copy Claude's parity row into `sandbox-container`, `codex-container`, `antigravity-container`, `opencode-container` and `pi-container`, one commit on `main` each.

  Verify: the reference and Claude rows are identical in the six repositories.

## Workflow follow-up

- The operator pushes `main` and the adoption branch in every touched repository.
- Archive this change with spec sync, which adds the scenario and the README item to `session-container-engine`.
- Codex, Antigravity, OpenCode and Pi adopt `sandbox-ref-35` in their own changes, with the same per-wrapper fixes. Their adoptions start from the tag each one holds.
