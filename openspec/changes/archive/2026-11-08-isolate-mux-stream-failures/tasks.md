# Tasks

## 1. Isolate stream teardown and retain bounded validation state

- [x] 1.1 Add deterministic missing/delayed CLOSE-acknowledgement regressions in `tests/test_mux.py` for both endpoint roles; verify the original implementation closes an unrelated working stream and include one test using the real ten-second deadline.
- [x] 1.2 Separate local close completion from wire retirement in `network/mux.py`, release payload/worker ownership and retain at most the existing outstanding-stream budget; verify missing ACK preserves another stream, delayed ACK restores capacity, repeated close is idempotent and exhausted capacity rejects local opens without channel teardown.
- [x] 1.3 Validate and discard legal crossing DATA/open-response/credit/EOF frames for closing streams, preserving identifier and credit rules; verify tests reject duplicates, over-credit, data after EOF, reused/unknown IDs and arbitrary fully retired DATA, with no negative or leaked byte accounting.
- [x] 1.4 Document caller completion, outstanding-slot retention and permanent-missing-ACK capacity limits in `network/README.md` and `docs/network-contract.md`; verify documented limits match constants and `python3 -m unittest discover -s tests -p test_mux.py -v` passes for this group.

## 2. Recover from bounded control pressure and cancellation

- [x] 2.1 Replace immediate queue-full protocol failure with bounded control backpressure outside stream condition locks, keeping one sender and no detached task per control; verify a reproducible burst exceeding immediate queue capacity drains after a paused writer resumes and subsequent traffic succeeds on the same channel.
- [x] 2.2 Apply finite shared-write budgets across queue/lock/drain progress and all outbound paths, preserving the separate partial-frame deadline; verify permanent writer stalls close the channel, wake blocked operations and finish cleanup within bounds while temporary pressure does not.
- [x] 2.3 Make required CLOSE scheduling and relay/proxy cleanup cancellation-safe; verify simultaneous close, cancellation during enqueue/lock/drain, remote close and session shutdown release sockets, active-handler counts, workers and buffers exactly once without losing required controls or deadlocking.
- [x] 2.4 Update transport-pressure and timeout guidance in `network/README.md` and `docs/network-contract.md`, removing the existing unconditional claim that reading never waits on a congested writer; verify guidance matches the new bounded-wait behavior and the complete mux suite passes.

## 3. Verify the installed provider path and migration

- [x] 3.1 Extend existing guard/network fixtures with a test-owned transport fault boundary and controlled TLS endpoints; verify the production guard, relay and proxy preserve unrelated traffic and admit a subsequent tunnel after delayed ACK and recoverable control congestion, without runtime fault switches, syscall mocks or application-command exceptions.
- [x] 3.2 Build candidate runtime and immutable proxy images under explicit maintenance authorization, then run `bash tests/run-runtime.sh --guard`, `--network-policy` and `--network` plus the TLS parser/proxy suites; verify allowed TLS/streaming, both profile inventories, mismatched-SNI zero-byte rejection, denied destinations, channel-loss closure, owned cleanup and new N23 acceptance against recorded image identities.
- [x] 3.3 Verify protected code/image changes invalidate previous qualification and candidate failure preserves the previous activation; run `bash tests/run-runtime.sh --qualification`, `--setup` and `--setup-runtime` with the candidate images and record actual pass/fail/unavailable outcomes.
- [x] 3.4 Document protected-code and dual-image deployment, requalification, restart and rollback in `docs/setup.md` and the relevant README guidance; record component fault instrumentation separately from production-path acceptance, actual deadlines, resource bounds, environment identities and any unavailable authentication/native-LSM checks in `docs/validation.md`.

## 4. Complete integration validation

- [x] 4.1 Run `python3 -m unittest discover -s tests -p test_wrapper.py -v`, the full mux suite and `bash tests/run-runtime.sh --guard-idle` against the candidate; verify ordinary mode admission and real-duration idle resume remain correct alongside N23 recovery.
- [x] 4.2 Run `bash -n` on changed shell scripts, `git diff --check` and `openspec validate isolate-mux-stream-failures --strict`; verify all delta scenarios have evidence, the implementation stays within N23 and `todo.md` marks N23 complete only after required acceptance succeeds.
