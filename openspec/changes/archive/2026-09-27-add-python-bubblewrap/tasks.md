# Tasks

## 1. Add the Runtime Packages

- [x] 1.1 Add `python3` and `bubblewrap` to the existing Debian package installation in `Containerfile`; verify `./claude-container.sh --container-build` completes successfully.
- [x] 1.2 Update the README's included-tools list to name Python 3 and Bubblewrap (`bwrap`); verify both command names match the runtime image packages.

## 2. Verify Runtime Availability

- [x] 2.1 Start a shell in the rebuilt image and verify `python3 --version` and `bwrap --version` both report their versions and exit successfully.
