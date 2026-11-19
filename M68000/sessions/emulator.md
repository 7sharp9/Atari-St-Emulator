# Emulator and tooling: handoff

Updated 2026-11-19 by the session that made the core about 15% faster (`Tailcalls` off, sampled loop detector) and
added the user-mode privilege checks, both behind the net.

## Resume point

- Last commit of this workstream: `c337526` emulator: 15% faster, privileged instructions trap in user mode; with
  `9a017aa` (Super Sprint `psg_capture.py` enters its ISR through `trap #0`) and `9c97fa3` (`tools/bench_builds.py`).
- Installed build: `bin/` and `server/bin/` `M68000.dll` SHA-256 `b17b5ad14363aba6…` (embedding commit `c337526`; a
  rebuild after the later commits changes the hash with no source edit), `stserver.dll` `adec5d78c43d7f4c…`.
  `checkpoint.txt` unchanged (`5000000 verify` passes).
- Working data: none. A pre-change control build is `git worktree add` at `d3d1a70` and
  `dotnet build -c Debug M68000.fsproj -o <dir>`.
- Uncommitted work left behind: none.

## Proven so far

- Speed: `tools/bench_builds.py`, six interleaved rounds, load 4 to 5: 30M boot median 7.34 s to 6.22 s (ratio 0.80 to
  0.88 in every round), 20M steps of Black Tiger `play_start.snap` 3.72 s to 3.12 s (0.82 to 0.86), boot snapshot
  byte-identical. `Tailcalls` off alone 5% and 8%, the sampled detector alone 8% and 9%. DEVELOPING.md "Performance".
- The sampled loop detector still fires: `ww 70000 60fe` / `callcap 70000 200000` on a 30M boot snapshot prints
  `LOOP DETECTED at PC=$00070000` on the old and new builds (one loop of period 1; not gated).
- Privilege and illegal encodings: `bash tools/priv_check.sh` 11/11 on the installed build, 1/11 on a `d3d1a70` build
  (STOP alone, which already checked). DEVELOPING.md "Undecoded encodings".
- Net (`tools/regress_net.sh`, `d3d1a70` build against the new one, Cadaver inputs): both verify PASS, 30M snapshot,
  Cadaver snapshot, game watch (25 lines) and DMA watch (11 lines) identical; selftest 1,000,051 pass, 0 wrong, 9 skip.
  `uv run python tools/gates.py run all -j 3`: 87/88, then `supersprint/liveproof` PASS after its harness fix (6/6 for
  the game), on DLL `3554979f…` (the same sources before the commit).
- Boot profile (`sample`, before the two speed changes): 21% of the main thread in the allocator, about 8% in
  `AtartSt.Step` itself, the rest in decode. `DOTNET_PerfMapEnabled=1` writes no perf map on this Mac.
- Earlier, unchanged: FDC busy search and Read Track, MFP in-service and IKBD pacing, execution profiles, recordings,
  provenance: DEVELOPING.md sections of the same names.
- Gate manifests: 88 gates, 71 declaring no inputs (`gates.py run all --dry-run`, 0 MISSING).

## Running

Nothing running.

## Open, in priority order

1. Cycle counting, stage 1 (unchanged): count 68000 cycles per instruction and report them only; byte-identical 30M
   snapshot and every gate; then instructions per frame in several games against the fixed 12,000. Stage 2 needs
   Dave's go-ahead.
