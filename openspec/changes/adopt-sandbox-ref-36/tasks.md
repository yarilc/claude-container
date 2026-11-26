# Tasks

## 1. Adopt `sandbox-ref-36`

- [ ] 1.1 Copy the tag's shared files with `tools/propagate.py` (design decision 1).
  - **Before:** check that `sandbox-ref-36` exists in `sandbox-container`, then commit this change directory on `main`.
  - **Copy:** from `sandbox-container`, run `python3 -I tools/propagate.py ../claude-container sandbox-ref-35 sandbox-ref-36` (dry run), then `--apply`.
  - **Verify:**
    - the plan lists the files in proposal "What Changes", with `docs/network-contract.md (2, 4 kept)`;
    - the tool switched to `adopt-sandbox-ref-36`;
    - `claude-container.ps1` and `.gitattributes` need no copy;
    - `python3 -m unittest tests.test_reference_copy tests.test_alignment` passes.

## 2. Claude's test and documentation

- [ ] 2.1 Make the fixture setup of `tests/test_network_runtime.py` copy the engine's build inputs from `engine.INPUTS` (design decision 2).
  - **Change:** `setup/` goes on `sys.path` at import, beside `network/` and `tests/`. The copy loop keeps the other names and replaces the five `launcher/engine/` names with `*engine.INPUTS`.
  - **Verify:**
    - `grep -n "launcher/engine/" tests/test_network_runtime.py` finds no build input;
    - `python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" tests/test_network_runtime.py` passes;
    - the module imports in the unit discovery of task 2.4.
- [ ] 2.2 Update the README engine items with the reference's `sandbox-ref-36` text and Claude's names (spec "Engine documentation").
  - **Budgets:** the engine's first process sets the process limit. Explicit nested limits apply for each controller the engine has.
  - **Hardening exceptions:**
    - the startup step and the `CHOWN` capability kept only in the bounding set;
    - the four-capability label;
    - for an engine image from before the tag: the harmless error and the advice to rerun `claude-container --container-setup`.
  - **New item:** "Systemd containers and nested limits", with the three example commands, eligibility, the controllers per platform, the ineligible notice and the SELinux/AppArmor note.
  - **Verify:**
    - `diff` of the three items against `sandbox-container/README.md` shows only Claude's command names;
    - no `SANDBOX_CONTAINER_` name appears in the new text;
    - `git diff --check` passes.
- [ ] 2.3 Update the engine passages of `AGENTS.md` with the reference's wording.
  - **Process limit:** "the startup program for the engine" replaces "the entrypoint for the engine".
  - **Engine rule:** the startup step that delegates the engine's own cgroup subtree joins the hardening exceptions. Only that step runs as the root of the engine's user namespace, and the launcher's commands in the engine run as its `podman` user.
  - **Verify:** `grep -n "entrypoint for the engine" AGENTS.md` finds nothing, and the engine rule names `support-nested-systemd-containers`.
- [ ] 2.4 Run the repository checks here, then commit the adoption on `adopt-sandbox-ref-36`, without merging.
  - **Unit checks:** `python3 -m unittest tests.test_reference_copy tests.test_alignment tests.test_engine tests.test_toolchains tests.test_launcher tests.test_setup tests.test_qualification tests.test_network_runtime`, with `SANDBOX_TEST_TMPDIR` on executable storage when `/tmp` is `noexec`.
  - **Other checks:**
    - `openspec validate adopt-sandbox-ref-36 --strict`;
    - `git diff --check`.
  - **Verify:**
    - the only failures are `tests/test_engine.py` cases that need a rootless engine or root, which task 3.1 runs;
    - the runtime suites skip without an engine;
    - the validation and the diff check pass.

## 3. Validation on WSL, within the reduced perimeter

