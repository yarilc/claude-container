# Tasks

## 1. Install the editor and set the defaults

- [x] 1.1 Add `nano` to the `apt-get install` list in `Containerfile` in alphabetical order, and verify by reading the file that the layer still ends with `apt-get clean` and `rm -rf /var/lib/apt/lists/*`
- [x] 1.2 Add `EDITOR=nano` and `VISUAL=nano` to the `ENV` block in `Containerfile`, and verify by reading that both are set in the same `ENV` instruction as the existing variables
- [x] 1.3 Append `unset historylog` to `/etc/nanorc` in the `Containerfile` `RUN` step, so nano stops trying to write history under the read-only home, and verify by reading that the line is in the `RUN` chain after the `npm install` steps

## 2. Build and verify the image

- [x] 2.1 Run `./claude-container.sh --container-build` and confirm the build succeeds, which shows that `nano` is available in the bookworm repository
- [x] 2.2 Run `./claude-container.sh --container-shell`, then inside it run `nano --version`, `echo "$EDITOR" "$VISUAL"` and confirm both values are `nano`
- [x] 2.3 Inside the container, open a scratch file in the workspace with `nano`, save a line, exit, and confirm the line is in the file on the host, to verify that the editor can write to the mounted workspace; then delete the scratch file
- [x] 2.4 Rebuild with `./claude-container.sh --container-build`, then run `grep -n historylog /etc/nanorc` in the container and confirm the `unset historylog` line is present, and open `nano` and confirm the "Unable to create directory" warning no longer appears on exit

## 3. Documentation

- [x] 3.1 Add a short note to `README.md` under "Included tools" stating that the image includes `nano` and sets `EDITOR` and `VISUAL` to it, and verify with `git diff --check`

## 4. Final verification

- [x] 4.1 Run `bash -n claude-container.sh` and `git diff --check`, and confirm both pass
- [x] 4.2 Start Claude with `./claude-container.sh`, run `/memory`, and confirm that the editor opens instead of the "Couldn't open ... in an editor" message