2. Core defects a fresh-context review found and this session did not fix. Each needs its own probe that fails first:
   - MFP: channel 6 (ACIA) is never gated on IERB/IMRB bit 6 and `EnqueueIkbd`/`ikbdReply` skip the ACIA
     receive-interrupt enable that `IkbdTick` checks; IMRA/IMRB are tested only when a request is raised, not in
     `TopPendingInterrupt`; IPRA/IPRB read as plain storage; the FDC line never raises MFP channel 7. Read by the
     reviewer, not re-read here. Proof: a poked loop that masks a pending source and counts handler entries.
   - `stserver` `boot` reuses the machine: `Cpu.Reset` keeps `Stopped`, `Halted` and the registers, and the MMU is
     not reset (`Program.fs` `AtartSt.Reset`, read here). Proof: `boot` after a STOP or a double fault runs.
   - `stserver` `peek`/`read` go through `PeekByte`, which has device side effects (`$fffc02` pops the IKBD byte);
     route them through `PeekBytes` as the REPL's `m` does. Proof: a queued byte survives a `read` of `$fffc02`.
   - RMW decoders (NEG, NOT, CLR, ADDQ, Scc, memory shifts, `RegEaOp` to memory) accept An and PC-relative
     destinations that are illegal on the 68000; add the data-alterable guard `ImmediateToEa` has. Proof: new
     `priv_check.sh` rows reaching vector 4.
   - A traced TRAP/TRAPV/CHK/divide-by-zero skips the trace exception; `ikbdCmdBuf` and `Stopped` are not in the
     snapshot; Timer B in event-count mode reads the wrong counter and is fast-forwarded; `WriteWord` drops
     `$fffc00`/`$fffc02`; supervisor-only memory (`$0-$7ff`, the I/O page) is not protected. Each only when a game needs it.
3. Speed, next steps (hypotheses until an interleaved A/B): `ResolveEa` allocates a 4-tuple, a boxed `EaResolved`,
   a closure and a fixup list per operand; returning through mutable scratch fields is a different design from
   the rejected struct tuple. The mutable `Cpu` remains the large one. Bound either by the 21% allocator share.
4. MFP arbitration order (Timer B above the ACIA); FDC gaps (spin-up, index, sector register); each when needed.
5. Gate manifests for Cadaver, Populous, Lemmings, Impossamole; a home for proofs that belong to no game
   (`tools/priv_check.sh`, `server/*_proof.py`, `tools/stdrive*_check.py`), which are not gates yet.
6. Go-Explore over forks; coverage against a static listing; `sub`/`subq` in the compare log; Ghidra import; MAME gaps.

## Known traps

- A copy of `M68000.dll` alone does not run (`dotnet exec` exits 131): a control build is its whole `-o` directory.
- `stserver.dll` is not built by `dotnet build M68000.fsproj`: build `server/StServer.fsproj`, which also reinstalls the
  core into `bin/`; cmp `bin/` against `server/bin/`. A session's MCP `stserver` keeps the build it started with.
- `M68000.dll` embeds HEAD's commit, so a rebuild after any commit changes its SHA-256 with no source edit.
- Run `tools/gates.py` with `uv run python`: under the system `python3` the Super Sprint gates ERROR on `numpy`.
- A worktree's `checkpoint.txt` is a symlink to the main checkout's: `N checkpoint` there writes through to MAIN.
- A harness that ran a supervisor-only routine from user-mode game code passed before `c337526` and fails after it:
  a gate that moves for that reason is the harness, not the core (Super Sprint `liveproof` printed 1/1 for every count).
- The loop detector reports a stuck loop up to a few samples (16 steps each) later than before; a script that
  matches the exact step of `LOOP DETECTED` would move. None is known.

## Waiting on Dave

- Push: `master` is 18 commits ahead of `origin/master` with this file's commit, only on this Mac.
- Which of Open 2's defects to fix next; the MFP group changes interrupt delivery, so it is a behaviour change for
  every game and wants the full gate run.
- Stale in other workstreams' handoffs (not edited here): `sessions/archipelagos.md` Open 1 and its "Both loader pokes
  applied" snapshots; `sessions/carriercommand.md` Open 6; `sessions/captive.md` Open 5; for supersprint, `sound.md:58`
  and `secrets.md:97` give liveproof's Q as 15559/15559 where the script prints 15559/15560.

## Next session

`/resume emulator`. Check `bin/` against a fresh build of HEAD and run `bash tools/priv_check.sh` (11/11). Then Open 2's
`stserver` items (`boot` reset and side-effect-free `peek`/`read`), which are tooling fixes with no effect on a game
run; then the MFP group behind the full net, or Open 1 stage 1 if Dave prefers the timing work.