- [ ] 3.1 Give the operator one `;`-joined line for WSL, run from the branch, that writes every log to `sbx-logs-c36/` and packs `sbx-logs-c36-$(hostname).tar.gz` in the workspace root (design decisions 3, 5 and 6).
  - **Preparation:**
    - record the commit, `podman version`, `df -h` and the image list;
    - stop if `localhost/claude-code:latest`, `localhost/claude-guard-toolchain:development` or the pinned alpine sample image is missing;
    - rebuild `localhost/claude-code-engine:latest` with `podman build --pull=never --tag localhost/claude-code-engine:latest launcher/engine`;
    - record its `io.containers.capabilities` label.
  - **Commands, each to its own full log, with its exit status in the summary:**
    - `python3 -m unittest tests.test_reference_copy tests.test_alignment tests.test_engine tests.test_toolchains`;
    - `bash tests/run-runtime.sh --setup`;
    - `bash tests/run-runtime.sh --setup-runtime`;
    - `bash tests/run-runtime.sh --qualification`;
    - `bash tests/run-runtime.sh --wrapper`;
    - `bash tests/run-runtime.sh -k SessionEngineTests`;
    - `bash tests/run-runtime.sh --network -k test_offline_session_engine_has_no_external_path`.
  - **After the commands:** record the image list again. The line runs every step even when an earlier one fails.
  - **Expected:**
    - the label reads `SETUID,SETGID,SYS_CHROOT,CHOWN`;
    - every command passes;
    - `test_engine_process_rlimit_counts_per_container` skips with "the engine does not use the process rlimit fallback";
    - the image tags before and after `--setup-runtime` are the same, apart from the rebuilt engine image.

  Analyse the archive in a new empty directory. A failure in shared code pauses the change for a fix in `sandbox-container` under a new tag. A Claude-only failure is fixed on the branch, and the failing command alone is rerun.
- [ ] 3.2 Have the operator check real use on the installation they use (design decision 7).
  - **Steps:** rerun `claude-container --container-setup` from the branch, then open one session that has library images.
  - **Verify:**
    - setup completes and builds the engine image;
    - in the session, `CONTAINER_HOST=tcp://127.0.0.1:2375`;
    - `podman info` reports rootless operation;
    - `podman run --rm <a library image> true` succeeds.

## 4. Record, merge and parity

- [ ] 4.1 Record the adoption and merge it.
  - **Record:** add the `sandbox-ref-36` adoption section to `docs/validation.md`, from the tool's template, with:
    - every result of tasks 2.4, 3.1 and 3.2;
    - the label value;
    - the expected skip;
    - the modes not run and why: the full unit discovery, `--guard`, the full `--network`, `--network-feasibility`, Rocky and the Windows validation script, with the reference's `ref-36` runs as their evidence (design decision 3);
    - the systemd cases left to the reference (design decision 4).
  - **Parity:**
    - Claude's implementation cell gains "with systemd in nested containers";
    - its real enforcement cell gains the WSL `sandbox-ref-36` entry, naming the reduced perimeter;
    - copy the reference row from `sandbox-container`.
  - **Merge:** commit with the tool's message and the co-author trailer, then merge into `main`.
  - **Verify:** `python3 -m unittest tests.test_reference_copy tests.test_alignment` passes on `main`.
- [ ] 4.2 Copy Claude's parity row into `sandbox-container`, `codex-container`, `antigravity-container`, `opencode-container` and `pi-container`, one commit on `main` each.

  Verify: the reference and Claude rows are identical in the six repositories.

## Workflow follow-up

- The operator pushes `main` and the adoption branch in every touched repository.
- Archive this change with spec sync. Afterwards, Claude's `session-container-engine` main spec equals the reference's, apart from `CLAUDE_CONTAINER_TOOLCHAINS`.
- A reference change makes adoptions faster, before Codex, Antigravity, OpenCode and Pi adopt `sandbox-ref-36` from `sandbox-ref-28`:
  - a more precise `checklist()`;
  - a dry-run warning for wrapper files that name changed shared files;
  - one runner command per host;
  - the one-host rule in `docs/propagation.md`.
- Widen the window of `test_interrupted_and_failed_creation_recovers_both_roles` in the five wrappers.
