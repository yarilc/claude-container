# Proposal

## Why

Claude runs on `sandbox-ref-35`. `sandbox-ref-36` lets a session run systemd in
nested containers, for example to test Ansible roles that manage services. It
also gives the engine image a capability label, so Podman no longer logs
`Capabilities requested by user or image are not allowed by default` at each
engine start. Claude needs both now.

Earlier adoptions took hours, because they ran every runner mode on two hosts.
This one validates only the components that the tag touches, on one host. The
copied files are byte-identical to the tag, and the reference ran its full
suites on both hosts before tagging.

## What Changes

- **Adopt the tag.** `tools/propagate.py` adopts `sandbox-ref-36` from
  `sandbox-ref-35`. The 2026-11-26 dry run gave this plan:
  - update 14 shared files:
    - `launcher/core.sh`;
    - `launcher/engine/.containerignore`, `launcher/engine/Containerfile` and
      `launcher/engine/entrypoint.sh`;
    - `network/qualification_records.py` and `network/qualify.py`;
    - `setup/common.py`, `setup/engine.py` and `setup/toolchains.py`;
    - `tests/fake_podman.py`, `tests/test_engine.py`, `tests/test_launcher.py`,
      `tests/test_qualification.py` and `tests/test_toolchains.py`;
  - add `launcher/engine/start.sh` and `launcher/engine/cgroup.sh`;
  - rewrite 2 references in `docs/network-contract.md`, keeping 4 as history;
  - move the manifest to commit `ce2c9d2`.

  The thin Windows entry, `.gitattributes` and the guard, proxy and session
  code do not change.
- **Engine behavior, from the shared files:**
  - the engine starts through a startup step that delegates its own cgroup
    subtree, then runs as the `podman` user;
  - on an eligible engine, nested containers get their own cgroups, so
    systemd images boot. Explicit nested limits apply for each controller the
    engine has;
  - an ineligible engine is announced at launch, with the reason;
  - qualification checks the delegation and the unwritable limit files;
  - the engine image declares `SETUID,SETGID,SYS_CHROOT,CHOWN` in
    `io.containers.capabilities`.
- **One test fix in Claude.** The setup of `tests/test_network_runtime.py`
  names the engine's build inputs in a list of its own, without `start.sh` and
  `cgroup.sh`. It takes them from `setup/engine.py` (`engine.INPUTS`), as the
  reference does. Without this fix, the network suite cannot install the
  engine.
- **Claude's documentation:**
  - the README's engine items take the reference's text:
    - the budgets;
    - the hardening exceptions, with the startup step and the label;
    - the new "Systemd containers and nested limits" item;
  - the engine passages of `AGENTS.md` take the reference's wording.
- **Reduced validation perimeter.**
  - The operator runs, on WSL only:
    - the shared unit tests of the changed files;
    - `--setup`, `--setup-runtime`, `--qualification` and `--wrapper`;
    - the engine cases of the default and network runtime modes.
  - The rest is not rerun:
    - the full unit discovery;
    - `--guard`, the full `--network` and `--network-feasibility`;
    - the Rocky host and the Windows validation script.

  The record names what was not run and why.
- **Not ported:** the reference's systemd runtime cases, its systemd sample
  recipe and the recipe's pin check. They stay as the reference's evidence of
  `sandbox-ref-36` on both hosts.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `session-container-engine`, with the reference's two `sandbox-ref-36` deltas:
  - added:
    - measured eligibility for cgroup delegation;
    - the delegated engine cgroup subtree;
    - the engine startup step;
    - systemd in nested containers;
    - explicit limits for nested containers;
    - ineligible engines are announced;
    - the engine image declares its capabilities;
  - modified:
    - engine budgets: the budgets bound the engine and its nested containers
      together;
    - the fixed engine hardening exceptions: they now include the startup step;
    - engine containment qualification: it adds the delegation checks;
    - engine documentation: it adds systemd containers and the nested limits.

## Impact

- **Shared files:** as listed by the dry run. A defect in them pauses this
  change for a fix in `sandbox-container`.
- **Claude's files:**
  - `tests/test_network_runtime.py`;
  - `README.md` and `AGENTS.md`;
  - `docs/validation.md`;
  - the parity table in `docs/network-contract.md`, here and in the reference
    and the other four wrappers.
- **Operators:**
  - rerun `claude-container --container-setup` after updating. It rebuilds the
    engine image with the startup step and the label.
  - an engine image from before this tag logs the harmless capability error
    until then.
  - Claude's runtime, egress and guard images are unchanged.
- **Residual risk:** a regression of Claude outside the touched components
  would show only in the next full run. The record states this.
