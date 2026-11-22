# Proposal

## Why

Claude runs on `sandbox-ref-25`. Since then:

**`sandbox-ref-26`:**
- Without the `pids` controller, the process budget falls back to the process
  rlimit.
- Only the `systemd` cgroup manager delegates controllers.
- The shared launcher files pass ShellCheck.

**`sandbox-ref-27`:** Windows support on a Podman machine:
- the PowerShell entry, the shim and the bootstrap;
- the namespace helper and the installer;
- offline and provider networking in the machine;
- the guard as the confined init of restricted sessions;
- setup changes for the machine;
- API key variables forwarded from Windows.

**`sandbox-ref-28`:** change `fix-windows-agent-guidance` in
`sandbox-container`, planned with this one:
- setup started from Windows gives the login and API key steps for
  PowerShell;
- the reference tools validate agent wrappers on Windows.

Without them, Claude reports budgets as enforced on a `cgroupfs` engine, which
applies none, and Claude cannot run from Windows.

## What Changes

- **Adopt the tag.** `tools/propagate.py` adopts `sandbox-ref-28` from
  `sandbox-ref-25`, after the reference tags `sandbox-ref-28`. The
  2026-11-22 dry run to `sandbox-ref-27` gave this plan:
  - update 22 shared files;
  - add 8: `launcher/windows/` and the Windows tests;
  - rewrite 9 tag references in `docs/network-contract.md`;
  - move the manifest.

  `sandbox-ref-28` changes only `setup/setup.py` and `tests/test_setup.py`,
  which that plan already updates.
- **Files outside the copied directories,** handled as `docs/propagation.md`
  says:
  - `claude-container.ps1`, the thin Windows entry, byte for byte from
    `sandbox-container.ps1`;
  - `.gitattributes`, followed by an LF renormalization.
- **Claude's agent part** (`agent/launcher.sh`) gets the ShellCheck header that
  the reference agent part carries. Without it, the lint requirement that
  arrives with the tag reports 26 findings.
- **Claude's own tests** change only where the shared changes alter what they
  check (setup output, budget notices). A failure caused by shared code
  pauses the change for a fix in the reference.
- **Claude's documentation** (`README.md`, `docs/setup.md`, `AGENTS.md`):
  - a Windows section adapted to Claude:
    - provider is the default;
    - the account login runs in the machine;
    - `$env:ANTHROPIC_API_KEY`;
    - the installer;
    - host CA trust with `--import-native-ca`;
    - the Windows limits, including Bitdefender;
  - the process rlimit fallback and `cgroupfs` budgets;
  - the setup changes;
  - the README's "Podman Machine … unsupported" sentence now names the Windows
    entry.
- **Parity tables:**
  - Claude's row names `sandbox-ref-28`, with this adoption's results;
  - the reference row matches the reference repository;
  - Claude's row is copied into the reference and the other wrappers.
- **Validation on Windows** with Claude, by the operator:
  - setup in provider mode with the account login;
  - a Claude session;
  - `windows-validate -Checkout` on both PowerShell editions, including
    `-Install` and `-StopMachine`.

## Capabilities

### New Capabilities

- `windows-launcher`: the reference capability, copied as is. It runs Claude
  from PowerShell in a Podman machine's WSL distribution.
- `windows-installation`: the reference capability, copied as is. A per-user
  install of the Windows entry.

### Modified Capabilities

- `container-isolation`: budgets follow the controllers the engine delegates,
  and the process budget falls back to the process rlimit.
- `container-launcher`: notices, qualification identity and documentation of
  the rlimit fallback.
- `container-setup`:
  - the questionnaire and saved budgets with the fallback;
  - recovery tags;
  - setup without a launch service;
  - carriage-return checks;
  - setup started by the Windows entry, with the authentication steps for
    PowerShell;
  - the service endpoint proposed for restricted modes.
- `network-egress`: the proxy process budget falls back to the rlimit, and the
  guard runs restricted sessions as a confined init.
- `shared-launcher`: ShellCheck, the shared Windows shim and bootstrap, the
  thin PowerShell entry, LF line endings, PSScriptAnalyzer and the bootstrap
  tests.
- `workspace-mounts`: Windows system and profile folders are sensitive
  workspace roots.

## Impact

- **Code:** shared files only, plus `claude-container.ps1`, `.gitattributes`
  and the ShellCheck header of `agent/launcher.sh`.
- **Installations:** the installed core, setup and guard change, so every
  Claude installation reruns `--container-setup`.
- **Behavior on Linux:**
  - on a `cgroupfs` engine, the launch notices state that the memory and CPU
    budgets are not enforced and that the process budget uses the rlimit;
  - restricted sessions run under the guard as init, so Ctrl+C reaches the
    agent at once.
- **Repositories:** `claude-container`. In `sandbox-container` and the other
  wrappers, the parity row only.
- **Dependency:** `fix-windows-agent-guidance` in `sandbox-container`, and its
  tag `sandbox-ref-28`, come first.
