# Design

## Context

See `proposal.md`. Facts the tool relies on, observed in the four wrappers on 2026-11-10:

**The manifest.** Each wrapper's `tests/test_reference_copy.py` declares:
- `REFERENCE_TAG = 'sandbox-ref-N'` and `REFERENCE_COMMIT = '<40 hex>'`;
- `CLOSED_DIRECTORIES = ('network', 'setup')` and `SKIPPED_PARTS = ('__pycache__', 'bin')`;
- a `MANIFEST` dict literal with one `'path': '<sha256>'` entry per line.

The file is agent-neutral and identical in structure in all four.

**The shared set.** This repository's `tests/test_alignment.py` declares `SHARED_DIRECTORIES` and `SHARED_TESTS` at each tag. The adopted scope can be smaller than the shared set: before `add-container-setup` a wrapper had only `setup/diagnostics.py`, and not `test_setup.py` or `test_alignment.py`.

**References in documents.** The tag and its commit appear in:
- the README;
- `AGENTS.md`;
- `CONTRIBUTING.md` (Pi only);
- `docs/setup.md`;
- `docs/network-contract.md`: the reference line with the commit, and the parity cells `Reference (\`sandbox-ref-N\`)` and `Ported from \`sandbox-ref-N\``.

They also appear in historical records that must keep the old values: `docs/validation.md`, `CHANGELOG.md`, `todo.md` (git-ignored) and `openspec/changes/archive/`.

**Runner modes.** These differ. Codex, OpenCode, Pi and Antigravity use a `case` with `--shared`, `--setup`, `--setup-runtime`, `--qualification`, `--network`, `--guard` and others. This repository uses an `if/elif` chain and has no `--shared`.

**What the Wave 3 scripts did.** The `adopt6.py` to `adopt9.py` scripts performed exactly these steps with hard-coded file lists, tags and commits.

## Goals / Non-Goals

**Goals:**
- One command that makes an adoption mechanical and verifiable, with a safe default (dry run).
- Never rewrite history records; never fork a shared file; never touch version control beyond creating the adoption branch.
- A written procedure that a maintainer can follow without the conversation history.

**Non-Goals:**
- Running the target's suites, committing, merging, tagging or pushing.
- Adopting several wrappers in one run. The procedure loops over them, so that each target's results stay separate.
- Changing the shared files or their alignment checks (no new tag).
- Closing the current documentation drift, the cross-repository parity check and the branch cleanup (excluded by the operator).

## Decisions

### A reference-only tool under `tools/`

`tools/propagate.py` lives outside `network/`, `setup/` and the shared tests, so it is never copied and needs no tag. It uses only the Python standard library and `git`. It runs on the host from this checkout, which is the source of truth for tags:

`python3 -I tools/propagate.py <target> <old-tag> <new-tag> [--apply]`

Rejected alternatives:
- **A shared script copied to every wrapper.** It would itself need propagating, and it would mix reference-side and target-side logic.
- **Wrapper-side `git fetch` from the reference.** The wrappers do not have this repository as a remote.

### Reading the manifest without importing it

The tool parses `tests/test_reference_copy.py` as text: the `REFERENCE_TAG` and `REFERENCE_COMMIT` assignments and the `MANIFEST` entries, one regex per line. It never imports or executes target code. A file whose structure does not match (missing assignment, duplicate key, malformed hash) is a precondition failure. Rewriting keeps every other line, so the agent-neutral test body is untouched.

### Scope rules

All lists come from git at the tags (`git ls-tree`, `git show`).

| Set | Definition |
| --- | --- |
| Shared at the new tag | Files under `SHARED_DIRECTORIES` (skipping `SKIPPED_PARTS`), plus `SHARED_TESTS`, both read from the new tag's `tests/test_alignment.py` |
| Adopted | The manifest keys |
| Added | Shared at the new tag, absent at the old tag, and either listed in a closed directory the target already adopts completely or a test whose directory the target adopts |
| Modified | Adopted, and with a different blob between the tags |
| Removed | Adopted, but absent at the new tag |

Files changed between the tags but outside the adopted scope are reported as "not adopted" and left alone. This covers the Pi egress-only case: `setup/common.py` was not adopted, so a change to it is not propagated.

"Adopts completely" for a closed directory means that every file of that directory at the old tag is in the manifest. This is how `test_reference_copy.py` already treats `CLOSED_DIRECTORIES`.

### Preconditions and atomicity

All checks run before any write:
- `git status --porcelain` is empty;
- the manifest tag and commit equal the old tag and `rev-parse <old>^{commit}`;
- both tags resolve here;
- every adopted file in the target equals its blob at the old tag;
- the branch `adopt-<new>` does not exist.

On `--apply`, the tool creates the branch with `git -C <target> switch -c adopt-<new>`, then writes the files and documents. Each file is written to a temporary file in the same directory and renamed into place. If a write fails midway, the tool reports the files already written; the branch and the clean starting point let the maintainer reset with git.

### Document rewriting

Only these files are processed:
- `README.md`, `AGENTS.md`, `CONTRIBUTING.md` and `docs/setup.md`: every exact occurrence of the old tag (as a whole word, so `sandbox-ref-1` does not match `sandbox-ref-10`) and of the old full commit becomes the new value;
- `docs/network-contract.md`: the same replacements.

`docs/validation.md`, `CHANGELOG.md`, `todo.md` and `openspec/` are never opened for writing. The dry run lists each file with its number of replacements.

### Checklist

The tool reads the target's `tests/run-runtime.sh` and collects the options it handles (tokens `--name` that appear as `case` labels or in `"${1:-}" == --name` tests). It then selects:

| Modes | When |
| --- | --- |
| `--shared` (or the reference-copy and alignment tests directly when absent) | Always |
| `--setup`, then `--setup-runtime` | Any file under `setup/` or `tests/test_setup.py` changed |
| `--qualification` | Any `network/qualif*`, `network/platform_check.py` or `tests/test_qualification.py` changed |
| `--guard`, `--network` | Any guard source, `network/proxy.py`, `relay.py`, `mux.py`, `session.py` or `control.py` changed |
| `--wrapper` | The profile schema (`network/agent_profile.py`) changed |

It prints:
- these modes;
- a `## Adoption of \`<new>\`: <date>` validation section template naming the tags, the commit and the copied files;
- a commit message: "Adopt <new> (...)" with the co-author trailer left for the maintainer.

### Procedure document

`docs/propagation.md` gives the end-to-end steps, including the parity-table update and the failure path. The README, `AGENTS.md` and the port checklist in `docs/network-contract.md` link to it.

## Risks / Trade-offs

- **[Text parsing of the manifest breaks on a reformatted file]** → The parser fails closed with the line it could not read. The manifest format has been stable across four repositories and six tags, and a test covers the format.
- **[A blind replace in documents could hit a historical mention inside a current document]** → Only five current-state files are processed, the dry run shows the counts, and the maintainer reviews the diff before committing, as the procedure requires.
- **[Mode detection misses a runner option]** → The checklist is advice; the procedure says to run every mode the change can affect, and the per-mode table is documented.
- **[The tool and the wrappers' `test_reference_copy.py` drift apart]** → The tests use a fixture copied from a real wrapper's file, and the procedure says to update the tool when that file's format changes.

## Migration Plan

No migration: new files only. The Wave 3 ad hoc scripts in the session scratchpad are superseded and were never committed.
