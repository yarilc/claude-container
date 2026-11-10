# Propagating the shared components

`network/`, `setup/` and the shared tests listed in `tests/test_alignment.py`
are written here and copied unchanged to Codex, OpenCode, Pi and Antigravity.
Each wrapper pins the copy with `tests/test_reference_copy.py`, which names a
reference tag `sandbox-ref-N`, its commit and the SHA-256 of every copied file.
The durable contract is
[reference-propagation](../openspec/specs/reference-propagation/spec.md).

A wrapper never edits a shared file. A defect found in a wrapper is fixed here,
published under a new tag and propagated again.

## 1. Decide whether a new tag is needed

A change needs a new tag when it modifies, adds or removes a file under
`network/` or `setup/`, or a test listed in `SHARED_TESTS`. Changes to the
wrapper, the agent profile, documentation, `tools/` or per-agent tests do not.

Before tagging, run this repository's suites that cover the change:

- `--setup` and `--qualification` for setup or qualification code;
- `--network` and `--guard` for proxy, relay, multiplex or guard code;
- the unit tests `tests/test_agent_profile.py` and `tests/test_alignment.py`.

Record the results in `docs/validation.md` under a section that names the new
tag. Merge into `main`, then create an annotated tag on the merge commit:

```bash
git tag -a sandbox-ref-N -m "Reference sandbox: <one-line summary>"
```

## 2. Adopt the tag in each wrapper

Run the tool from this checkout, once per wrapper, starting with a dry run:

```bash
python3 -I tools/propagate.py ../codex-container sandbox-ref-M sandbox-ref-N
```

The tool refuses to change a target when:

- its tree is not clean;
- its manifest names another tag or commit;
- a tag is missing here;
- a copied file differs from the old tag (a fork);
- the branch `adopt-sandbox-ref-N` already exists.

The dry run prints:

- the files to update, add and remove;
- files that changed but are outside the wrapper's adopted scope ("not adopted");
- the documents and the number of references to update;
- the runner modes to execute;
- a validation-record template and a commit message.

"Not adopted" files are expected while a wrapper has adopted only part of the
shared set, for example `setup/` before its guided-setup change. They are left
alone; the wrapper's own change that adopts them copies them later.

When the plan is right, apply it:

```bash
python3 -I tools/propagate.py ../codex-container sandbox-ref-M sandbox-ref-N --apply
```

This switches the wrapper to the new branch `adopt-sandbox-ref-N`, copies the
files byte for byte, deletes removed files, and rewrites `REFERENCE_TAG`,
`REFERENCE_COMMIT` and the manifest. It updates the tag and the full commit
only in current-state documents:

- `README.md`, `AGENTS.md`, `CONTRIBUTING.md` and `docs/setup.md`;
- `docs/network-contract.md`, including the parity cells `Reference (...)` and
  `Ported from ...`.

History stays as written: `docs/validation.md`, `CHANGELOG.md`, `todo.md` and
archived OpenSpec changes are never rewritten. The tool does not commit, merge,
tag, push or run suites.

## 3. Verify and record

Review `git diff` in the wrapper. Run every runner mode the tool listed, in the
wrapper checkout, plus any other mode the change can affect. Fill in the
validation-record template in the wrapper's `docs/validation.md` with the
results.

If a suite fails because of shared code, stop: fix it here (step 1) under a new
tag and adopt that tag instead. Discard the adoption branch first:

```bash
git -C ../codex-container switch main
git -C ../codex-container branch -D adopt-sandbox-ref-N
```

A failure caused by the wrapper itself, such as a literal message that a shared
test checks, is fixed in the wrapper on the same branch.

## 4. Commit, merge and update parity

Commit in each wrapper with the printed message and the co-author trailer, then
merge `adopt-sandbox-ref-N` into `main`. The tool already moved that wrapper's
own parity cells; check that the five rows of the parity table in
`docs/network-contract.md` are still identical across the repositories, and
update a row's status text when the adoption changed it. The user pushes the
branches and the tag.

## Keeping the tool in step

`tools/propagate.py` parses the wrappers' `tests/test_reference_copy.py` as text
(`REFERENCE_TAG`, `REFERENCE_COMMIT` and one `'path': 'sha256',` line per
`MANIFEST` entry). If that file's format changes, update the tool and
`tests/test_propagate.py` in the same change.
