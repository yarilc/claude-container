# Validation record

## Archive disposition

On 2026-11-01, the user authorized synchronization, archive, and commit of
`align-container-sandboxing` with the previously reported runtime blockers.
The change is archived at
`openspec/changes/archive/2026-11-01-align-container-sandboxing/` with 20 of 26
tasks complete. Tasks 2.3, 3.4, 4.3, 5.1, 5.4, and 6.2 remain unchecked because
their real-engine acceptance could not be completed. Archiving does not turn
these checks into passes. All four delta specifications were synchronized and
all seven main specifications passed strict validation before archive.

The named-change validation command recorded below was run while the change
was active. After archive, use `openspec validate --specs --strict` to validate
the synchronized main specifications.

## Environment

Checks on 2026-11-01 ran as UID/GID 1000 in a container on Linux
6.6.87.2-microsoft-standard-WSL2, x86_64. The available client is Podman 4.3.1;
Python is 3.11.2 and the planning CLI is OpenSpec 1.16.0. These are the checking
environment's versions, not versions established for a rebuilt runtime image.

The workspace under `/mnt/d` reports mode 0777 even for a newly created private
directory. Synthetic wrapper tests therefore use native executable temporary
storage, not workspace directories, for their fake executable, HOME, sockets,
and credential state. Temporary test resources are removed after each test.

No host service socket was exposed at `/run/podman/podman.sock` or the default
caller runtime path, and no `CONTAINER_HOST` was configured. Local engine
operations fail before usable engine information is returned:

```text
Error: command required for rootless mode with multiple IDs: exec: "newuidmap": executable file not found in $PATH
```

The wrapper preserves the engine diagnostic and exits with an actionable
`cannot query Podman; check the local rootless service` error. Installing helpers
inside this read-only container is not a substitute for a working host engine.
No runtime security policy was relaxed to bypass the unavailable engine.

## Executed checks

| Check | Result | Evidence and limits |
| --- | --- | --- |
| Wrapper behavior suite | Passed | 33 tests using a fake Podman and synthetic state; no real engine or model requests |
| Bash syntax | Passed | `bash -n` on wrapper, image smoke script, and runtime runner |
| Whitespace | Passed | `git diff --check` and whitespace inspection of new files |
| OpenSpec validation | Passed | `openspec validate align-container-sandboxing --strict` |
| Default runtime discovery | Passed as opt-in gating only | Eight runtime checks are skipped unless explicitly enabled; this establishes no runtime behavior |
| Enabled runtime suite | Failed at engine precondition | Eight tests attempted; the missing `newuidmap` error prevents container startup |
| Disposable runtime runner | Failed at engine precondition | `bash tests/run-runtime.sh` exits 125 on its initial engine query, before creating a volume |
| Image inspection | Failed at engine precondition | `podman image exists localhost/claude-code:latest` cannot query the engine |
| Image build, CLI/tool smoke, actual image versions | Unavailable | No working launch engine; the Containerfile was not changed or rebuilt |
| Real boundary, identity, persistence, worktree, CA, and child-bind acceptance | Unavailable | Tests are delivered but have not passed against real containers |
| Real concurrent-session lifecycle and cleanup | Unavailable | Fake-engine lifecycle checks pass; real concurrent containers remain unverified |
| SELinux enforcing acceptance | Unavailable | No suitable engine/environment was exposed |
| Claude internal sandbox tool operation | Unavailable | No authenticated sandbox request was made; no compatibility conclusion is claimed |
| ShellCheck | Unavailable | Not installed; a Podman fallback cannot run without an engine |

## Coverage and remaining acceptance

