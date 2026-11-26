# Design

## Context

Claude adopted `sandbox-ref-35` on 2026-11-25. `sandbox-ref-36` holds two
reference changes:
- `support-nested-systemd-containers`;
- `declare-engine-image-capabilities`.

The reference also archived `keep-parity-history-in-propagation` in that range.
It touches only `tools/`, so wrappers receive nothing from it.

The reference validated `ref-36` on 2026-11-26, with every mode passing:
- **Rocky 9 lab host:** Podman 5.8.0;
- **WSL:** Podman 4.9.3.

Its systemd and cgroup delegation runtime cases passed on both hosts, and so
did the qualification probe, which reads a bounding set of `00000000000400c1`
and finds no root process. Two reference findings shape this adoption:
- **Stale engine image:** with the new engine options, an engine image built
  before the tag starts its old entrypoint as root, and the check engine never
  answers. The runner's engine image must be rebuilt before the runtime modes.
- **Hard-coded input list:** the reference's `tests/test_network_runtime.py`
  listed the engine's build inputs in its own copy of the list. `ref-36`
  replaced it with `engine.INPUTS`. Claude's copy of the test
  (`tests/test_network_runtime.py:87-91`) still has the old list.

**What Claude adds to the shared code:**
- its profile: the image names `localhost/claude-code` and
  `localhost/claude-code-engine`, and the `CLAUDE_CONTAINER_` variables;
- `agent/launcher.sh`, on top of `launcher/core.sh`;
- its own runtime tests:
  - `SessionEngineTests` in `tests/test_runtime.py`, with three cases;
  - the engine case of `tests/test_network_runtime.py`, which shares the
    fixture setup of every network case.

Claude's main spec of `session-container-engine` equals the reference's at
`ref-35`, apart from `CLAUDE_CONTAINER_TOOLCHAINS`. Its README engine items and
AGENTS engine passages have the reference's `ref-35` text.

## Goals / Non-Goals

**Goals:**
- Claude runs on `sandbox-ref-36` today, with the evidence that its own code
  works with the changed components.
- The operator spends one run of one line on one host. Full logs go to files,
  in one archive.

**Non-Goals:**
- No porting of the reference's systemd runtime cases, of its systemd sample
  recipe, or of the recipe's pin check (see Decision 4).
- No validation on Rocky or on the Windows Podman machine.
- No widening of the 25-second window of
  `test_interrupted_and_failed_creation_recovers_both_roles`. That case is in
  the full `--network`, which this adoption does not run. It stays a
  follow-up.
- No change to `tools/propagate.py`. A faster, generic adoption flow is a
  separate reference change, after this one.

## Decisions

1. **Copy with the tool, and prove the copy by hash.** `tools/propagate.py`
   applies the plan of the dry run. `tests/test_reference_copy.py` proves that
   every shared file is byte-identical to `ce2c9d2`, so the reference's runs
   of `ref-36` hold for the shared code itself.

2. **One list of engine inputs.**
   - **What changes:** the fixture setup of `tests/test_network_runtime.py`
     copies `*engine.INPUTS` from `setup/engine.py`, as the reference does.
     That needs `setup/` on `sys.path` and `import engine`.
   - **Rejected:** adding `start.sh` and `cgroup.sh` to Claude's list. The
     next engine input would break the suite again.

3. **Test perimeter: the changed components, through Claude's code, on WSL.**

   | Changed in the tag | What runs in Claude | What it proves |
   | --- | --- | --- |
   | Every shared file | `python3 -m unittest tests.test_reference_copy tests.test_alignment` | Hash identity and alignment |
   | `tests/test_engine.py` and `tests/test_toolchains.py`, with `setup/engine.py` and `setup/toolchains.py` | `python3 -m unittest tests.test_engine tests.test_toolchains` | The engine recipe, the label and the options, with Claude's profile |
   | `setup/` | `--setup`, `--setup-runtime` | Setup builds Claude's engine image with the new inputs, and the image tags are unchanged around it |
   | `network/qualify.py` and `network/qualification_records.py` | `--qualification` | The `session-engine` probe on Claude's engine image |
   | `launcher/core.sh` | `--wrapper` | The shared launcher tests and Claude's launcher on the new core |
   | `launcher/engine/` | `-k SessionEngineTests` and `--network -k test_offline_session_engine_has_no_external_path` | The engine started by Claude's launcher, and the fix of Decision 2 |

   - **Why WSL is enough:** Claude adds no host-specific code to these
     components. The reference's `ref-36` runs measured how the shared engine
     behaves on each host.
   - **Expected skip:** `test_engine_process_rlimit_counts_per_container`
     skips with "the engine does not use the process rlimit fallback", as in
     the reference's WSL run.
   - **Why the rest is safe to skip:** no file under the guard, proxy, session,
     feasibility or Windows code changed. The record lists what was not run
     and why.
   - **Rejected: the matrix of `ref-35`,** every mode on both hosts, about 41
     minutes of suites on WSL and 13 on Rocky. It would only repeat the
     reference's evidence for byte-identical code.