| Contract | Synthetic evidence | Required real-engine evidence |
| --- | --- | --- |
| `container-launcher`: verified engine and supported contexts | Rootful/non-Linux/empty/malformed/query errors, local and explicit Unix contexts, named/TCP/SSH rejection | Actual engine info and wrapper-in-container launch |
| `container-launcher`: interface and help | Argv including spaces/empty strings, stdin, TTY, shell mode, side-effect-free help | Native Claude help/version in both state modes |
| `container-launcher`: image behavior | Physical script path, absence vs inspection failure, build failure status | Image build/inspect and installed versions |
| `container-launcher`: owned lifecycle | Collisions, stopped/all-name enumeration, decimal suffixes, retry limit, exit 125, INT/TERM/HUP, owned cleanup | Real simultaneous shell sessions and removal |
| `persistent-state` | Shared default/custom directory, isolated home, conflicts, private creation, ownership/access/mode errors, resolved aliases and escaping configuration symlinks | Persisted writes, profile separation, and filesystem ownership |
| `container-podman-access` | Exact opt-in values, selected-endpoint verification/precedence, remapped host paths, inaccessible/invalid sources and results, launch-mode combinations | Same-host Unix service, actual remapped socket, child absolute-path bind |
| `container-isolation` | Read-only/identity/tmpfs argv, no privilege or policy bypass, independent YOLO/socket combinations | External sentinel denial, `/usr` write denial, ephemeral `/tmp`, actual mount flags |
| Existing `workspace-mounts` | Physical cwd, parent selection, spaces, shell/build composition | Shared Git metadata, writable siblings, no inferred outside metadata mount |
| Existing `host-ca-trust` | Disabled/enabled variables, read-only single-file mount, mixed-case controls, missing bundle errors | Read-only mounted bundle and all four CA variables in both state modes |
| Existing `runtime-image` | Existing Containerfile retained | Actual Python/Bubblewrap/nano availability, editor variables, Claude/OpenSpec startup |

Automated tests never use the caller's real Claude configuration or API keys,
perform login, or submit paid model requests. Real runtime tests create synthetic
host HOME and state directories. The same-host runner binds only the test
project, its disposable native volume, and the explicitly delegated host socket;
the socket grants the runner broader host-user authority as documented in README.

The native sandbox check is separate from the automated suites. On an appropriate
authenticated session, run a harmless command through Claude's internal sandbox
and verify both its actual execution and expected output file. Record versions
and diagnostics if it fails. Neither `bwrap --version`, successful basic namespace
probes, a zero CLI status, nor Antigravity's validation record establishes Claude
sandbox compatibility. Retain standard seccomp, SELinux, capabilities, and tmpfs
`noexec` while checking; a policy change requires a separate decision.

## Reproduction

Run the synthetic suite on executable native Linux temporary storage:

```bash
python3 -m unittest discover -s tests -p test_wrapper.py -v
bash -n claude-container.sh tests/image-smoke.sh tests/run-runtime.sh
git diff --check
openspec validate align-container-sandboxing --strict
```

If `/tmp` is `noexec`, set `CLAUDE_TEST_TMPDIR` to a private native Linux directory
that allows execution. The suite deliberately rejects privacy checks performed
on filesystems that report all directories as 0777.

To finish runtime acceptance, expose a reachable same-host rootless Unix service
to this environment and set `CONTAINER_HOST=unix:///absolute/client/socket`, or
run from the host with working local rootless Podman. Keep original host absolute
workspace/build paths. Ensure the selected service's reported host socket path
is bindable by the launch engine. Then build and run:

```bash
./claude-container.sh --container-build --version
bash tests/run-runtime.sh
# Optional: use the image's Python for synthetic tests as well.
bash tests/run-runtime.sh --wrapper
```

The runner creates a disposable native Linux volume, supplies it through
`CLAUDE_TEST_STATE_ROOT` at its real host path, and removes that volume on exit.
It requires an already built image and active rootless API service. For direct
execution on a host with Python, use:

```bash
CLAUDE_RUNTIME_TESTS=1 python3 -m unittest discover -s tests -p test_runtime.py -v
```

Direct host execution uses native temporary state. With a Unix service client
inside a container, use the runner or explicitly provide `CLAUDE_TEST_STATE_ROOT`
backed by private native storage at the same absolute host path. `/tmp` inside
an arbitrary client container is not automatically a valid bind source on the
host. Record actual engine/kernel/architecture, image CLI/OpenSpec versions,
commands, and acceptance results here after a successful run. Do not mark the
outstanding OpenSpec runtime tasks complete based only on synthetic coverage.