4. **The systemd cases stay in the reference.**
   - **Where the evidence is:** the requirements "Systemd in nested
     containers" and "Explicit limits for nested containers" rest on the
     reference's runs. Both use the shared engine and a Rocky Linux sample
     image, without Claude's code.
   - **What porting would cost:** about 150 lines of test code, the sample
     recipe with its pin check, and the base image prepared in each engine.
   - **What Claude exercises:** its own engine path, through
     `SessionEngineTests` and the qualification probe.
   - **Later:** a reference change may make these engine cases shared, so
     wrappers receive them by copy.

5. **Prepare and check the images before the runtime modes.**
   - **Rebuild:** `localhost/claude-code-engine:latest` from the branch, with
     `podman build --pull=never --tag localhost/claude-code-engine:latest
     launcher/engine`. This avoids the stale-image failure.
   - **Label:** the image's `io.containers.capabilities` label reads
     `SETUID,SETGID,SYS_CHROOT,CHOWN`.
   - **Fail fast:** the run stops early when one of these is missing:
     - `localhost/claude-code:latest`;
     - `localhost/claude-guard-toolchain:development`, which the network
       fixture builds the guard with;
     - the pinned alpine sample image.

     Otherwise a case would skip, and a skip proves nothing.
   - **Free space:** the run records the free space before it starts.
   - **No other rebuild:** Claude's runtime image does not change, because its
     `Containerfile` is unchanged.

6. **One line for the operator.**
   - **Form:** a `;`-joined line that writes everything to `sbx-logs-c36/`:
     - the commit, `podman version`, `df -h` and the image list before and
       after;
     - the label check;
     - one full log per command, and a summary with each exit status.
   - **Archive:** the line packs it into `sbx-logs-c36-$(hostname).tar.gz` in
     the workspace root.
   - **No partial records:** every step runs even when an earlier one fails,
     so the image list after the run is always written.

7. **Real use on the operator's installation.**
   - **Steps:** after the suites, the operator reruns
     `claude-container --container-setup` from the branch on the installation
     they use. Then they open one session that has library images. In it,
     `podman info` reports rootless operation, and a library image runs.
   - **Cost:** the operator must rerun setup after updating anyway, so this
     check costs one session.

8. **Specs take the reference's deltas verbatim.** The change's
   `session-container-engine` delta joins the two `ref-36` deltas of the
   reference, which name no `SANDBOX_` variable.
   - **After archive:** Claude's main spec equals the reference's, apart from
     `CLAUDE_CONTAINER_TOOLCHAINS`.
   - **Known warning:** the strict check of the main spec warns that the
     description of "Fixed engine hardening exceptions" is over 500 characters,
     as it does in the reference.

## Risks / Trade-offs

- **A Claude regression outside the touched components goes unseen** →
  - the copy is proven byte-identical;
  - no shared file outside those components changed;
  - the record names the modes not run;
  - the next full run, or the next adoption that touches those areas, covers
    them.
- **Host-specific engine behavior on Rocky is not rerun for Claude** → the
  reference measured it at `ref-36` with the same bytes. Claude's launcher adds
  only names and its agent image.
- **A shared defect found here** → pause the change and fix it in
  `sandbox-container` under a new tag, as for earlier adoptions.
- **Installations keep the old engine image until setup reruns** → the README
  and the record say to rerun `--container-setup`. The old image only logs
  the harmless capability error. A restricted session also needs a
  qualification that holds the new engine checks.

## Migration Plan

- Merge into `main` after the record.
- Operators rerun `claude-container --container-setup`. It builds the engine
  image and requalifies the installation.
- **Rollback:** reinstall the `sandbox-ref-35` release with setup from the
  previous `main`.
